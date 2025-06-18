from playwright.sync_api import Page, TimeoutError

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://the-internet.herokuapp.com/login"
        self.username_locator = "#username"
        self.password_locator = "#password"
        self.login_button = 'button[type="submit"]'
        self.flash_message = ".flash"

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
        try:
            msg = self.page.locator(self.flash_message).inner_text()
            return "You logged into a secure area!" in msg
        except TimeoutError:
            return False

    def is_error(self):
        try:
            msg = self.page.locator(self.flash_message).inner_text()
            return "Your username is invalid!" in msg or "Your password is invalid!" in msg
        except TimeoutError:
            return False
