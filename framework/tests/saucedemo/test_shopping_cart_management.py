import pytest
from playwright.sync_api import Page, expect
from framework.pages.saucedemo.login_page import LoginPage
from framework.pages.saucedemo.inventory_page import InventoryPage


@pytest.mark.ai_generated
def test_shopping_cart_management(page: Page) -> None:
    """Tests logging in and adding an item to the shopping cart using logical POM classes."""
    login_page = LoginPage(page)
    inventory_page = InventoryPage(page)

    # Given the user navigates to the login page
    login_page.navigate("https://www.saucedemo.com")

    # When the user logs in with valid credentials
    login_page.login("standard_user", "secret_sauce")

    # Then the page transitions to the inventory dashboard
    expect(page).to_have_url("https://www.saucedemo.com/inventory.html")

    # And the user adds an item to cart using the parameterized action method
    inventory_page.add_item_to_cart("Sauce Labs Backpack")

    # Then the shopping cart badge should be visible and equal "1"
    expect(inventory_page.shopping_cart_badge).to_be_visible()
    expect(inventory_page.shopping_cart_badge).to_have_text("1")
