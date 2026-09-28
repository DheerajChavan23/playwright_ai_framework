"""Smoke test suite validating baseline POM and fixtures."""

from playwright.sync_api import Page
from framework.pages.base_page import BasePage


def test_base_page_smoke(page: Page) -> None:
    """Validate BasePage navigation, text extraction, and visibility checks."""
    base_page = BasePage(page)
    base_page.navigate("data:text/html,<h1>Autonomous Test Framework</h1><p id='desc'>Playwright + Gemini</p>")
    assert base_page.is_visible("#desc") is True
    assert "Playwright + Gemini" in base_page.get_text("#desc")
