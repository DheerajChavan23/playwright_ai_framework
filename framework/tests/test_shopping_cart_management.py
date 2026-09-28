import pytest
from playwright.sync_api import Page, expect
from framework.pages.shopping_cart_management_page import ShoppingCartManagementPage


@pytest.mark.ai_generated
def test_shopping_cart_management(page: Page) -> None:
    """Tests adding an item to the shopping cart as a standard user."""
    page_obj = ShoppingCartManagementPage(page)

    # Given the user navigates to "https://www.saucedemo.com"
    page_obj.navigate("https://www.saucedemo.com")

    # When the user fills in the "Username" textbox with "standard_user"
    # And the user fills in the "Password" textbox with "secret_sauce"
    # And the user clicks the "login-button" button
    page_obj.login("standard_user", "secret_sauce")

    # Then the page URL should transition to "https://www.saucedemo.com/inventory.html"
    expect(page).to_have_url("https://www.saucedemo.com/inventory.html")

    # And the user clicks the "Add to cart" button for the "Sauce Labs Backpack"
    page_obj.add_backpack_to_cart()

    # And the shopping cart badge should be visible on the page
    expect(page_obj.shopping_cart_badge).to_be_visible()

    # And the shopping cart badge text should equal "1"
    expect(page_obj.shopping_cart_badge).to_have_text("1")
