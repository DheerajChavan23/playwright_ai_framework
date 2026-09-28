import re
from playwright.sync_api import Page, Locator
from framework.pages.base_page import BasePage


class ShoppingCartManagementPage(BasePage):
    """Page object representing the Shopping Cart Management functionality on Saucedemo."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username_input: Locator = page.get_by_role("textbox", name="Username")
        self.password_input: Locator = page.get_by_role("textbox", name="Password")
        self.login_button: Locator = page.get_by_role("button", name=re.compile(r"login", re.IGNORECASE))
        self.add_backpack_to_cart_button: Locator = page.locator('[data-test="add-to-cart-sauce-labs-backpack"]')
        self.shopping_cart_badge: Locator = page.locator('[data-test="shopping-cart-badge"]')

    def navigate(self, url: str = "https://www.saucedemo.com") -> None:
        """Navigates to the specified URL."""
        self.page.goto(url)

    def login(self, username: str = "standard_user", password: str = "secret_sauce") -> None:
        """Fills credentials and submits the login form."""
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def add_backpack_to_cart(self) -> None:
        """Clicks the 'Add to cart' button for Sauce Labs Backpack."""
        self.add_backpack_to_cart_button.click()
