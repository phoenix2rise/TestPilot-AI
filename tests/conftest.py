import os
from pathlib import Path

import pytest
import allure
from playwright.sync_api import sync_playwright


def pytest_addoption(parser):
    # pytest-playwright (and some other plugins) already define --browser.
    # If it exists, adding it again raises:
    # ValueError: option names {'--browser'} already added
    try:
        parser.addoption("--browser", action="store", default="chromium")
    except ValueError:
        # Option already registered by another plugin: keep it.
        pass


@pytest.fixture(scope="session")
def browser_name(request):
    # Works whether --browser came from our addoption or a plugin.
    return request.config.getoption("--browser")


@pytest.fixture(scope="function")
def page(browser_name, tmp_path_factory):
    artifact_root = Path(os.getenv("PW_ARTIFACT_DIR", "artifacts/playwright"))
    video_dir = artifact_root / "videos" / browser_name
    trace_dir = artifact_root / "traces" / browser_name
    video_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        context = browser.new_context(record_video_dir=str(video_dir))
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        allure.dynamic.label("browser", browser_name)
        allure.dynamic.parameter("browser", browser_name)

        yield page

        context.tracing.stop(path=str(trace_dir / f"trace_{browser_name}.zip"))
        context.close()
        browser.close()
