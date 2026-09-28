"""Base Page Object implementation providing resilient, web-first interactions with Playwright."""

from typing import Union
from playwright.sync_api import Locator, Page, expect


class BasePage:
    """Base class for all Page Objects.

    Encapsulates Playwright Page instance and provides resilient actions
    that rely on web-first auto-waiting and built-in locators.
    Strictly enforces Playwright auto-waiting and zero arbitrary time.sleep().
    """

    def __init__(self, page: Page) -> None:
        """Initialize BasePage with a Playwright Page instance.

        Args:
            page: Active Playwright Page instance.
        """
        self.page: Page = page

    def _resolve_locator(self, locator: Union[str, Locator]) -> Locator:
        """Resolve a string selector or existing Locator into a Playwright Locator.

        Args:
            locator: A selector string (CSS/XPath/role/text) or a Playwright Locator.

        Returns:
            Locator instance.
        """
        if isinstance(locator, str):
            return self.page.locator(locator)
        return locator

    def navigate(self, url: str, **kwargs) -> None:
        """Navigate to the specified URL using Playwright auto-waiting.

        Args:
            url: Destination URL.
            **kwargs: Additional navigation options for page.goto.
        """
        self.page.goto(url, **kwargs)

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

    def get_locator(self, locator: Union[str, Locator]) -> Locator:
        """Get or cast to a Playwright Locator instance.

        Args:
            locator: Target selector or Locator.

        Returns:
            Resolved Locator instance.
        """
        return self._resolve_locator(locator)
