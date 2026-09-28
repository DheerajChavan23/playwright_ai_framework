from playwright.sync_api import Page, expect
from framework.pages.base_page import BasePage

class CartPage(BasePage):
    URL = "https://www.saucedemo.com/cart.html"

    def __init__(self, page: Page):
        super().__init__(page)
        # No specific elements are needed in the constructor for this simple scenario
        # Locators for items will be dynamic based on item_name

    def expect_page_to_be_loaded(self) -> None:
        """Verifies that the cart page is loaded."""
        self.expect_page_title("Swag Labs")
        self.expect_current_url(self.URL)
        # Optionally, check for a common element like "Your Cart" title
        expect(self.page.get_by_text("Your Cart")).to_be_visible()

    def expect_item_in_cart(self, item_name: str) -> None:
        """
        Verifies that a specific item is listed in the shopping cart.
        """
        # Using the .cart_item_label for more specific context within the cart
        cart_item_label = self.page.locator(f".cart_item_label:has-text('{item_name}')")
        expect(cart_item_label).to_be_visible()

    def verify_item_in_cart(self, item_name: str) -> None:
        """Alias for expect_item_in_cart."""
        self.expect_item_in_cart(item_name)

    def proceed_to_checkout(self) -> None:
        """Clicks the checkout button."""
        self.page.locator("[data-test='checkout']").click()

