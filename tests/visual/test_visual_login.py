from PIL import ImageChops, Image
import os

def test_login_page_visual_regression(page,browser_name):
    browser_name = request.config.getoption("--browser")
    os.makedirs("actual", exist_ok=True)
    os.makedirs("baseline", exist_ok=True)
    os.makedirs("diff", exist_ok=True)

    screenshot_path = f"actual/login_{browser_name}.png"
    baseline_path = f"baseline/login_{browser_name}.png"
    diff_path = f"diff/login_diff_{browser_name}.png"

    page.goto("https://the-internet.herokuapp.com/login")
    page.screenshot(path=screenshot_path)

    # Optional auto-baseline update
    if os.getenv("UPDATE_BASELINE") == "1":
        Image.open(screenshot_path).save(baseline_path)
        return

    assert os.path.exists(baseline_path), f"Baseline image missing for {browser_name}!"

    actual = Image.open(screenshot_path)
    expected = Image.open(baseline_path)

    assert actual.mode == expected.mode, "Image modes differ!"
    assert actual.size == expected.size, "Image sizes differ!"

    diff = ImageChops.difference(actual, expected)

    if diff.getbbox():
        diff.save(diff_path)
        assert False, f"Visual regression in {browser_name}. See {diff_path}"