from playwright.sync_api import Page, expect

class BasePage:
    """Base class for all Page Objects."""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str) -> None:
        """Navigates to the specified URL."""
        self.page.goto(url)
