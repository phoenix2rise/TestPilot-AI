from playwright.sync_api import Page

from utils.locator_healer import fill_with_fallback, click_with_fallback


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://the-internet.herokuapp.com/login"
        self.username_locator = "input[name='username']"
        self.password_locator = "#password"
        self.login_button = "button[type='submit']"
        self.success_message = ".flash.success"
        self.error_message = ".flash.error"

    def load(self):
        self.page.goto(self.url)

    def login(self, username: str, password: str):
        # Self-heal capable locator fill: primary + fallbacks, with event recording
        fill_with_fallback(
            self.page,
            primary=self.username_locator,
            fallbacks=["username", "input[name='username']"]"],
            value=username,
            owner=self,
            field="username_locator",
        )
        self.page.fill(self.password_locator, password)
        click_with_fallback(
            self.page,
            primary=self.login_button,
            fallbacks=["button[type='submit']"],
            owner=self,
            field="login_button",
        )

    def is_success(self) -> bool:
        return self.page.locator(self.success_message).is_visible()

    def is_error(self) -> bool:
        return self.page.locator(self.error_message).is_visible()

    def get_message_text(self) -> str:
        # both success and error messages use ".flash"
        return self.page.locator(".flash").inner_text()
