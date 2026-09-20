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

    # 8b. Test Tune Config button opens Dedicated Mock Meter Configuration dialog
    tune_config_btn = page.get_by_role("button", name="Tune Config")
    expect(tune_config_btn).to_be_visible()
    tune_config_btn.click()
    expect(page.get_by_text("Dedicated Mock Meter Configuration")).to_be_visible(
        timeout=5000
    )
    reset_sync_btn = page.get_by_role("button", name="Reset to Canvas Sync")
    expect(reset_sync_btn).to_be_visible()

    # Test Raw INI Editor tab
    raw_tab = page.get_by_role("tab", name="Raw INI Editor")
    expect(raw_tab).to_be_visible()
    raw_tab.click()
    expect(page.get_by_text("Direct INI Configuration Payload")).to_be_visible()
    expect(reset_sync_btn).to_be_visible()

    for vp_w, vp_h in [(1280, 800), (950, 700), (750, 600)]:
        page.set_viewport_size({"width": vp_w, "height": vp_h})
        page.wait_for_timeout(300)
        card_box = page.locator(".q-dialog .q-card").first.bounding_box()
        btn_box = reset_sync_btn.bounding_box()
        assert card_box is not None
        assert btn_box is not None
        # Assert Reset to Canvas Sync button is fully contained within the dialog card horizontally
        assert btn_box["x"] >= card_box["x"] - 5
        assert btn_box["x"] + btn_box["width"] <= card_box["x"] + card_box["width"] + 5

    cancel_btn = page.get_by_role("button", name="Cancel")
    expect(cancel_btn).to_be_visible()
    cancel_btn.click()
    expect(page.get_by_text("Dedicated Mock Meter Configuration")).not_to_be_visible(
        timeout=5000
    )

    # 9. Switch to Swagger UI sub-tab
    swagger_subtab = page.get_by_role("tab", name="Swagger UI")
    expect(swagger_subtab).to_be_visible()
    swagger_subtab.click()

    expect(page.get_by_text("Interactive OpenAPI Documentation")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_role("button", name="Open /docs in New Tab")).to_be_visible()
    expect(page.get_by_role("button", name="Open ReDoc")).to_be_visible()
    expect(page.get_by_role("button", name="OpenAPI Spec (JSON)")).to_be_visible()
    expect(page.locator('iframe[title="Swagger UI Documentation"]')).to_be_visible()
