from playwright.sync_api import Page, expect
from framework.pages.base_page import BasePage

class DashboardPage(BasePage):
    """Page object for the OrangeHRM Dashboard Page."""

    def __init__(self, page: Page):
        super().__init__(page)
        self._dashboard_heading_locator = page.get_by_role("heading", name="Dashboard")

    @property
    def dashboard_heading(self):
        """Returns the locator for the Dashboard heading."""
        return self._dashboard_heading_locator
