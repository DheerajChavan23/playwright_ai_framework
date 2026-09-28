import re
import pytest
from playwright.sync_api import Page, expect
from framework.pages.saucedemo.login_page import LoginPage
from framework.pages.saucedemo.inventory_page import InventoryPage
from framework.pages.saucedemo.cart_page import CartPage
from framework.pages.saucedemo.checkout_step_one_page import CheckoutStepOnePage
from framework.pages.saucedemo.checkout_step_two_page import CheckoutStepTwoPage
from framework.pages.saucedemo.checkout_complete_page import CheckoutCompletePage

def test_purchase_bike_light_product_flow(page: Page):
    login_page = LoginPage(page)
    inventory_page = InventoryPage(page)
    cart_page = CartPage(page)
    checkout_step_one_page = CheckoutStepOnePage(page)
    checkout_step_two_page = CheckoutStepTwoPage(page)
    checkout_complete_page = CheckoutCompletePage(page)

    # Given the user navigates to the landing URL
    login_page.navigate("https://www.saucedemo.com")

    # When the user enters credentials and logs in
    login_page.login("standard_user", "secret_sauce")

    # Then the application should transition to the authenticated URL
    expect(page).to_have_url("https://www.saucedemo.com/inventory.html")

    # When the user adds the bike light to the cart and goes to cart
    inventory_page.add_to_cart("add-to-cart-sauce-labs-bike-light")
    expect(page.get_by_role("button", name=re.compile(r"Cart.*1 item", re.IGNORECASE))).to_be_visible()
    inventory_page.go_to_cart()

    # Then the user should see 'Sauce Labs Bike Light' in the cart summary
    cart_page.verify_item_in_cart("Sauce Labs Bike Light")

    # When the user clicks checkout and completes the form
    cart_page.proceed_to_checkout()
    checkout_step_one_page.fill_checkout_info("John", "Doe", "12345")
    checkout_step_one_page.continue_checkout()

    # And clicks finish
    checkout_step_two_page.finish_checkout()

    # Then the user should see the checkout complete confirmation message
    checkout_complete_page.verify_order_complete("Thank you for your order!")
