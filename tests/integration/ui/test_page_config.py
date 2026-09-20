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
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=10000)

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
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=10000)

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


@pytest.mark.ui
def test_config_test_config_button(page: Page, live_server_url: str):
    """Verify Test Config button in Configuration Editor is visible and clickable."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=10000)

    test_cfg_btn = page.get_by_role("button", name="Test Config")
    expect(test_cfg_btn).to_be_visible(timeout=10000)
    test_cfg_btn.click()

    expect(page.get_by_text("Running digitizer engine test").first).to_be_visible(
        timeout=10000
    )


@pytest.mark.ui
def test_config_history_test_backup(page: Page, live_server_url: str):
    """Verify testing a backup snapshot from the history dialog."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Config").click()
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=10000)

    # Open history dialog
    history_btn = page.get_by_role("button", name="Snapshots & Diffs")
    expect(history_btn).to_be_visible(timeout=10000)
    history_btn.click()

    # Create a snapshot
    tag_input = page.get_by_placeholder(
        "Snapshot label / description (e.g. Pre-calibration)"
    )
    expect(tag_input).to_be_visible(timeout=5000)
    tag_input.fill("Playwright Test Snapshot")

    take_btn = page.get_by_role("button", name="Take Snapshot")
    expect(take_btn).to_be_visible()
    take_btn.click()

    # Wait for snapshot row to appear with Test button
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_text("Playwright Test Snapshot").first).to_be_visible(
        timeout=5000
    )
    test_btn = dialog.get_by_role("button", name="Test", exact=True).first
    expect(test_btn).to_be_visible()
    test_btn.click()

    # Check test modal opens
    expect(page.get_by_text("Running digitizer engine test").first).to_be_visible(
        timeout=10000
    )
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
