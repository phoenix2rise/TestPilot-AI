from PIL import ImageChops, Image
import os

def test_login_page_visual_regression(page):
    page.goto("https://the-internet.herokuapp.com/login")
    page.screenshot(path="actual/login.png")

    baseline_path = "baseline/login.png"
    assert os.path.exists(baseline_path), "Baseline image missing!"

    actual = Image.open("actual/login.png")
    expected = Image.open(baseline_path)
    diff = ImageChops.difference(actual, expected)

    assert not diff.getbbox(), "Visual regression detected!"
