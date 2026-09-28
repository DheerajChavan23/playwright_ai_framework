import pytest
from playwright.sync_api import Page, expect
from framework.pages.add_backpack_to_shopping_cart_page import AddBackpackToShoppingCartPage


@pytest.mark.ai_generated
def test_add_backpack_to_shopping_cart(page: Page) -> None:
    """Verify standard_user can log in and add the Sauce Labs Backpack to the cart."""
    page_obj = AddBackpackToShoppingCartPage(page)

    # Given the user navigates to the login page
    page_obj.navigate()

    # When the user enters credentials and logs in
    page_obj.login("standard_user", "secret_sauce")

    # And the user clicks the 'Add to cart' button for Sauce Labs Backpack
    page_obj.add_backpack_to_cart()

    # Then the page URL should transition to inventory
    expect(page).to_have_url("https://www.saucedemo.com/inventory.html")

    # And the shopping cart badge should be visible and display '1'
    expect(page_obj.shopping_cart_badge).to_be_visible()
    expect(page_obj.shopping_cart_badge).to_have_text("1")
