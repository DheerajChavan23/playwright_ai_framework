import re
from playwright.sync_api import Page, expect
from framework.pages.base_page import BasePage

class InventoryPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, base_url="https://www.saucedemo.com")
        self.url = f"{self.base_url}/inventory.html"
        self._sort_products_dropdown = self.page.locator("select[data-test='product-sort-container']")
        self._shopping_cart_link = self.page.locator("[data-test='shopping-cart-link']")
        self._remove_bike_light_button = self.page.locator("[data-test='remove-sauce-labs-bike-light']")

    def expect_page_to_be_loaded(self) -> None:
        """Verifies that the inventory page elements are visible and URL is correct."""
        self.expect_current_url(self.url)
        expect(self._shopping_cart_link).to_be_visible()

    @property
    def shopping_cart_badge(self):
        """Returns the locator for the shopping cart badge."""
        return self.page.locator(".shopping_cart_badge")

    @property
    def sort_products_dropdown(self):
        return self._sort_products_dropdown

    @property
    def shopping_cart_icon_one_item(self):
        return self._shopping_cart_link

    @property
    def remove_bike_light_button(self):
        return self._remove_bike_light_button

    def add_item_to_cart(self, item_name: str) -> None:
        data_test_id = f"add-to-cart-{item_name.lower().replace(' ', '-')}"
        add_to_cart_button = self.page.locator(f"[data-test='{data_test_id}'], [id='{data_test_id}'], [id='{item_name}']")
        expect(add_to_cart_button).to_be_visible()
        add_to_cart_button.click()

    def add_to_cart(self, item_name: str) -> None:
        """Alias for add_item_to_cart."""
        self.add_item_to_cart(item_name)

    def expect_cart_badge_count(self, count: str) -> None:
        """Verifies the shopping cart badge count."""
        badge = self.page.locator(".shopping_cart_badge")
        expect(badge).to_have_text(count)

    def click_cart_icon(self) -> None:
        """Clicks the shopping cart icon using relative CSS / data-test."""
        self._shopping_cart_link.click()

    def go_to_cart(self) -> None:
        self.click_cart_icon()

