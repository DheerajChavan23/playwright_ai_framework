"""Automation Generator Agent translating BDD plans into Page Objects and Pytest suites."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.llm_client import LLMClient
from config.agent_prompts import GENERATOR_PROMPT
from config.settings import settings


class GeneratorAgent:
    """Generates production-grade Page Object Model classes and Pytest test functions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or settings.gemini_model or "gemini-3.8-flash"
        self.llm_client = LLMClient(api_key=self.api_key, default_model=self.model_name)


    def _infer_feature_name(self, test_plan: str, default: str = "feature_test") -> str:
        """Infer snake_case feature name from test plan."""
        match = re.search(r"Feature Key:\s*[`'\"]?([a-zA-Z0-9_\-]+)[`'\"]?", test_plan)
        if match:
            return match.group(1).strip().lower().replace("-", "_")

        match_title = re.search(r"# Feature:\s*(.+)", test_plan)
        if match_title:
            raw_title = match_title.group(1).strip()
            clean = re.sub(r"[^\w\s]", "", raw_title).lower()
            return "_".join(clean.split())[:30]

        return default

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON payload from LLM response."""
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start : end + 1])
            raise ValueError(f"Failed to parse JSON from Generator Agent response:\n{raw_text}")

    def generate_code(
        self,
        test_plan: str,
        dom_snapshot: Union[Dict[str, Any], list, str],
        url: str,
        feature_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call Gemini to generate Page Object code and Pytest test code.

        Args:
            test_plan: BDD test plan markdown.
            dom_snapshot: Pruned accessibility DOM map.
            url: Target application URL.
            feature_name: Optional custom feature name.

        Returns:
            Dictionary containing page_code, test_code, and file paths.
        """
        resolved_feature = feature_name or self._infer_feature_name(test_plan)
        page_class_name = "".join(part.capitalize() for part in resolved_feature.split("_")) + "Page"

        snapshot_str = (
            json.dumps(dom_snapshot, indent=2)
            if not isinstance(dom_snapshot, str)
            else dom_snapshot
        )

        prompt = GENERATOR_PROMPT.format(
            url=url,
            feature_name=resolved_feature,
            page_class_name=page_class_name,
            test_plan=test_plan,
            dom_snapshot=snapshot_str,
        )

        raw_output = self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
        )
        parsed = self._parse_response(raw_output)


        # Standardize expected keys
        parsed.setdefault("feature_name", resolved_feature)
        parsed.setdefault("page_class_name", page_class_name)
        parsed.setdefault("page_file_path", f"framework/pages/{resolved_feature}_page.py")
        parsed.setdefault("test_file_path", f"framework/tests/test_{resolved_feature}.py")

        return parsed

    def generate_and_save(
        self,
        test_plan: str,
        dom_snapshot: Union[Dict[str, Any], list, str],
        url: str,
        feature_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate code and write files to disk under framework/pages and framework/tests.

        Returns:
            Result dictionary with file paths, codes, and feature name.
        """
        generated = self.generate_code(
            test_plan=test_plan,
            dom_snapshot=dom_snapshot,
            url=url,
            feature_name=feature_name,
        )

        page_path = Path(generated["page_file_path"])
        test_path = Path(generated["test_file_path"])

        page_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)

        page_path.write_text(generated["page_code"], encoding="utf-8")
        test_path.write_text(generated["test_code"], encoding="utf-8")

        return generated
