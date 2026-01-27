import pytest

from sites.loader import load_site_config
from sites.runner import FlowRunner, FlowContext
from utils.locator_registry import LocatorRegistry
from utils.travel_dates import next_friday_to_monday_trip


@pytest.mark.parametrize("site_name", ["booking", "expedia"])
def test_search_brussels_friday_monday(page, site_name):
    cfg = load_site_config(site_name)
    checkin, checkout = next_friday_to_monday_trip()

    vars = {
        "DESTINATION": "Brussels",
        "CHECKIN": checkin,
        "CHECKOUT": checkout,
    }

    registry = LocatorRegistry(site=cfg.name, locators=cfg.locators)
    ctx = FlowContext(base_url=cfg.base_url, vars=vars, registry=registry)
    FlowRunner(ctx).run(page, "search", cfg.flows)

    assert page.url
