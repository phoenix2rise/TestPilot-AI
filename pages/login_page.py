from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://the-internet.herokuapp.com/login"
        self.username_locator = "#username"
        self.password_locator = "#password"
        self.login_button = 'button[type="submit"]'
        self.success_message = ".flash.success"
        self.error_message = ".flash.error"

    def load(self):
        self.page.goto(self.url)

    def login(self, username, password):
        try:
            self.page.fill(self.username_locator, username)
        except:
            self.page.fill("input[name='username']", username)
        self.page.fill(self.password_locator, password)
        self.page.click(self.login_button)

    def is_success(self):
        return self.page.locator(self.success_message).is_visible()

    def is_error(self):
        return self.page.locator(self.error_message).is_visible()
