from pages.login_page import LoginPage

def test_valid_login(page):
    login = LoginPage(page)
    login.load()
    login.login("tomsmith", "SuperSecretPassword!")
    assert login.is_success()

def test_invalid_login(page):
    login = LoginPage(page)
    login.load()
    login.login("wronguser", "wrongpass")
    assert login.is_error()
