"""Playwright UI integration tests for the REST API Console & Mock Camera Studio."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_api_console_and_mock_camera_studio_ui(page: Page, live_server_url: str):
    """Test API Console tabs, REST endpoint execution, and Mock Camera Studio controls."""
    # 1. Open Web UI
    page.goto(f"{live_server_url}/", wait_until="domcontentloaded")

    # 2. Navigate to API Console tab
    api_tab = page.get_by_role("tab", name="API Console")
    expect(api_tab).to_be_visible(timeout=10000)
    api_tab.click()

    # 3. Assert header and sub-tabs
    expect(page.get_by_text("REST API Console & Studio")).to_be_visible(timeout=5000)
    rest_subtab = page.get_by_role("tab", name="REST Endpoints")
    mock_subtab = page.get_by_role("tab", name="Mock Camera Studio")
    expect(rest_subtab).to_be_visible()
    expect(mock_subtab).to_be_visible()

    # 4. Test REST Endpoints tab execution
    expect(page.get_by_role("button", name="Execute")).to_be_visible()
    page.get_by_role("button", name="Execute").click()
    expect(page.get_by_text("HTTP 200")).to_be_visible(timeout=10000)

    # 5. Switch to Mock Camera Studio sub-tab
    mock_subtab.click()
    expect(page.get_by_text("Procedural Mock Camera Parameters")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("Live Generated Camera Picture")).to_be_visible(
        timeout=5000
    )
    query_btn = page.get_by_role("button", name="Make Query / Update Snapshot")
    expect(query_btn).to_be_visible()
    expect(page.get_by_role("button", name="Copy Mock URL")).to_be_visible()
    expect(page.get_by_role("button", name="Set as [ImageSource] URL")).to_be_visible()

    # 6. Click Make Query / Update Snapshot and verify mock camera preview and telemetry
    query_btn.click()
    expect(page.locator("#mock-camera-preview-img")).to_be_visible(timeout=10000)
    expect(page.get_by_text("00452.91241")).to_be_visible(timeout=5000)

    # 7. Test Reset Defaults button
    reset_defaults_btn = page.get_by_role("button", name="Reset Defaults")
    expect(reset_defaults_btn).to_be_visible()
    reset_defaults_btn.click()
    expect(
        page.get_by_text("Mock camera parameters reset to default values")
    ).to_be_visible(timeout=5000)

    # 8. Test Reset Ticker button
    reset_btn = page.get_by_role("button", name="Reset Ticker")
    expect(reset_btn).to_be_visible()
    reset_btn.click()
    expect(page.get_by_text("Mock camera ticker reset to 100.0")).to_be_visible(
        timeout=5000
    )
