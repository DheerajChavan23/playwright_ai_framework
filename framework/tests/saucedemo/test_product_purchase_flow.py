import pytest
from playwright.sync_api import Page, expect
from framework.pages.saucedemo.login_page import LoginPage
from framework.pages.saucedemo.inventory_page import InventoryPage
from framework.pages.saucedemo.cart_page import CartPage

# Define constants for test data
STANDARD_USER = "standard_user"
SECRET_SAUCE = "secret_sauce"
BIKE_LIGHT_PRODUCT_NAME = "Sauce Labs Bike Light"

@pytest.fixture(scope="function", autouse=True)
def setup_pages(page: Page):
    """
    Fixture to initialize page objects for each test function.
    """
    login_page = LoginPage(page)
    inventory_page = InventoryPage(page)
    cart_page = CartPage(page)
    return login_page, inventory_page, cart_page

def test_successful_login_and_adding_bike_light_to_cart(setup_pages):
    """
    Scenario: Successful login and adding "Sauce Labs Bike Light" to cart
    """
    login_page, inventory_page, cart_page = setup_pages

    # Given the user navigates to the Swag Labs login page (https://www.saucedemo.com).
    login_page.navigate()
    login_page.expect_page_to_be_loaded()

    # When the user enters "standard_user" into the "Username" textbox on the "Landing / Login Screen".
    # And the user enters "secret_sauce" into the "Password" textbox on the "Landing / Login Screen".
    # And the user clicks the "Login" button on the "Landing / Login Screen".
    login_page.login(STANDARD_USER, SECRET_SAUCE)

    # Then the user is redirected to the Inventory page (https://www.saucedemo.com/inventory.html).
    inventory_page.expect_page_to_be_loaded() # This includes URL and element visibility checks

    # When the user clicks the "Add to cart" button for "Sauce Labs Bike Light" on the "Authenticated Dashboard / Post-Login Screen".
    inventory_page.add_item_to_cart(BIKE_LIGHT_PRODUCT_NAME)

    # Then the shopping cart icon on the "Authenticated Dashboard / Post-Login Screen" displays "1" item.
    inventory_page.expect_cart_badge_count("1")

    # When the user clicks the "Cart" icon on the "Authenticated Dashboard / Post-Login Screen".
    inventory_page.click_cart_icon()

    # Then the user is redirected to the Shopping Cart page and "Sauce Labs Bike Light" is listed in the cart.
    cart_page.expect_page_to_be_loaded() # This includes URL and common element checks
    cart_page.expect_item_in_cart(BIKE_LIGHT_PRODUCT_NAME)
