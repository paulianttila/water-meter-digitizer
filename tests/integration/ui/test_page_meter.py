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
    expect(page.get_by_text("Good", exact=False).first).to_be_visible()

    # 2. Assert Processed Capture image and dial groupings
    expect(page.get_by_text("Processed Capture")).to_be_visible()
    expect(page.get_by_text("Digital Counters")).to_be_visible()
    expect(page.get_by_text("Analog Dials")).to_be_visible()

    # 3. Test Inspect ROIs modal
    inspect_btn = page.get_by_role("button", name="Inspect ROIs")
    expect(inspect_btn).to_be_visible()
    inspect_btn.click()
    expect(page.get_by_text("ROI & Reference Marks Inspector")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("Alignment References")).to_be_visible()
    page.keyboard.press("Escape")

    # 4. Assert individual ROIs
    expect(page.get_by_text("digit1", exact=True)).to_be_visible()
    expect(page.get_by_text("analog1", exact=True)).to_be_visible()


@pytest.mark.ui
def test_meter_tabs_values_statistics_and_history(page: Page, live_server_url: str):
    """Verify switching between Values, Statistics, and History tabs on Meter page."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Meter").click()

    # 1. Values tab is selected by default
    expect(page.get_by_role("tab", name="Values")).to_be_visible(timeout=10000)
    stats_tab = page.get_by_role("tab", name="Statistics")
    history_tab = page.get_by_role("tab", name="History")
    expect(stats_tab).to_be_visible()
    expect(history_tab).to_be_visible()

    # 2. Switch to Statistics tab and test demo seeding
    stats_tab.click()
    expect(page.get_by_text("TOTAL CONSUMPTION")).to_be_visible(timeout=5000)
    expect(page.get_by_text("AVG PER DAILY")).to_be_visible(timeout=5000)

    more_btn = page.locator("button:has(i:text('more_vert'))").first
    expect(more_btn).to_be_visible(timeout=5000)
    more_btn.click()

    seed_item = page.get_by_text("Seed 14d Demo Data")
    expect(seed_item).to_be_visible(timeout=5000)
    seed_item.click()

    expect(page.get_by_text("Seeded 14 days of demo readings")).to_be_visible(
        timeout=5000
    )
    expect(page.locator(".nicegui-echart")).to_be_visible(timeout=5000)

    # 3. Switch to History tab and check table columns
    history_tab.click()
    expect(page.get_by_text("Timestamp (UTC)")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Meter Readout")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Digital Digits")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Analog Dials")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Quality / Status")).to_be_visible(timeout=5000)

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
