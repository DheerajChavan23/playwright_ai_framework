"""Test Planner Agent powered by Google Gemini."""

import json
import os
import re
from typing import Any, Dict, Optional, Union
from core.llm_client import LLMClient
from config.agent_prompts import PLANNER_PROMPT
from config.settings import settings


class PlannerAgent:
    """Evaluates target app state and user goals to produce structured BDD test plans."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or settings.gemini_model or "gemini-3.8-flash"
        self.llm_client = LLMClient(api_key=self.api_key, default_model=self.model_name)


    def extract_feature_name(self, plan_markdown: str, default: str = "feature_test") -> str:
        """Extract recommended snake_case feature name from the generated plan.

        Args:
            plan_markdown: Markdown test plan returned by Gemini.
            default: Default feature name if none found.

        Returns:
            Sanitized snake_case feature name.
        """
        match = re.search(r"Feature Key:\s*[`'\"]?([a-zA-Z0-9_\-]+)[`'\"]?", plan_markdown)
        if match:
            return match.group(1).strip().lower().replace("-", "_")

        # Fallback to feature title regex
        match_title = re.search(r"# Feature:\s*(.+)", plan_markdown)
        if match_title:
            raw_title = match_title.group(1).strip()
            clean = re.sub(r"[^\w\s]", "", raw_title).lower()
            return "_".join(clean.split())[:30]

        return default

    def plan_test(
        self,
        url: str,
        scenario: str,
        dom_snapshot: Union[Dict[str, Any], list, str],
    ) -> str:
        """Generate a structured BDD test plan from scenario and DOM accessibility snapshot.

        Args:
            url: Target web app URL.
            scenario: User's natural language test requirement.
            dom_snapshot: Pruned accessibility map.

        Returns:
            Markdown-formatted BDD test plan.
        """
        snapshot_str = (
            json.dumps(dom_snapshot, indent=2)
            if not isinstance(dom_snapshot, str)
            else dom_snapshot
        )

        prompt = PLANNER_PROMPT.format(
            url=url,
            scenario=scenario,
            dom_snapshot=snapshot_str,
        )

        plan_content = self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
        )
        return plan_content.strip()

