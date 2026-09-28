from playwright.sync_api import Page, expect

class CheckoutCompletePage:
    def __init__(self, page: Page):
        self.page = page

    def verify_order_complete(self, message: str) -> None:
        expect(self.page.get_by_role("heading", name=message)).to_be_visible()
