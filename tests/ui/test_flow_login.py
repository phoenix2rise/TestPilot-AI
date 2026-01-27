import os
import pytest

from sites.loader import load_site_config
from sites.runner import FlowRunner, FlowContext
from utils.locator_registry import LocatorRegistry


def pytest_addoption(parser):
    # Add --site safely (ignore if already present)
    try:
        parser.addoption("--site", action="store", default=os.getenv("TP_SITE", "demo"))
    except ValueError:
        pass


@pytest.fixture(scope="session")
def site_name(pytestconfig):
    return pytestconfig.getoption("--site")


def test_login_flow(page, site_name):
    cfg = load_site_config(site_name)

    creds = {
        "USER": os.getenv("USER", "demo@example.com"),
        "PASS": os.getenv("PASS", "password"),
    }

    registry = LocatorRegistry(site=cfg.name, locators=cfg.locators)
    ctx = FlowContext(base_url=cfg.base_url, vars=creds, registry=registry)
    FlowRunner(ctx).run(page, "login", cfg.flows)

    assert page.url
