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
        parser.addoption("--browser", action="store", default="all")
    except ValueError:
        # Option already registered by another plugin: keep it.
        pass


def pytest_generate_tests(metafunc):
    if "browser_name" not in metafunc.fixturenames:
        return
    browser_opt = metafunc.config.getoption("--browser")
    if browser_opt:
        browser_opt = browser_opt.strip()
    if not browser_opt or browser_opt == "all":
        browsers = ["chromium", "firefox", "webkit"]
    else:
        browsers = [item.strip() for item in browser_opt.split(",") if item.strip()]
    metafunc.parametrize("browser_name", browsers, scope="session")


@pytest.fixture(scope="session")
def browser_name(request):
    return request.param


def _safe_artifact_name(nodeid: str) -> str:
    return (
        nodeid.replace("/", "_")
        .replace("\\", "_")
        .replace("::", "__")
        .replace(" ", "_")
        .replace("[", "_")
        .replace("]", "_")
    )


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="function")
def page(browser_name, request, tmp_path_factory):
    artifact_root = Path(os.getenv("PW_ARTIFACT_DIR", "artifacts/playwright"))
    video_dir = artifact_root / "videos" / browser_name
    trace_dir = artifact_root / "traces" / browser_name
    screenshot_dir = artifact_root / "screenshots" / browser_name
    video_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    headless = not _env_flag("PW_HEADED", "0")
    slow_mo = int(os.getenv("PW_SLOW_MO", "0"))
    user_agent = os.getenv(
        "PW_USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    locale = os.getenv("PW_LOCALE", "en-US")
    viewport_width = int(os.getenv("PW_VIEWPORT_WIDTH", "1365"))
    viewport_height = int(os.getenv("PW_VIEWPORT_HEIGHT", "768"))

    with sync_playwright() as p:
        try:
            browser = getattr(p, browser_name).launch(headless=headless, slow_mo=slow_mo)
        except PlaywrightError as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message:
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", browser_name],
                    check=False,
                )
                try:
                    browser = getattr(p, browser_name).launch(headless=True)
                except PlaywrightError:
                    pytest.skip(
                        f"Playwright browser binaries missing for {browser_name}: {message}"
                    )
            else:
                raise
        context = browser.new_context(
            record_video_dir=str(video_dir),
            user_agent=user_agent,
            locale=locale,
            viewport={"width": viewport_width, "height": viewport_height},
        )
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        def _close_popup(new_page):
            if new_page is page:
                return
            try:
                new_page.close()
            except PlaywrightError:
                pass

        page.on("popup", _close_popup)
        context.on("page", _close_popup)
        page.on("dialog", lambda dialog: dialog.dismiss())

        # ⬇️ Add browser label here, in test context
        allure.dynamic.label("browser", browser_name)
        allure.dynamic.parameter("browser", browser_name)

        yield page

        test_id = _safe_artifact_name(request.node.nodeid)
        screenshot_path = screenshot_dir / f"{test_id}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            if screenshot_path.exists():
                allure.attach.file(
                    str(screenshot_path),
                    name="screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
        except PlaywrightError:
            pass

        trace_path = trace_dir / f"trace_{browser_name}_{test_id}.zip"
        try:
            context.tracing.stop(path=str(trace_path))
        except PlaywrightError:
            trace_path = None

        context.close()

        if trace_path and trace_path.exists():
            allure.attach.file(
                str(trace_path),
                name="trace",
                attachment_type=allure.attachment_type.ZIP,
            )

        if page.video:
            try:
                video_path = Path(page.video.path())
            except PlaywrightError:
                video_path = None
            if video_path and video_path.exists():
                allure.attach.file(
                    str(video_path),
                    name="video",
                    attachment_type=allure.attachment_type.WEBM,
                )

        browser.close()
