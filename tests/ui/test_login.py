import os
import pytest
import allure

from pages.login_page import LoginPage


@allure.feature("Auth")
@allure.story("Login")
def test_login_success(page):
    login_page = LoginPage(page)

    # For secure self-heal workflow: force primary locator to break so fallback triggers & is recorded
    if os.getenv("BREAK_LOCATOR", "false").lower() == "true":
        login_page.username_locator = "#username_broken"

    login_page.load()
    login_page.login("tomsmith", "SuperSecretPassword!")
    assert login_page.is_success(), "Expected successful login message"


@allure.feature("Auth")
@allure.story("Login")
def test_login_invalid_password(page):
    login_page = LoginPage(page)

    if os.getenv("BREAK_LOCATOR", "false").lower() == "true":
        login_page.username_locator = "#username_broken"

    login_page.load()
    login_page.login("tomsmith", "wrongpassword")
    assert login_page.is_error(), "Expected invalid credentials message"
