"""UI integration tests for application shell, header, and tab navigation
using Playwright.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_app_shell_header_and_tabs_navigation(page: Page, live_server_url: str):
    """Test loading the Web UI at root / (and /gui redirect) and switching tabs."""
    # 1. Open root / directly
    page.goto(f"{live_server_url}/", wait_until="domcontentloaded")

    # 2. Check top navigation header
    expect(page.get_by_text("Water Meter Digitizer")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Interactive Web UI & Setup Wizard")).to_be_visible()
    expect(page.locator("#gui-status-badge")).to_be_visible()

    # 3. Check tabs exist in sidebar
    meter_tab = page.get_by_role("tab", name="Meter")
    services_tab = page.get_by_role("tab", name="Services")
    setup_tab = page.get_by_role("tab", name="Setup")
    config_tab = page.get_by_role("tab", name="Config")
    baselines_tab = page.get_by_role("tab", name="Baselines")
    api_tab = page.get_by_role("tab", name="API Console")
    help_tab = page.get_by_role("tab", name="Help")
    about_tab = page.get_by_role("tab", name="About")

    expect(meter_tab).to_be_visible()
    expect(services_tab).to_be_visible()
    expect(setup_tab).to_be_visible()
    expect(config_tab).to_be_visible()
    expect(baselines_tab).to_be_visible()
    expect(api_tab).to_be_visible()
    expect(help_tab).to_be_visible()
    expect(about_tab).to_be_visible()

    # 4. Test clicking status badge to navigate to Services tab
    page.locator("#gui-status-badge").click()
    expect(page.get_by_text("Services & System Diagnostics")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("System Diagnostics & Health")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Leak & Zero-Flow Monitor")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Services & Integrations")).to_be_visible(timeout=5000)

    # 5. Navigate to Baselines tab
    baselines_tab.click()
    expect(page.get_by_text("Baseline & Previous Values Manager")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_role("button", name="Save Baseline")).to_be_visible()

    # 6. Navigate to API Console tab
    api_tab.click()
    expect(page.get_by_text("REST API Console & Explorer")).to_be_visible(timeout=5000)
    expect(page.get_by_role("button", name="Execute")).to_be_visible()

    # 7. Navigate to About tab
    about_tab.click()
    expect(page.get_by_text("About Water Meter Digitizer")).to_be_visible(timeout=5000)
    expect(page.get_by_text("APPLICATION VERSION")).to_be_visible()

    # 8. Navigate to Help tab
    help_tab.click()
    expect(page.get_by_text("Help & Documentation")).to_be_visible(timeout=5000)

    # 9. Navigate to Config tab
    config_tab.click()
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=5000)

    # 10. Navigate back to Meter tab
    meter_tab.click()
    expect(page.get_by_text("Meter Dashboard")).to_be_visible(timeout=5000)
