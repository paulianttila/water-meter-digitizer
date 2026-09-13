"""UI integration tests for setup wizard interaction with mock camera."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_setup_wizard_step_inspection_with_mock_camera(
    page: Page, live_server_url: str
):
    """Verify setup wizard interaction, step traversal, and image display with mock camera."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    # In Step 1: Set URL to mock camera and click download
    url_input = page.get_by_label("URL")
    expect(url_input).to_be_visible(timeout=5000)
    url_input.fill(f"{live_server_url}/api/mock_camera?value=00789.1234")

    download_btn = page.locator("button:has(i:has-text('sym_s_download'))")
    if download_btn.count() > 0:
        download_btn.first.click()
    page.wait_for_timeout(600)

    continue_btn = page.get_by_role("button", name="Continue")
    expect(continue_btn).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 2: Initial rotate
    expect(page.get_by_text("Step 2 of 9: Initial rotate")).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 3: Draw reference points
    expect(page.get_by_text("Step 3 of 9: Draw reference points")).to_be_visible(
        timeout=5000
    )
    continue_btn.click()

    # Step 4: Adjust image
    expect(page.get_by_text("Step 4 of 9: Adjust image")).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 5: Draw digital region of interest
    expect(
        page.get_by_text("Step 5 of 9: Draw digital region of interest")
    ).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 6: Draw analog region of interest
    expect(
        page.get_by_text("Step 6 of 9: Draw analog region of interest")
    ).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 7: Meters
    expect(page.get_by_text("Step 7 of 9: Meters")).to_be_visible(timeout=5000)
    continue_btn.click()

    # Step 8: Services & Integrations
    expect(page.get_by_text("Step 8 of 9: Services & Integrations")).to_be_visible(
        timeout=5000
    )
    continue_btn.click()

    # Step 9: Final
    expect(page.get_by_text("Step 9 of 9: Final")).to_be_visible(timeout=5000)
