"""UI integration tests for application shell, header, and tab navigation
using Playwright.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_app_shell_header_and_tabs_navigation(page: Page, live_server_url: str):
    """Test loading the Web UI and switching between all primary tabs."""
    # 1. Open the NiceGUI dashboard
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")

    # 2. Check top navigation header
    expect(page.get_by_text("Water Meter Digitizer")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Interactive Web UI & Setup Wizard")).to_be_visible()
    expect(page.locator("#gui-status-badge")).to_be_visible()

    # 3. Check tabs exist
    meter_tab = page.get_by_role("tab", name="Meter")
    setup_tab = page.get_by_role("tab", name="Setup")
    config_tab = page.get_by_role("tab", name="Config")
    help_tab = page.get_by_role("tab", name="Help")
    about_tab = page.get_by_role("tab", name="About")

    expect(meter_tab).to_be_visible()
    expect(setup_tab).to_be_visible()
    expect(config_tab).to_be_visible()
    expect(help_tab).to_be_visible()
    expect(about_tab).to_be_visible()

    # 4. Navigate to About tab
    about_tab.click()
    expect(page.get_by_text("About Water Meter Digitizer")).to_be_visible(timeout=5000)
    expect(page.get_by_text("APPLICATION VERSION")).to_be_visible()

    # 5. Navigate to Help tab
    help_tab.click()
    expect(page.get_by_text("Help & Documentation")).to_be_visible(timeout=5000)

    # 6. Navigate to Config tab
    config_tab.click()
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=5000)

    # 7. Navigate back to Meter tab
    meter_tab.click()
    expect(page.get_by_text("Meter Dashboard")).to_be_visible(timeout=5000)
