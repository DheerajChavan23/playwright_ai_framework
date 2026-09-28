"""Pytest configuration, fixtures, and failure hooks for Playwright tests."""

import base64
import os
import re
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import BrowserContext, Page


def _extract_domain(item_or_node: pytest.Item) -> str:
    """Extract domain name from environment variable or test file path structure."""
    env_domain = os.environ.get("TEST_DOMAIN")
    if env_domain:
        return env_domain

    node_path = Path(str(getattr(item_or_node, "path", getattr(item_or_node, "fspath", ""))))
    parts = list(node_path.parts)
    if "tests" in parts:
        idx = parts.index("tests")
        if idx + 1 < len(parts) - 1:
            return parts[idx + 1]
    return "common"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Hook to capture test results and attach full-page screenshots on failure."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    # Capture full-page screenshot if test failed during call phase
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
                domain = _extract_domain(item)
                screenshots_dir = Path("reports/screenshots") / domain
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                safe_test_name = re.sub(r'[\\/*?:"<>|]', "_", item.name)
                screenshot_path = screenshots_dir / f"{safe_test_name}.png"

                # Capture full-page screenshot
                try:
                    screenshot_bytes = page.screenshot(path=str(screenshot_path), full_page=True)
                except Exception:
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

                # 2. Embed screenshot as base64 inline image inside pytest-html report
                try:
                    from pytest_html import extras

                    encoded_img = base64.b64encode(screenshot_bytes).decode("utf-8")
                    report_extras = getattr(report, "extras", [])

                    # Add standard PNG extra (handled natively by pytest-html)
                    report_extras.append(
                        extras.png(encoded_img, name=f"failure_{safe_test_name}")
                    )

                    # Embed inline HTML image element with styling
                    inline_img_html = (
                        f'<div class="failure-screenshot" style="margin-top: 10px;">'
                        f'<p><strong>📸 Failure Screenshot ({domain}):</strong></p>'
                        f'<img src="data:image/png;base64,{encoded_img}" '
                        f'alt="failure screenshot {safe_test_name}" '
                        f'style="max-width: 100%; max-height: 600px; border: 2px solid #e74c3c; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/>'
                        f'</div>'
                    )
                    report_extras.append(extras.html(inline_img_html))
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
        domain = _extract_domain(request.node)
        traces_dir = Path("reports/traces") / domain
        traces_dir.mkdir(parents=True, exist_ok=True)
        safe_test_name = re.sub(r'[\\/*?:"<>|]', "_", request.node.name)
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
