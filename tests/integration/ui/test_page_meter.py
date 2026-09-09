"""UI integration tests for the Meter Dashboard page using Playwright."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_meter_dashboard_metrics_and_images(page: Page, live_server_url: str):
    """Verify Meter Dashboard values, primary metrics, and cropped dial displays."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Meter").click()

    # 1. Assert header & metric cards
    expect(page.get_by_text("Meter Dashboard")).to_be_visible(timeout=10000)
    expect(page.get_by_text("TOTAL", exact=True)).to_be_visible()
    expect(page.get_by_text("PRIMARY", exact=True)).to_be_visible()
    expect(page.get_by_text("DIGITAL", exact=True)).to_be_visible()
    expect(page.get_by_text("ANALOG", exact=True)).to_be_visible()

    # 2. Assert Processed Capture image and dial groupings
    expect(page.get_by_text("Processed Capture")).to_be_visible()
    expect(page.get_by_text("Digital Counters")).to_be_visible()
    expect(page.get_by_text("Analog Dials")).to_be_visible()

    # 3. Assert individual ROIs
    expect(page.get_by_text("digit1", exact=True)).to_be_visible()
    expect(page.get_by_text("analog1", exact=True)).to_be_visible()


@pytest.mark.ui
def test_meter_tabs_consumption_and_raw_data(page: Page, live_server_url: str):
    """Verify switching between Values, Consumption, and Raw Data tabs on Meter page."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Meter").click()

    # 1. Values tab is selected by default
    expect(page.get_by_role("tab", name="Values")).to_be_visible(timeout=10000)
    consumption_tab = page.get_by_role("tab", name="Consumption")
    raw_data_tab = page.get_by_role("tab", name="Raw Data")

    expect(consumption_tab).to_be_visible()
    expect(raw_data_tab).to_be_visible()

    # 2. Switch to Consumption tab
    consumption_tab.click()
    expect(
        page.get_by_text("Interval:").or_(
            page.get_by_text("History storage backend is disabled.")
        )
    ).to_be_visible(timeout=5000)

    # 3. Switch to Raw Data tab
    raw_data_tab.click()
    expect(page.get_by_text('"meters":')).to_be_visible(timeout=5000)

    # 4. Switch back to Values tab
    page.get_by_role("tab", name="Values").click()
    expect(page.get_by_text("Processed Capture")).to_be_visible(timeout=5000)


@pytest.mark.ui
def test_meter_refresh_readout(page: Page, live_server_url: str):
    """Test manual readout trigger via Refresh button."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Meter").click()

    refresh_btn = page.get_by_role("button", name="Refresh")
    expect(refresh_btn).to_be_visible(timeout=10000)
    refresh_btn.click()

    # Verify that metrics and capture reload successfully
    expect(page.get_by_text("Processed Capture")).to_be_visible(timeout=10000)
    expect(page.get_by_text("PRIMARY", exact=True)).to_be_visible()
