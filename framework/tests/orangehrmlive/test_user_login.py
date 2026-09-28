import pytest
import re
from playwright.sync_api import Page, expect

# Import Page Objects
from framework.pages.orangehrmlive.login_page import LoginPage
from framework.pages.orangehrmlive.dashboard_page import DashboardPage

# Target URL for the application
TARGET_URL = "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login"

@pytest.mark.orangehrmlive
@pytest.mark.user_login
def test_successful_admin_login(page: Page) -> None:
    """Tests a successful admin login scenario on OrangeHRM.

    Scenario:
    - Given User navigates to the OrangeHRM login page.
    - When User enters "Admin" into the username input field.
    - And User enters "admin123" into the password input field.
    - And User clicks the "Login" button.
    - Then User should be successfully logged in and redirected to the Dashboard.
    """
    # Instantiate the Login Page Object
    login_page = LoginPage(page)

    # Given: User navigates to the OrangeHRM login page.
    login_page.navigate(TARGET_URL)
    expect(page).to_have_url(TARGET_URL)

    # When: User enters "Admin" into the username input field.
    # And: User enters "admin123" into the password input field.
    # And: User clicks the "Login" button.
    # The login method encapsulates these actions and returns the next page object.
    dashboard_page = login_page.login("Admin", "admin123")

    # Then: User should be successfully logged in and redirected to the Dashboard.
    # Web-first assertion for URL redirection
    expect(page).to_have_url(re.compile(".*/dashboard/index"))

    # Web-first assertion for Dashboard heading visibility
    expect(dashboard_page.dashboard_heading).to_be_visible()
    expect(dashboard_page.dashboard_heading).to_have_text("Dashboard")
