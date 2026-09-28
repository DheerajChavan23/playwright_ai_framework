from playwright.sync_api import Page

class CheckoutStepOnePage:
    def __init__(self, page: Page):
        self.page = page
        self.first_name_input = page.get_by_role("textbox", name="First Name")
        self.last_name_input = page.get_by_role("textbox", name="Last Name")
        self.postal_code_input = page.get_by_role("textbox", name="Zip/Postal Code")
        self.continue_button = page.get_by_role("button", name="continue")

    def fill_checkout_info(self, first_name: str, last_name: str, postal_code: str) -> None:
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.postal_code_input.fill(postal_code)

    def continue_checkout(self) -> None:
        self.continue_button.click()
