import re
from playwright.sync_api import Page, expect
from framework.pages.base_page import BasePage
from framework.pages.orangehrmlive.dashboard_page import DashboardPage

class LoginPage(BasePage):
    """Page object for the OrangeHRM Login Page."""

    def __init__(self, page: Page):
        super().__init__(page)
        self._username_input = page.get_by_role("textbox", name="Username")
        self._password_input = page.get_by_role("textbox", name="Password")
        self._login_button = page.get_by_role("button", name="Login")

    def login(self, username: str, password: str) -> DashboardPage:
        """Performs a login action with the given credentials.

        Args:
            username: The username to enter.
            password: The password to enter.

        Returns:
            A DashboardPage object representing the page after successful login.
        """
        expect(self._username_input).to_be_visible()
        self._username_input.fill(username)

        expect(self._password_input).to_be_visible()
        self._password_input.fill(password)

        expect(self._login_button).to_be_visible()
        self._login_button.click()

        # After clicking login, we expect to be on the Dashboard page
        # The DashboardPage object is returned for chaining actions/assertions
        return DashboardPage(self.page)
