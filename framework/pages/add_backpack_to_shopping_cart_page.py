from playwright.sync_api import Page, Locator
from framework.pages.base_page import BasePage


class AddBackpackToShoppingCartPage(BasePage):
    """Page object for adding the Sauce Labs Backpack to the shopping cart."""

    URL = "https://www.saucedemo.com"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username_input: Locator = self.page.get_by_role("textbox", name="Username")
        self.password_input: Locator = self.page.get_by_role("textbox", name="Password")
        self.login_button: Locator = self.page.locator("[data-test='login-button']")
        self.backpack_add_to_cart_button: Locator = self.page.locator("[data-test='add-to-cart-sauce-labs-backpack']")
        self.shopping_cart_badge: Locator = self.page.locator("[data-test='shopping-cart-badge']")

    def navigate(self) -> None:
        """Navigates to the Sauce Demo login page."""
        self.page.goto(self.URL)

    def login(self, username: str = "standard_user", password: str = "secret_sauce") -> None:
        """Fills credentials and submits the login form."""
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def add_backpack_to_cart(self) -> None:
        """Adds the Sauce Labs Backpack item to the cart."""
        self.backpack_add_to_cart_button.click()
