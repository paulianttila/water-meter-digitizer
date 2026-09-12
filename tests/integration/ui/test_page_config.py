"""UI integration tests for the Configuration Editor page using Playwright."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_config_editor_display_and_validate(page: Page, live_server_url: str):
    """Verify configuration text editor loading and syntax validation."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()

    # 1. Assert header and actions
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=10000)
    expect(page.get_by_role("button", name="Reload File")).to_be_visible()
    expect(page.get_by_role("button", name="Save File")).to_be_visible()
    expect(page.get_by_role("button", name="Hot-Reload")).to_be_visible()
    validate_btn = page.get_by_role("button", name="Validate")
    expect(validate_btn).to_be_visible()

    # 2. Click Validate button
    validate_btn.click()
    expect(page.get_by_text("Syntax is valid")).to_be_visible(timeout=5000)


@pytest.mark.ui
def test_config_inspect_json_dialog(page: Page, live_server_url: str):
    """Verify Inspect JSON dialog opening and content inspection."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()

    # 1. Click Inspect JSON button
    inspect_btn = page.get_by_role("button", name="Inspect JSON")
    expect(inspect_btn).to_be_visible(timeout=10000)
    inspect_btn.click()

    # 2. Verify JSON inspection modal opens
    expect(page.get_by_text("Parsed Configuration (JSON)")).to_be_visible(timeout=5000)
    expect(page.get_by_text('"image_source":')).to_be_visible()

    # 3. Close modal
    page.keyboard.press("Escape")


@pytest.mark.ui
def test_config_history_dialog(page: Page, live_server_url: str):
    """Verify opening and closing the configuration history modal."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()

    # 1. Open Snapshots dialog
    history_btn = page.get_by_role("button", name="Snapshots & Diffs")
    expect(history_btn).to_be_visible(timeout=10000)
    history_btn.click()

    # 2. Assert history modal content
    expect(page.get_by_text("Configuration History")).to_be_visible(timeout=5000)
    expect(
        page.get_by_placeholder("Snapshot label / description (e.g. Pre-calibration)")
    ).to_be_visible()

    # 3. Close dialog
    page.keyboard.press("Escape")


@pytest.mark.ui
def test_config_hot_reload_shows_refresh_warning(page: Page, live_server_url: str):
    """Verify hot-reload triggers warning banner with Refresh Page action."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()

    # 1. Trigger hot-reload from toolbar
    hot_reload_btn = page.get_by_role("button", name="Hot-Reload")
    expect(hot_reload_btn).to_be_visible(timeout=10000)
    hot_reload_btn.click()

    # 2. Wait for reload banner to appear
    banner = page.locator("#reload-warning-banner")
    expect(banner).to_be_visible(timeout=10000)
    expect(
        page.get_by_text("Configuration has been hot-reloaded into runtime")
    ).to_be_visible()
    expect(page.get_by_role("button", name="Refresh Page")).to_be_visible()
