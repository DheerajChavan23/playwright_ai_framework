"""Subprocess Pytest Execution Engine and Failure Parser."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional



class TestRunner:
    """Executes Pytest suites via subprocess and parses structured execution results."""

    def __init__(
        self,
        uv_path: Optional[str] = None,
        headed: bool = False,
        slowmo: int = 0,
    ) -> None:
        self.uv_path = uv_path or shutil.which("uv") or "uv"
        self.headed = headed
        self.slowmo = slowmo

    def _parse_failure_reason(self, stdout: str, stderr: str) -> str:
        """Extract root cause (e.g. assertion error or locator timeout) from pytest output.

        Args:
            stdout: Pytest standard output.
            stderr: Pytest standard error.

        Returns:
            Concise description of the failure reason.
        """
        combined = f"{stdout or ''}\n{stderr or ''}"

        # 1. Collect Pytest failure lines marked with 'E   '
        e_lines = [
            re.sub(r"^\s*E\s+", "", line).strip()
            for line in combined.splitlines()
            if re.match(r"^\s*E\s+", line)
        ]
        if e_lines:
            return " | ".join(e_lines)

        # 2. Check Pytest short test summary section
        if "short test summary info" in combined:
            summary_part = combined.split("short test summary info", 1)[1]
            failed_lines = [
                line.strip()
                for line in summary_part.splitlines()
                if line.strip().startswith("FAILED")
            ]
            if failed_lines:
                return " | ".join(failed_lines)

        # 3. Generic python exception extraction from traceback
        if "Traceback (most recent call last):" in combined:
            tb_lines = [l.strip() for l in combined.splitlines() if l.strip()]
            if tb_lines:
                return tb_lines[-1]

        return ""

    def run_test(
        self,
        test_file_path: str,
        timeout: int = 120,
        headed: Optional[bool] = None,
        slowmo: Optional[int] = None,
        domain: Optional[str] = None,
        html_report_path: Optional[str | Path] = None,
        allure_results_dir: Optional[str | Path] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a test file or directory via `uv run pytest <target> --tb=short`.

        Args:
            test_file_path: Relative or absolute path to test file or domain directory.
            timeout: Subprocess timeout in seconds (default: 120s).
            headed: Whether to launch browser in visible mode.
            slowmo: Milliseconds to delay actions (appends --slowmo <ms> if > 0).
            domain: Domain name of the target application (injected into env).
            html_report_path: Target path for the segregated timestamped HTML report.
            allure_results_dir: Target directory for domain-segregated Allure results.
            extra_args: Optional additional pytest flags.

        Returns:
            Dictionary containing:
                - success (bool): True if exit_code == 0
                - exit_code (int): Subprocess exit code
                - stdout (str): Standard output
                - stderr (str): Standard error
                - failure_reason (str): Parsed failure message if test failed
                - html_report (str): Path to generated HTML report if specified
                - allure_results (str): Path to generated Allure results if specified
        """
        cmd = [self.uv_path, "run", "pytest", str(test_file_path), "--tb=short"]

        use_headed = self.headed if headed is None else headed
        use_slowmo = self.slowmo if slowmo is None else slowmo

        # Append --headed if requested
        if use_headed:
            cmd.append("--headed")

        # Append --slowmo <ms> if a non-zero value is provided
        if use_slowmo and use_slowmo > 0:
            cmd.extend(["--slowmo", str(use_slowmo)])

        # Segregated HTML report storage
        if html_report_path:
            cmd.extend([f"--html={str(html_report_path)}", "--self-contained-html"])

        # Segregated Allure results directory
        if allure_results_dir:
            cmd.append(f"--alluredir={str(allure_results_dir)}")

        if extra_args:
            cmd.extend(extra_args)

        env = os.environ.copy()
        if domain:
            env["TEST_DOMAIN"] = domain

        use_shell = sys.platform.startswith("win")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=use_shell,
                timeout=timeout,
                env=env,
            )
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            exit_code = -1
            stdout = e.stdout or "" if isinstance(e.stdout, str) else ""
            stderr = f"Subprocess timed out after {timeout} seconds."
        except Exception as e:
            exit_code = -2
            stdout = ""
            stderr = f"Execution failed with error: {str(e)}"

        success = (exit_code == 0)
        failure_reason = "" if success else self._parse_failure_reason(stdout, stderr)

        return {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "failure_reason": failure_reason,
            "html_report": str(html_report_path) if html_report_path else None,
            "allure_results": str(allure_results_dir) if allure_results_dir else None,
        }
