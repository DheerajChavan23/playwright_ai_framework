"""Automation Generator Agent translating BDD plans into Page Objects and Pytest suites."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.llm_client import LLMClient
from core.utils import ensure_package_dir, extract_domain_name
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
        self.model_name = model_name or settings.gemini_model or "gemini-3.7-flash"
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
        domain_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call Gemini to generate Page Object code and Pytest test code.

        Args:
            test_plan: BDD test plan markdown.
            dom_snapshot: Pruned accessibility DOM map.
            url: Target application URL.
            feature_name: Optional custom feature name.
            domain_name: Optional custom domain name (inferred from URL if omitted).

        Returns:
            Dictionary containing page_code, test_code, and file paths.
        """
        resolved_domain = domain_name or extract_domain_name(url)
        resolved_feature = feature_name or self._infer_feature_name(test_plan)
        suggested_class_name = "".join(part.capitalize() for part in resolved_feature.split("_")) + "Page"

        snapshot_str = (
            json.dumps(dom_snapshot, indent=2)
            if not isinstance(dom_snapshot, str)
            else dom_snapshot
        )

        prompt = GENERATOR_PROMPT.format(
            url=url,
            domain_name=resolved_domain,
            feature_name=resolved_feature,
            page_class_name=suggested_class_name,
            test_plan=test_plan,
            dom_snapshot=snapshot_str,
        )

        raw_output = self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
        )
        parsed = self._parse_response(raw_output)

        parsed.setdefault("domain_name", resolved_domain)
        parsed.setdefault("feature_name", resolved_feature)
        parsed.setdefault(
            "test_file_path",
            f"framework/tests/{resolved_domain}/test_{resolved_feature}.py",
        )

        # Handle multi-page generation vs single-page generation
        pages_list = parsed.get("pages", [])
        if pages_list and isinstance(pages_list, list):
            for p in pages_list:
                p_class = p.get("page_class_name", "")
                p_file = p.get("page_file_path", "")
                if not p_file and p_class:
                    slug = re.sub(r'(?<!^)(?=[A-Z])', '_', p_class).lower()
                    if not slug.endswith("_page"):
                        slug = f"{slug}_page"
                    p["page_file_path"] = f"framework/pages/{resolved_domain}/{slug}.py"
                elif p_file and f"framework/pages/{resolved_domain}" not in p_file:
                    file_name = Path(p_file).name
                    p["page_file_path"] = f"framework/pages/{resolved_domain}/{file_name}"

            # Fallbacks for primary page references
            primary_file = parsed.get("primary_page_file") or pages_list[-1]["page_file_path"]
            primary_class = parsed.get("primary_page_class") or pages_list[-1]["page_class_name"]
            primary_code = pages_list[-1].get("page_code", "")

            parsed.setdefault("page_file_path", primary_file)
            parsed.setdefault("page_class_name", primary_class)
            parsed.setdefault("page_code", primary_code)
        else:
            # Single logical page object
            resp_class = parsed.get("page_class_name")
            if resp_class:
                slug = re.sub(r'(?<!^)(?=[A-Z])', '_', resp_class).lower()
                if not slug.endswith("_page"):
                    slug = f"{slug}_page"
                default_page_file = f"framework/pages/{resolved_domain}/{slug}.py"
                parsed.setdefault("page_file_path", default_page_file)
            else:
                parsed.setdefault("page_class_name", suggested_class_name)
                parsed.setdefault(
                    "page_file_path",
                    f"framework/pages/{resolved_domain}/{resolved_feature}_page.py",
                )

        return parsed

    def generate_and_save(
        self,
        test_plan: str,
        dom_snapshot: Union[Dict[str, Any], list, str],
        url: str,
        feature_name: Optional[str] = None,
        domain_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate code and write files to disk under framework/pages/<domain> and framework/tests/<domain>.

        Returns:
            Result dictionary with file paths, codes, feature name, and domain name.
        """
        generated = self.generate_code(
            test_plan=test_plan,
            dom_snapshot=dom_snapshot,
            url=url,
            feature_name=feature_name,
            domain_name=domain_name,
        )

        # Write all generated page objects (multi-page or single)
        pages_list = generated.get("pages", [])
        if pages_list and isinstance(pages_list, list):
            for p_item in pages_list:
                p_path = Path(p_item["page_file_path"])
                ensure_package_dir(p_path.parent)
                p_path.write_text(p_item.get("page_code", ""), encoding="utf-8")
        else:
            page_path = Path(generated["page_file_path"])
            ensure_package_dir(page_path.parent)
            page_path.write_text(generated.get("page_code", ""), encoding="utf-8")

        test_path = Path(generated["test_file_path"])
        ensure_package_dir(test_path.parent)
        test_path.write_text(generated["test_code"], encoding="utf-8")

        return generated

