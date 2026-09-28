"""Base Page Object implementation providing resilient, web-first interactions with Playwright."""

import re
from typing import Optional, Union
from playwright.sync_api import Locator, Page, expect


class BasePage:
    """Base class for all Page Objects.

    Encapsulates Playwright Page instance and provides resilient actions
    that rely on web-first auto-waiting and built-in locators.
    Strictly enforces Playwright auto-waiting and zero arbitrary time.sleep().
    """

    def __init__(self, page: Page, base_url: str = "") -> None:
        """Initialize BasePage with a Playwright Page instance.

        Args:
            page: Active Playwright Page instance.
            base_url: Optional base application URL.
        """
        self.page: Page = page
        self.base_url: str = base_url

    def _resolve_locator(self, locator: Union[str, Locator]) -> Locator:
        """Resolve a string selector (CSS/relative XPath/text) or existing Locator into a Playwright Locator.

        Supports standard CSS selectors, relative XPath expressions (e.g. '//button[...]'),
        and Playwright selector prefixes.

        Args:
            locator: A selector string (CSS / relative XPath / text) or a Playwright Locator.

        Returns:
            Locator instance.
        """
        if isinstance(locator, str):
            if locator.startswith("//") or locator.startswith("(//"):
                return self.page.locator(f"xpath={locator}")
            return self.page.locator(locator)
        return locator

    def by_xpath(self, xpath: str) -> Locator:
        """Locate element(s) using a relative XPath expression.

        Args:
            xpath: Relative XPath string (e.g. "//div[contains(@class, 'item')]//button").

        Returns:
            Playwright Locator instance.
        """
        selector = f"xpath={xpath}" if not xpath.startswith("xpath=") else xpath
        return self.page.locator(selector)

    def by_css(self, selector: str) -> Locator:
        """Locate element(s) using a relative or standard CSS selector.

        Args:
            selector: CSS selector string (e.g. ".inventory_item:has-text('Bike Light') button").

        Returns:
            Playwright Locator instance.
        """
        return self.page.locator(selector)

    def by_container(
        self,
        container_selector: str,
        has_text: str,
        child_selector: str = "button",
    ) -> Locator:
        """Locate child element inside a contextual parent container filtered by text.

        Example:
            self.by_container(".inventory_item", "Sauce Labs Bike Light", "button")

        Args:
            container_selector: CSS or XPath selector for the container.
            has_text: Text that the parent container must contain.
            child_selector: Selector for target child element inside container.

        Returns:
            Playwright Locator instance.
        """
        return self.page.locator(container_selector).filter(has_text=has_text).locator(child_selector)

    def navigate(self, url: Optional[str] = None, **kwargs) -> None:
        """Navigate to the specified URL or self.url/self.base_url using Playwright auto-waiting.

        Args:
            url: Destination URL. If omitted, uses self.url or self.base_url.
            **kwargs: Additional navigation options for page.goto.
        """
        target_url = (
            url
            or getattr(self, "url", None)
            or getattr(self, "URL", None)
            or getattr(self, "base_url", None)
            or getattr(self, "BASE_URL", None)
        )
        if not target_url:
            raise ValueError("No URL provided to navigate to.")
        self.page.goto(target_url, **kwargs)

    def click(self, locator: Union[str, Locator], **kwargs) -> None:
        """Click on the target element with Playwright auto-waiting.

        Args:
            locator: Target element selector or Locator.
            **kwargs: Additional options for locator.click.
        """
        loc = self._resolve_locator(locator)
        loc.click(**kwargs)

    def fill(self, locator: Union[str, Locator], text: str, **kwargs) -> None:
        """Fill target input field with text using Playwright auto-waiting.

        Args:
            locator: Target element selector or Locator.
            text: Text to fill into the input field.
            **kwargs: Additional options for locator.fill.
        """
        loc = self._resolve_locator(locator)
        loc.fill(text, **kwargs)

    def get_text(self, locator: Union[str, Locator]) -> str:
        """Retrieve inner text of target element with auto-waiting.

        Args:
            locator: Target element selector or Locator.

        Returns:
            Inner text string of the target element.
        """
        loc = self._resolve_locator(locator)
        return loc.inner_text()

    def is_visible(self, locator: Union[str, Locator]) -> bool:
        """Check whether target element is currently visible.

        Args:
            locator: Target element selector or Locator.

        Returns:
            True if element is visible, False otherwise.
        """
        loc = self._resolve_locator(locator)
        return loc.is_visible()

    def wait_for_url(self, url_pattern: str, **kwargs) -> None:
        """Wait for current page URL to match the specified regex or string pattern.

        Args:
            url_pattern: Expected URL pattern or substring.
            **kwargs: Additional options for page.wait_for_url.
        """
        self.page.wait_for_url(url_pattern, **kwargs)

    def expect_page_title(self, expected_title: Union[str, re.Pattern]) -> None:
        """Verify the page title matches expected string or regex.

        Args:
            expected_title: Expected title string or regex pattern.
        """
        expect(self.page).to_have_title(expected_title)

    def expect_current_url(self, expected_url: Union[str, re.Pattern]) -> None:
        """Verify the page URL matches expected string or regex.

        Args:
            expected_url: Expected URL string or regex pattern.
        """
        if isinstance(expected_url, str):
            clean = re.escape(expected_url.rstrip("/")) + r"/?"
            pattern = re.compile(rf"^{clean}$")
            expect(self.page).to_have_url(pattern)
        else:
            expect(self.page).to_have_url(expected_url)

