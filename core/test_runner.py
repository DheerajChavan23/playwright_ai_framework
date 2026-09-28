"""Subprocess Pytest Execution Engine and Failure Parser."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


class TestRunner:
    """Executes Pytest suites via subprocess and parses structured execution results."""

    def __init__(self, uv_path: str | None = None) -> None:
        self.uv_path = uv_path or shutil.which("uv") or "uv"

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

    def run_test(self, test_file_path: str, timeout: int = 120) -> Dict[str, Any]:
        """Execute a test file via `uv run pytest <test_file_path> --tb=short`.

        Args:
            test_file_path: Relative or absolute path to test file.
            timeout: Subprocess timeout in seconds (default: 120s).

        Returns:
            Dictionary containing:
                - success (bool): True if exit_code == 0
                - exit_code (int): Subprocess exit code
                - stdout (str): Standard output
                - stderr (str): Standard error
                - failure_reason (str): Parsed failure message if test failed
        """
        cmd = [self.uv_path, "run", "pytest", str(test_file_path), "--tb=short"]

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
        }
