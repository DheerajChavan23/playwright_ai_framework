"""End-to-End Autonomous Automation Orchestrator."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from agents.generator import GeneratorAgent
from agents.healer import HealerAgent
from agents.planner import PlannerAgent
from agents.reporter import ReporterAgent
from config.settings import settings
from core.browser_manager import BrowserManager
from core.test_runner import TestRunner
from core.utils import extract_domain_name


class AutomationOrchestrator:
    """Coordinates DOM reconnaissance, planning, code generation, execution, and self-healing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        headless: Optional[bool] = None,
        headed: bool = False,
        slowmo: int = 0,
        max_healing_attempts: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model

        if headed:
            self.headed = True
            self.headless = False
        elif headless is not None:
            self.headless = headless
            self.headed = not headless
        else:
            self.headless = settings.default_headless
            self.headed = not self.headless

        self.slowmo = slowmo or 0
        self.max_healing_attempts = (
            max_healing_attempts
            if max_healing_attempts is not None
            else settings.max_healing_attempts
        )

        self.browser_manager = BrowserManager(headless=self.headless)
        self.test_runner = TestRunner(headed=self.headed, slowmo=self.slowmo)
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
        dom_snapshot = await self.browser_manager.inspect_page(url, scenario=scenario)
        elements_count = len(dom_snapshot.get("interactive_elements", []))
        screens = dom_snapshot.get("screens", [])
        if len(screens) > 1:
            details_str = f"Multi-step exploration: captured {len(screens)} screens ({', '.join(s['screen_name'] for s in screens)})"
        else:
            details_str = f"Extracted {elements_count} interactive elements from '{dom_snapshot.get('title', '')}'"
        notify("DOM Reconnaissance", "COMPLETED", details_str)

        # 2. Test Planning
        notify("Test Planner", "RUNNING", "Formulating BDD test plan with Gemini")
        test_plan = self.planner.plan_test(url, scenario, dom_snapshot)
        feature_name = self.planner.extract_feature_name(test_plan)
        domain_name = extract_domain_name(url)
        notify("Test Planner", "COMPLETED", f"Generated BDD plan for feature '{feature_name}' (domain: '{domain_name}')")

        # 3. Code Generation (Domain-specific Page Object & Pytest Suite)
        notify("Code Generator", "RUNNING", f"Synthesizing POM & Pytest suite in '{domain_name}' subdirectories")
        gen_result = self.generator.generate_and_save(
            test_plan=test_plan,
            dom_snapshot=dom_snapshot,
            url=url,
            feature_name=feature_name,
            domain_name=domain_name,
        )
        page_file = gen_result["page_file_path"]
        test_file = gen_result["test_file_path"]
        notify("Code Generator", "COMPLETED", f"Created {page_file} and {test_file}")

        # Domain-segregated report storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_report_file = Path("reports") / f"report_{domain_name}_{timestamp}.html"
        allure_results_dir = Path("reports") / "allure-results" / domain_name
        html_report_file.parent.mkdir(parents=True, exist_ok=True)
        allure_results_dir.mkdir(parents=True, exist_ok=True)

        # 4. Initial Test Execution
        notify("Subprocess Test Runner", "RUNNING", f"Executing {test_file}")
        test_result = self.test_runner.run_test(
            test_file,
            domain=domain_name,
            html_report_path=html_report_file,
            allure_results_dir=allure_results_dir,
        )
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
                updated_dom = await self.browser_manager.inspect_page(url, scenario=scenario)
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
            test_result = self.test_runner.run_test(
                test_file,
                domain=domain_name,
                html_report_path=html_report_file,
                allure_results_dir=allure_results_dir,
            )
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
        reporter = ReporterAgent(domain=domain_name, html_report_file=html_report_file)
        allure_compile_status = reporter.compile_allure_report(domain_results_dir=allure_results_dir)

        run_data = {
            "success": test_result["success"],
            "attempts": attempts,
            "healing_history": healing_history,
            "url": url,
            "scenario": scenario,
            "domain_name": domain_name,
            "test_plan": test_plan,
            "feature_name": feature_name,
            "page_file": page_file,
            "test_file": test_file,
            "test_result": test_result,
            "failure_reason": test_result.get("failure_reason", ""),
            "allure_compile": allure_compile_status,
            "html_report": str(html_report_file),
            "allure_results": str(allure_results_dir),
            "traces_dir": str(Path("reports/traces") / domain_name),
            "screenshots_dir": str(Path("reports/screenshots") / domain_name),
        }

        summary_md = reporter.generate_summary(run_data)
        run_data["summary_markdown"] = summary_md
        run_data["summary_file"] = str(reporter.summary_file)

        overall_status = "PASSED" if test_result["success"] else "FAILED"
        notify("Reporting Pipeline", overall_status, f"Final result: {overall_status}")

        return run_data

    def serve_report(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger allure serve for the generated domain results directory."""
        domain = run_data.get("domain_name")
        allure_dir = run_data.get("allure_results") or (Path("reports/allure-results") / (domain or ""))
        reporter = ReporterAgent(domain=domain)
        return reporter.serve_allure_report(allure_dir)
