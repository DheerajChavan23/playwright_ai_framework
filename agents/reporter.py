"""Test Reporting and Executive Summary Generator."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ReporterAgent:
    """Compiles test reports, serves allure UI, and produces executive markdown summaries."""

    def __init__(
        self,
        reports_dir: str = "reports",
        domain: Optional[str] = None,
        html_report_file: Optional[str | Path] = None,
    ) -> None:
        self.reports_dir = Path(reports_dir)
        self.domain = domain

        if domain:
            self.allure_results_dir = self.reports_dir / "allure-results" / domain
            self.allure_report_dir = self.reports_dir / "allure-report" / domain
            self.summary_file = self.reports_dir / f"executive_summary_{domain}.md"
        else:
            self.allure_results_dir = self.reports_dir / "allure-results"
            self.allure_report_dir = self.reports_dir / "allure-report"
            self.summary_file = self.reports_dir / "executive_summary.md"

        if html_report_file:
            self.html_report_file = Path(html_report_file)
        else:
            self.html_report_file = self.reports_dir / "report.html"

    def compile_allure_report(
        self,
        domain_results_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """Compile Allure HTML report from raw results if allure CLI is available.

        Returns:
            Dict indicating whether compilation was performed and status.
        """
        allure_bin = shutil.which("allure")
        results_dir = Path(domain_results_dir) if domain_results_dir else self.allure_results_dir
        if not allure_bin:
            return {
                "compiled": False,
                "reason": f"Allure CLI binary not found in PATH. Raw results saved in {results_dir}.",
                "path": str(results_dir),
            }

        cmd = [
            allure_bin,
            "generate",
            str(results_dir),
            "-o",
            str(self.allure_report_dir),
            "--clean",
        ]
        try:
            use_shell = sys.platform.startswith("win")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=use_shell)
            return {
                "compiled": res.returncode == 0,
                "path": str(self.allure_report_dir),
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        except Exception as e:
            return {
                "compiled": False,
                "reason": f"Allure report compilation failed: {str(e)}",
            }

    def serve_allure_report(
        self,
        domain_results_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """Trigger `allure serve <results_dir>` if allure binary is available."""
        allure_bin = shutil.which("allure")
        results_dir = Path(domain_results_dir) if domain_results_dir else self.allure_results_dir
        if not allure_bin:
            return {
                "served": False,
                "reason": "Allure CLI binary not found in PATH.",
                "path": str(results_dir),
            }

        cmd = [allure_bin, "serve", str(results_dir)]
        try:
            use_shell = sys.platform.startswith("win")
            subprocess.run(cmd, shell=use_shell)
            return {"served": True, "path": str(results_dir)}
        except Exception as e:
            return {
                "served": False,
                "reason": f"Failed to execute allure serve: {str(e)}",
                "path": str(results_dir),
            }

    def generate_summary(self, data: Dict[str, Any]) -> str:
        """Generate and save an executive Markdown summary of the automated test run.

        Args:
            data: Execution metrics and artifact paths from AutomationOrchestrator.

        Returns:
            Markdown formatted summary content.
        """
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status_badge = "✅ **PASSED**" if data.get("success") else "❌ **FAILED**"
        healing_history = data.get("healing_history", [])
        healing_count = len(healing_history)

        lines = [
            "# Autonomous E2E Automation - Executive Test Summary",
            "",
            f"**Execution Timestamp:** {now}  ",
            f"**Overall Status:** {status_badge}  ",
            f"**Target URL:** `{data.get('url', 'N/A')}`  ",
            f"**Target Domain:** `{data.get('domain_name', 'N/A')}`  ",
            f"**User Scenario:** {data.get('scenario', 'N/A')}  ",
            f"**Total Run Attempts:** {data.get('attempts', 1)}  ",
            f"**Healing Iterations Triggered:** {healing_count}",

            "",
            "---",
            "",
            "## 📁 Generated Artifacts & Reports",
            f"- **HTML Test Report:** `{data.get('html_report', self.html_report_file)}`",
            f"- **Allure Raw Results:** `{data.get('allure_results', self.allure_results_dir)}`",
            f"- **Page Object File:** `{data.get('page_file', 'N/A')}`",
            f"- **Pytest Test File:** `{data.get('test_file', 'N/A')}`",
            f"- **Trace Directory:** `{self.reports_dir / 'traces' / (data.get('domain_name') or self.domain or '')}`",
            f"- **Screenshots Directory:** `{self.reports_dir / 'screenshots' / (data.get('domain_name') or self.domain or '')}`",
            "",
            "---",
            "",
            "## 📋 BDD Test Specification",
            data.get("test_plan", "_No test plan recorded._"),
            "",
            "---",
            "",
            "## 🩺 Self-Healing & Diagnostics Log",
        ]

        if not healing_history:
            lines.append("No healing iterations required. The generated suite passed on the first run.")
        else:
            lines.append("| Attempt | Diagnosis | Fix Type | Patched File |")
            lines.append("|---|---|---|---|")
            for h in healing_history:
                attempt = h.get("attempt", "N/A")
                diag = h.get("diagnosis", "N/A").replace("\n", " ")
                ftype = h.get("fix_type", "N/A")
                patched = h.get("patched_file", "N/A")
                lines.append(f"| {attempt} | {diag} | `{ftype}` | `{patched}` |")

        if not data.get("success") and data.get("failure_reason"):
            lines.extend([
                "",
                "---",
                "",
                "## ⚠️ Final Failure Reason",
                "```text",
                data.get("failure_reason", ""),
                "```",
            ])

        summary_md = "\n".join(lines)
        self.summary_file.write_text(summary_md, encoding="utf-8")
        return summary_md
