from playwright.sync_api import Page, expect
from framework.pages.base_page import BasePage

class LoginPage(BasePage):
    URL = "https://www.saucedemo.com"

    def __init__(self, page: Page):
        super().__init__(page)
        self.username_input = page.get_by_role("textbox", name="Username")
        self.password_input = page.get_by_role("textbox", name="Password")
        self.login_button = page.get_by_role("button", name="Login")

    def expect_page_to_be_loaded(self) -> None:
        """Verifies that the login page elements are visible and URL is correct."""
        expect(self.username_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.login_button).to_be_visible()
        self.expect_page_title("Swag Labs")
        self.expect_current_url(self.URL)

    def login(self, username: str, password: str) -> None:
        """
        Performs a login action with the given username and password.
        """
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
