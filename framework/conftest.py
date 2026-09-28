"""Pytest configuration, fixtures, and failure hooks for Playwright tests."""

import base64
import os
import re
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import BrowserContext, Page


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Hook to capture test results and attach screenshots on failure."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    # Capture screenshot if test failed during call phase
    if report.when == "call" and report.failed:
        page: Page | None = None
        if "page" in item.funcargs:
            page = item.funcargs["page"]
        elif "context" in item.funcargs:
            ctx = item.funcargs["context"]
            if hasattr(ctx, "pages") and ctx.pages:
                page = ctx.pages[0]

        if page is not None and not page.is_closed():
            try:
                screenshots_dir = Path("reports/screenshots")
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                safe_test_name = re.sub(r"[^\w\-_\.]", "_", item.name)
                screenshot_path = screenshots_dir / f"{safe_test_name}.png"
                screenshot_bytes = page.screenshot(path=str(screenshot_path))

                # 1. Attach screenshot to Allure report
                try:
                    import allure

                    allure.attach(
                        screenshot_bytes,
                        name=f"failure_{safe_test_name}",
                        attachment_type=allure.attachment_type.PNG,
                    )
                except Exception:
                    pass

                # 2. Attach screenshot to pytest-html report
                try:
                    from pytest_html import extras

                    encoded_img = base64.b64encode(screenshot_bytes).decode("utf-8")
                    report_extras = getattr(report, "extras", [])
                    report_extras.append(
                        extras.png(encoded_img, name=f"failure_{safe_test_name}")
                    )
                    report.extras = report_extras
                except Exception:
                    pass
            except Exception:
                pass


@pytest.fixture(autouse=True)
def context_tracing(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Enable Playwright tracing and export trace archive on test failure."""
    if "context" not in request.fixturenames and "page" not in request.fixturenames:
        yield
        return

    context: BrowserContext = request.getfixturevalue("context")
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield

    rep_call = getattr(request.node, "rep_call", None)
    rep_setup = getattr(request.node, "rep_setup", None)
    failed = (rep_call and rep_call.failed) or (rep_setup and rep_setup.failed)

    if failed:
        traces_dir = Path("reports/traces")
        traces_dir.mkdir(parents=True, exist_ok=True)
        safe_test_name = re.sub(r"[^\w\-_\.]", "_", request.node.name)
        trace_path = traces_dir / f"{safe_test_name}.zip"
        try:
            context.tracing.stop(path=str(trace_path))
            try:
                import allure

                allure.attach.file(
                    str(trace_path),
                    name=f"trace_{safe_test_name}",
                    attachment_type="application/zip",
                    extension="zip",
                )
            except Exception:
                pass
        except Exception:
            pass
    else:
        try:
            context.tracing.stop()
        except Exception:
            pass
