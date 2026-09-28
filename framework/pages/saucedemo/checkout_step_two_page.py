from playwright.sync_api import Page

class CheckoutStepTwoPage:
    def __init__(self, page: Page):
        self.page = page
        self.finish_button = page.get_by_role("button", name="finish")

    def finish_checkout(self) -> None:
        self.finish_button.click()
