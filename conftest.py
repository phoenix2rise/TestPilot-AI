import pytest
import allure

from playwright.sync_api import sync_playwright

def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chromium")

@pytest.fixture(scope="session")
def browser_name(request):
    browser = request.config.getoption("--browser")
    allure.dynamic.label("Browser", browser)
    return browser

@pytest.fixture(scope="function")
def page(browser_name, tmp_path_factory):
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        context = browser.new_context(record_video_dir=str(tmp_path_factory.mktemp("videos")))
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        yield page

        context.tracing.stop(path=str(tmp_path_factory.mktemp("traces") / f"trace_{browser_name}.zip"))
        context.close()
        browser.close()
