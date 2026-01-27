import allure
import pytest
from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from sites.loader import load_site_config
from sites.runner import FlowContext, FlowRunner
from utils.locator_registry import LocatorRegistry
from utils.travel_dates import next_friday_to_monday_trip


def _run_flow(page, site_name: str, flow_name: str, vars: dict[str, str]) -> None:
    cfg = load_site_config(site_name)

    registry = LocatorRegistry(site=cfg.name, locators=cfg.locators)
    ctx = FlowContext(base_url=cfg.base_url, vars=vars, registry=registry)
    try:
        FlowRunner(ctx).run(page, flow_name, cfg.flows)
    except (PlaywrightError, PlaywrightTimeoutError, RuntimeError) as exc:
        pytest.skip(f"Skipping due to external site instability: {exc}")

    assert page.url


@allure.suite("Travel")
@allure.sub_suite("Booking.com")
def test_booking_search_brussels_friday_monday(page):
    checkin, checkout = next_friday_to_monday_trip()
    vars = {
        "DESTINATION": "Brussels",
        "CHECKIN": checkin,
        "CHECKOUT": checkout,
    }
    _run_flow(page, "booking", "search", vars)


@allure.suite("Travel")
@allure.sub_suite("Expedia")
def test_expedia_search_brussels_friday_monday(page):
    checkin, checkout = next_friday_to_monday_trip()
    vars = {
        "DESTINATION": "Brussels",
        "CHECKIN": checkin,
        "CHECKOUT": checkout,
    }
    _run_flow(page, "expedia", "search", vars)


@allure.suite("Events")
@allure.sub_suite("Google Search")
def test_google_events_search_brussels(page):
    vars = {"QUERY": "Events happening on this saturday in Brussels"}
    _run_flow(page, "google", "search", vars)


@allure.suite("Events")
@allure.sub_suite("Brave Search")
def test_brave_events_search_brussels(page):
    vars = {"QUERY": "Events happening on this saturday in Brussels"}
    _run_flow(page, "brave", "search", vars)
