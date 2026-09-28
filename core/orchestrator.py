"""End-to-End Autonomous Automation Orchestrator."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from agents.generator import GeneratorAgent
from agents.healer import HealerAgent
from agents.planner import PlannerAgent
from agents.reporter import ReporterAgent
from config.settings import settings
from core.browser_manager import BrowserManager
from core.test_runner import TestRunner


class AutomationOrchestrator:
    """Coordinates DOM reconnaissance, planning, code generation, execution, and self-healing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        headless: Optional[bool] = None,
        max_healing_attempts: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.headless = (
            headless if headless is not None else settings.default_headless
        )
        self.max_healing_attempts = (
            max_healing_attempts
            if max_healing_attempts is not None
            else settings.max_healing_attempts
        )

        self.browser_manager = BrowserManager(headless=self.headless)
        self.test_runner = TestRunner()
        self.planner = PlannerAgent(api_key=self.api_key, model_name=self.model_name)
        self.generator = GeneratorAgent(api_key=self.api_key, model_name=self.model_name)
        self.healer = HealerAgent(api_key=self.api_key, model_name=self.model_name)
        self.reporter = ReporterAgent()

    async def run(
        self,
        url: str,
        scenario: str,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, Any]:
        """Execute autonomous pipeline: Inspect -> Plan -> Generate -> Run -> Heal -> Report.

        Args:
            url: Target application URL.
            scenario: User's natural language test requirement.
            progress_callback: Optional hook (step, status, details) for real-time progress.

        Returns:
            Dictionary with execution status, attempts, test plan, and report paths.
        """
        def notify(step: str, status: str, details: str = "") -> None:
            if progress_callback:
                progress_callback(step, status, details)

        # 1. DOM Reconnaissance
        notify("DOM Reconnaissance", "RUNNING", f"Navigating to {url}")
        dom_snapshot = await self.browser_manager.inspect_page(url)
        elements_count = len(dom_snapshot.get("interactive_elements", []))
        notify(
            "DOM Reconnaissance",
            "COMPLETED",
            f"Extracted {elements_count} interactive elements from '{dom_snapshot.get('title', '')}'",
        )

        # 2. Test Planning
        notify("Test Planner", "RUNNING", "Formulating BDD test plan with Gemini")
        test_plan = self.planner.plan_test(url, scenario, dom_snapshot)
        feature_name = self.planner.extract_feature_name(test_plan)
        notify("Test Planner", "COMPLETED", f"Generated BDD plan for feature '{feature_name}'")

        # 3. Code Generation (Page Object & Pytest Suite)
        notify("Code Generator", "RUNNING", "Synthesizing Page Object Model and Pytest suite")
        gen_result = self.generator.generate_and_save(
            test_plan=test_plan,
            dom_snapshot=dom_snapshot,
            url=url,
            feature_name=feature_name,
        )
        page_file = gen_result["page_file_path"]
        test_file = gen_result["test_file_path"]
        notify("Code Generator", "COMPLETED", f"Created {page_file} and {test_file}")

        # 4. Initial Test Execution
        notify("Subprocess Test Runner", "RUNNING", f"Executing {test_file}")
        test_result = self.test_runner.run_test(test_file)
        attempts = 1
        healing_history: List[Dict[str, Any]] = []

        if test_result["success"]:
            notify("Subprocess Test Runner", "PASSED", "Initial test run succeeded cleanly")
        else:
            notify(
                "Subprocess Test Runner",
                "FAILED",
                f"Initial failure: {test_result.get('failure_reason', 'Unknown error')}",
            )

        # 5. Self-Healing Loop
        while not test_result["success"] and attempts <= self.max_healing_attempts:
            notify(
                "Self-Healer Agent",
                "HEALING",
                f"Attempt {attempts}/{self.max_healing_attempts}: Diagnosing and repairing code",
            )

            # Re-inspect DOM if necessary for updated state
            try:
                updated_dom = await self.browser_manager.inspect_page(url)
            except Exception:
                updated_dom = dom_snapshot

            heal_result = self.healer.heal(
                test_file_path=test_file,
                page_file_path=page_file,
                failure_reason=test_result.get("failure_reason", ""),
                error_logs=f"{test_result.get('stdout', '')}\n{test_result.get('stderr', '')}",
                dom_snapshot=updated_dom,
            )

            healing_history.append({
                "attempt": attempts,
                "diagnosis": heal_result.get("diagnosis", ""),
                "fix_type": heal_result.get("fix_type", ""),
                "patched_file": heal_result.get("patched_file", ""),
            })

            notify(
                "Self-Healer Agent",
                "PATCHED",
                f"Applied {heal_result.get('fix_type')} fix to {heal_result.get('patched_file')}",
            )

            # Re-run test suite
            notify("Subprocess Test Runner", "RE-TESTING", f"Re-executing {test_file}")
            test_result = self.test_runner.run_test(test_file)
            attempts += 1

            if test_result["success"]:
                notify("Self-Healer Agent", "SUCCESS", "Healed test suite passed successfully")
                break
            else:
                notify(
                    "Self-Healer Agent",
                    "RETRY_FAILED",
                    f"Test still failing: {test_result.get('failure_reason', '')}",
                )

        # 6. Reporting Pipeline
        notify("Reporting Pipeline", "RUNNING", "Compiling HTML and Allure test reports")
        allure_compile_status = self.reporter.compile_allure_report()

        run_data = {
            "success": test_result["success"],
            "attempts": attempts,
            "healing_history": healing_history,
            "url": url,
            "scenario": scenario,
            "test_plan": test_plan,
            "feature_name": feature_name,
            "page_file": page_file,
            "test_file": test_file,
            "test_result": test_result,
            "failure_reason": test_result.get("failure_reason", ""),
            "allure_compile": allure_compile_status,
        }

        summary_md = self.reporter.generate_summary(run_data)
        run_data["summary_markdown"] = summary_md
        run_data["summary_file"] = str(self.reporter.summary_file)
        run_data["html_report"] = str(self.reporter.html_report_file)
        run_data["allure_results"] = str(self.reporter.allure_results_dir)

        overall_status = "PASSED" if test_result["success"] else "FAILED"
        notify("Reporting Pipeline", overall_status, f"Final result: {overall_status}")

        return run_data
