"""Autonomous Self-Healing Agent diagnosing and repairing test failures."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.llm_client import LLMClient
from config.agent_prompts import HEALER_PROMPT
from config.settings import settings


class HealerAgent:
    """Diagnoses test failures, identifies root causes, and patches code in-place."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or settings.gemini_model or "gemini-3.8-flash"
        self.llm_client = LLMClient(api_key=self.api_key, default_model=self.model_name)


    def _infer_page_path(self, test_file_path: str) -> str:
        """Infer corresponding page object path from test file path."""
        p = Path(test_file_path)
        stem = p.stem  # e.g., 'test_cart_checkout'
        if stem.startswith("test_"):
            feature_name = stem[5:]
        else:
            feature_name = stem

        page_file = Path("framework/pages") / f"{feature_name}_page.py"
        return str(page_file)

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON payload from Healer Agent response."""
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
            raise ValueError(f"Failed to parse JSON from Healer Agent response:\n{raw_text}")

    def heal(
        self,
        test_file_path: str,
        failure_reason: str,
        error_logs: str,
        dom_snapshot: Union[Dict[str, Any], list, str],
        page_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Diagnose failure, query Gemini for a fix, and overwrite the affected file(s).

        Args:
            test_file_path: Path to failing test file.
            failure_reason: Concise root cause extracted by TestRunner.
            error_logs: Complete stdout/stderr trace.
            dom_snapshot: Current DOM accessibility snapshot.
            page_file_path: Optional path to Page Object file (inferred if omitted).

        Returns:
            Dictionary containing diagnosis, fix_type, patched_file, and updated code.
        """
        test_path = Path(test_file_path)
        resolved_page_path = Path(page_file_path or self._infer_page_path(test_file_path))

        test_code = test_path.read_text(encoding="utf-8") if test_path.exists() else ""
        page_code = (
            resolved_page_path.read_text(encoding="utf-8")
            if resolved_page_path.exists()
            else ""
        )

        snapshot_str = (
            json.dumps(dom_snapshot, indent=2)
            if not isinstance(dom_snapshot, str)
            else dom_snapshot
        )

        prompt = HEALER_PROMPT.format(
            test_file_path=str(test_path),
            page_file_path=str(resolved_page_path),
            test_code=test_code,
            page_code=page_code,
            failure_reason=failure_reason,
            error_logs=error_logs,
            dom_snapshot=snapshot_str,
        )

        raw_output = self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
        )
        healing_result = self._parse_response(raw_output)


        diagnosis = healing_result.get("diagnosis", "No diagnosis provided.")
        fix_type = healing_result.get("fix_type", "UNKNOWN")
        patched_target = str(healing_result.get("patched_file", "both")).lower()

        updated_page_code = healing_result.get("page_code")
        updated_test_code = healing_result.get("test_code")

        # Overwrite page file if patched
        if patched_target in ("page", "both") and updated_page_code and resolved_page_path.exists():
            resolved_page_path.write_text(updated_page_code, encoding="utf-8")

        # Overwrite test file if patched
        if patched_target in ("test", "both") and updated_test_code and test_path.exists():
            test_path.write_text(updated_test_code, encoding="utf-8")

        return {
            "diagnosis": diagnosis,
            "fix_type": fix_type,
            "patched_file": patched_target,
            "test_file_path": str(test_path),
            "page_file_path": str(resolved_page_path),
            "applied": True,
        }
