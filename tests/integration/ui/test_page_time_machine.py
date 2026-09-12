"""Playwright UI integration tests for the Time Machine historical scrubber and inspector."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_time_machine_navigation_and_controls(page: Page, live_server_url: str):
    """Test Time Machine tab layout, playback controls, and comparison cards."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")

    # 1. Switch to Meter page -> Time Machine tab
    meter_tab = page.get_by_role("tab", name="Meter")
    expect(meter_tab).to_be_visible(timeout=5000)
    meter_tab.click()

    tm_tab = page.get_by_role("tab", name="Time Machine")
    expect(tm_tab).to_be_visible(timeout=5000)
    tm_tab.click()

    # 2. Header and Inspection viewports
    expect(page.get_by_text("Time Machine & Frame Inspector")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("Historical Frame", exact=False).first).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("Latest Live Frame", exact=False)).to_be_visible(
        timeout=5000
    )

    # 3. Detection ROI breakdown cards
    expect(page.get_by_text("Digital Drums", exact=False).first).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_text("Analog Dials", exact=False).first).to_be_visible(
        timeout=5000
    )

    # 4. Playback controls and speed selector
    play_btn = page.locator("button:has(i:text('play_arrow'))").first
    if play_btn.is_visible():
        play_btn.click()
        # Verify countdown timer badge becomes visible
        expect(page.get_by_text("Next:", exact=False)).to_be_visible(timeout=5000)
        # Pause playback
        pause_btn = page.locator("button:has(i:text('pause'))").first
        if pause_btn.is_visible():
            pause_btn.click()

    # 5. Toggle filters (e.g. Frames Only)
    frames_switch = page.get_by_text("Frames Only")
    if frames_switch.is_visible():
        frames_switch.click()
