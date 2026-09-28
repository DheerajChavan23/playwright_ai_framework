from playwright.sync_api import Page, expect
import re

class BasePage:
    URL = None # To be overridden by child classes

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str = None) -> None:
        """Navigates to the page's URL or a specified URL."""
        target_url = url if url else self.URL
        if not target_url:
            raise ValueError("URL not defined for this page or not provided.")
        self.page.goto(target_url)
        self.expect_page_to_be_loaded()

    def expect_page_to_be_loaded(self) -> None:
        """
        Abstract method to be implemented by child classes to verify page load.
        """
        raise NotImplementedError("Each page object must implement expect_page_to_be_loaded method.")

    def get_page_title(self) -> str:
        """Returns the title of the current page."""
        return self.page.title()

    def expect_page_title(self, title: str) -> None:
        """Asserts the page title."""
        expect(self.page).to_have_title(title)

    def expect_current_url(self, url: str) -> None:
        """Asserts the current URL."""
        expect(self.page).to_have_url(url)
