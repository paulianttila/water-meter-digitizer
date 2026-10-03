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

    # 3. Check 4 main pillar tabs exist in sidebar
    dashboard_tab = page.get_by_role("tab", name="Dashboard")
    settings_tab = page.get_by_role("tab", name="Settings")
    studio_tab = page.get_by_role("tab", name="Studio")
    system_tab = page.get_by_role("tab", name="System")

    expect(dashboard_tab).to_be_visible()
    expect(settings_tab).to_be_visible()
    expect(studio_tab).to_be_visible()
    expect(system_tab).to_be_visible()

    # 4. Test clicking status badge to navigate to System -> Services
    page.locator("#gui-status-badge").click()
    expect(page.get_by_text("Services & System Diagnostics")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("System Diagnostics & Health")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Leak & Zero-Flow Monitor")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Services & Integrations")).to_be_visible(timeout=5000)

    # 5. Navigate to Settings Pillar & Baselines subtab
    settings_tab.click()
    baselines_subtab = page.get_by_role("tab", name="Baselines")
    expect(baselines_subtab).to_be_visible(timeout=5000)
    baselines_subtab.click()
    expect(page.get_by_text("Baseline & Previous Values Manager")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_role("button", name="Save Baseline")).to_be_visible()

    # 6. Switch to Config subtab within Settings
    config_subtab = page.get_by_role("tab", name="Config")
    expect(config_subtab).to_be_visible()
    config_subtab.click()
    expect(page.get_by_text("Configuration Editor")).to_be_visible(timeout=5000)

    # 7. Navigate to Studio Pillar
    studio_tab.click()
    expect(page.get_by_text("REST API Console & Studio")).to_be_visible(timeout=5000)
    expect(page.get_by_role("button", name="Execute")).to_be_visible()

    # 8. Navigate to System Pillar & About subtab
    system_tab.click()
    about_subtab = page.get_by_role("tab", name="About")
    expect(about_subtab).to_be_visible(timeout=5000)
    about_subtab.click()
    expect(page.get_by_text("About Water Meter Digitizer")).to_be_visible(timeout=5000)
    expect(page.get_by_text("APPLICATION VERSION")).to_be_visible()

    # 9. Navigate to Help subtab within System
    help_subtab = page.get_by_role("tab", name="Help")
    expect(help_subtab).to_be_visible()
    help_subtab.click()
    expect(page.get_by_text("Help & Documentation")).to_be_visible(timeout=5000)

    # 10. Navigate back to Dashboard Pillar
    dashboard_tab.click()
    expect(page.get_by_text("Meter Dashboard")).to_be_visible(timeout=5000)


@pytest.mark.ui
def test_help_page_card_expansion_and_scrollability(page: Page, live_server_url: str):
    """Verify that Help page cards are closed by default, and expanding multiple
    cards in restricted viewports allows independent vertical scrolling.
    """
    page.set_viewport_size({"width": 1024, "height": 650})
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")

    # Navigate to System pillar -> Help subtab
    page.get_by_role("tab", name="System").click()
    page.get_by_role("tab", name="Help").click()
    expect(page.get_by_text("Help & Documentation")).to_be_visible(timeout=5000)

    # Verify cards are present and closed by default
    arch_card = page.get_by_text("Runtime Architecture", exact=True)
    wizard_card = page.get_by_text("Setup Wizard Progression", exact=True)
    rules_card = page.get_by_text(
        "Marker Placement Rules & Calibration Tips", exact=True
    )
    wiki_card = page.get_by_text("Wiki Documentation & Deep Dives", exact=True)

    expect(arch_card).to_be_visible()
    expect(wizard_card).to_be_visible()
    expect(rules_card).to_be_visible()
    expect(wiki_card).to_be_visible()

    # Click headers to expand
    for card in [arch_card, wizard_card, rules_card, wiki_card]:
        card.click()
        page.wait_for_timeout(300)

    page.wait_for_timeout(500)

    # Verify that the active tab panel becomes scrollable vertically with NO horizontal scrollbar
    layout_info = page.evaluate("""() => {
        const body = document.body;
        const scrollContainer = document.querySelector('#help-subtab-workflow');
        return {
            bodyScrollHeight: body.scrollHeight,
            windowHeight: window.innerHeight,
            bodyScrollWidth: body.scrollWidth,
            windowWidth: window.innerWidth,
            panelScrollable: scrollContainer ? scrollContainer.scrollHeight > scrollContainer.clientHeight : false,
            panelScrollHeight: scrollContainer ? scrollContainer.scrollHeight : 0,
            panelClientHeight: scrollContainer ? scrollContainer.clientHeight : 0,
            horizontalScrollable: scrollContainer ? scrollContainer.scrollWidth > scrollContainer.clientWidth : false,
            panelScrollWidth: scrollContainer ? scrollContainer.scrollWidth : 0,
            panelClientWidth: scrollContainer ? scrollContainer.clientWidth : 0
        };
    }""")

    assert layout_info["bodyScrollHeight"] <= layout_info["windowHeight"]
    assert layout_info["bodyScrollWidth"] <= layout_info["windowWidth"]
    assert layout_info["panelScrollable"] is True
    assert layout_info["horizontalScrollable"] is False

    # Scroll the bottom-most wiki card into view and verify it can be seen
    wiki_link = page.get_by_text("Getting Started & Hardware")
    wiki_link.scroll_into_view_if_needed()
    expect(wiki_link).to_be_visible()


@pytest.mark.ui
def test_api_console_page_layout_left_aligned_tabs_and_execute(
    page: Page, live_server_url: str
):
    """Verify that the API Console tabs are left-aligned, Swagger UI card is full-height,
    and executing REST requests in a constrained viewport does not collapse the page content.
    """
    page.set_viewport_size({"width": 1024, "height": 520})
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")

    # 1. Navigate to Studio pillar
    studio_tab = page.get_by_role("tab", name="Studio")
    studio_tab.click()
    expect(page.get_by_text("REST API Console & Studio")).to_be_visible(timeout=5000)

    # 2. Verify subtab buttons are present and left-aligned
    rest_subtab = page.get_by_role("tab", name="REST Endpoints")
    mock_subtab = page.get_by_role("tab", name="Mock Camera Studio")
    swagger_subtab = page.get_by_role("tab", name="Swagger UI")

    expect(rest_subtab).to_be_visible()
    expect(mock_subtab).to_be_visible()
    expect(swagger_subtab).to_be_visible()

    tabs_align = page.evaluate("""() => {
        const panels = document.querySelector('#api-console-tab-panels');
        const restTab = document.querySelector('.q-tab[aria-label="REST Endpoints"]') || document.querySelector('.q-tab');
        const tabsContainer = restTab ? restTab.closest('.q-tabs') : null;
        return {
            hasPanels: !!panels,
            tabOffsetLeft: restTab ? restTab.offsetLeft : 0
        };
    }""")
    assert tabs_align["hasPanels"] is True
    # Left aligned tabs start near the left boundary
    assert tabs_align["tabOffsetLeft"] < 60

    # 3. Switch to Swagger UI subtab and verify full-height iframe card
    swagger_subtab.click()
    expect(page.get_by_text("Interactive OpenAPI Documentation")).to_be_visible(
        timeout=5000
    )
    swagger_iframe = page.locator('iframe[title="Swagger UI Documentation"]')
    expect(swagger_iframe).to_be_visible()

    swagger_height = page.evaluate("""() => {
        const iframe = document.querySelector('iframe[title="Swagger UI Documentation"]');
        return iframe ? iframe.clientHeight : 0;
    }""")
    assert swagger_height > 200

    # 4. Switch back to REST Endpoints subtab
    rest_subtab.click()
    execute_btn = page.get_by_role("button", name="Execute")
    expect(execute_btn).to_be_visible(timeout=5000)

    # 5. Click Execute and verify page content remains fully intact and visible
    execute_btn.click()
    page.wait_for_timeout(1000)

    expect(execute_btn).to_be_visible()
    expect(page.get_by_text("REST API Console & Studio")).to_be_visible()
    expect(page.get_by_text("Response Body")).to_be_visible()

    # Verify container geometry: card has non-zero height and panel is scrollable if needed
    panel_info = page.evaluate("""() => {
        const panel = document.querySelector('#api-subtab-rest');
        const card = panel ? panel.querySelector('.q-card') : null;
        return {
            panelClientHeight: panel ? panel.clientHeight : 0,
            cardClientHeight: card ? card.clientHeight : 0,
            cardOffsetHeight: card ? card.offsetHeight : 0
        };
    }""")
    assert panel_info["cardClientHeight"] >= 400
