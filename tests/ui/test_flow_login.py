import os
import pytest

from sites.loader import load_site_config
from sites.runner import FlowRunner, FlowContext
from utils.locator_registry import LocatorRegistry


@pytest.fixture(scope="session")
def site_name(pytestconfig):
    return pytestconfig.getoption("site", default=os.getenv("TP_SITE", "demo"))


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
