import os
import sys
import subprocess
from pathlib import Path

import pytest
import allure
from playwright.sync_api import Error as PlaywrightError, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _is_missing_browser_error(message: str) -> bool:
    lowered = message.lower()
    return "executable doesn't exist" in lowered or "playwright install" in lowered


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
    return request.config.getoption("--browser")


@pytest.fixture(scope="function")
def page(browser_name, tmp_path_factory):
    artifact_root = Path(os.getenv("PW_ARTIFACT_DIR", "artifacts/playwright"))
    video_dir = artifact_root / "videos" / browser_name
    trace_dir = artifact_root / "traces" / browser_name
    video_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = getattr(p, browser_name).launch(headless=True)
        except PlaywrightError as exc:
            message = str(exc)
            if _is_missing_browser_error(message):
                install_result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", browser_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if install_result.returncode != 0:
                    pytest.skip(
                        "Playwright browser install failed for "
                        f"{browser_name}:\n{install_result.stdout}\n"
                        f"{install_result.stderr}"
                    )
                try:
                    browser = getattr(p, browser_name).launch(headless=True)
                except PlaywrightError:
                    pytest.skip(
                        f"Playwright browser binaries missing for {browser_name}: {message}"
                    )
            else:
                raise
        context = browser.new_context(record_video_dir=str(video_dir))
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        # ⬇️ Add browser label here, in test context
        allure.dynamic.label("browser", browser_name)
        allure.dynamic.parameter("browser", browser_name)

        yield page

        context.tracing.stop(path=str(trace_dir / f"trace_{browser_name}.zip"))
        context.close()
        browser.close()
