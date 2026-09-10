"""UI integration tests for the Services & System Diagnostics page using Playwright."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_services_page_telemetry_and_actions(page: Page, live_server_url: str):
    """Verify system diagnostics, leak monitor, and service cards."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Services").click()

    # 1. Assert headers and subcards
    expect(page.get_by_text("Services & System Diagnostics")).to_be_visible(
        timeout=10000
    )
    expect(page.get_by_text("System Diagnostics & Health")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Leak & Zero-Flow Monitor")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Services & Integrations")).to_be_visible(timeout=5000)

    # 2. Check Diagnostics sub-metrics
    expect(page.get_by_text("Camera Feed")).to_be_visible()
    expect(page.get_by_text("Memory & Process")).to_be_visible()
    expect(page.get_by_text("Image Cache")).to_be_visible()
    expect(page.get_by_text("LiteRT Models")).to_be_visible()

    # 3. Check Leak Monitor sub-metrics & Reset button
    expect(page.get_by_text("Current Flow Rate")).to_be_visible()
    expect(page.get_by_text("Continuous Duration")).to_be_visible()
    expect(page.get_by_role("button", name="Reset Leak State")).to_be_visible()

    # 4. Check Services & Integrations cards
    expect(page.get_by_text("Background Poller")).to_be_visible()
    expect(page.get_by_text("MQTT & Home Assistant")).to_be_visible()
    expect(page.get_by_role("button", name="Trigger Readout")).to_be_visible()
