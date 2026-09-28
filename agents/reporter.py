"""Test Reporting and Executive Summary Generator."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ReporterAgent:
    """Compiles test reports and produces executive markdown summaries."""

    def __init__(self, reports_dir: str = "reports") -> None:
        self.reports_dir = Path(reports_dir)
        self.allure_results_dir = self.reports_dir / "allure-results"
        self.allure_report_dir = self.reports_dir / "allure-report"
        self.html_report_file = self.reports_dir / "report.html"
        self.summary_file = self.reports_dir / "executive_summary.md"

    def compile_allure_report(self) -> Dict[str, Any]:
        """Compile Allure HTML report from raw results if allure CLI is available.

        Returns:
            Dict indicating whether compilation was performed and status.
        """
        allure_bin = shutil.which("allure")
        if not allure_bin:
            return {
                "compiled": False,
                "reason": "Allure CLI binary not found in PATH. Raw results saved in reports/allure-results.",
                "path": str(self.allure_results_dir),
            }

        cmd = [
            allure_bin,
            "generate",
            str(self.allure_results_dir),
            "-o",
            str(self.allure_report_dir),
            "--clean",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
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
            f"**User Scenario:** {data.get('scenario', 'N/A')}  ",
            f"**Total Run Attempts:** {data.get('attempts', 1)}  ",
            f"**Healing Iterations Triggered:** {healing_count}",
            "",
            "---",
            "",
            "## 📁 Generated Artifacts & Reports",
            f"- **HTML Test Report:** `{self.html_report_file}`",
            f"- **Allure Raw Results:** `{self.allure_results_dir}`",
            f"- **Page Object File:** `{data.get('page_file', 'N/A')}`",
            f"- **Pytest Test File:** `{data.get('test_file', 'N/A')}`",
            f"- **Trace Directory:** `{self.reports_dir / 'traces'}`",
            f"- **Screenshots Directory:** `{self.reports_dir / 'screenshots'}`",
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
