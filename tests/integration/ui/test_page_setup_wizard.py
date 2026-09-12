"""UI integration tests for the Setup Wizard workflow using Playwright."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
def test_full_9_step_wizard_traversal(page: Page, live_server_url: str):
    """Verify complete step-by-step traversal through the 9-step calibration
    pipeline.
    """
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    continue_btn = page.get_by_role("button", name="Continue")
    back_btn = page.get_by_role("button", name="Back", exact=True)

    # Step 1: Download image
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)
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

    # Step 9: Final / Apply & Finish
    expect(page.get_by_text("Step 9 of 9: Final")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Configuration not yet saved")).to_be_visible(timeout=5000)
    expect(page.get_by_role("button", name="Save Config")).to_be_visible()
    expect(continue_btn).not_to_be_visible()

    # Test backward traversal
    back_btn.click()
    expect(page.get_by_text("Step 8 of 9: Services & Integrations")).to_be_visible(
        timeout=5000
    )
    expect(continue_btn).to_be_visible()


@pytest.mark.ui
def test_setup_wizard_reset_dialog(page: Page, live_server_url: str):
    """Verify reset confirmation dialog."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    reset_btn = page.get_by_role("button", name="Reset to File")
    expect(reset_btn).to_be_visible(timeout=10000)
    reset_btn.click()

    expect(page.get_by_text("Reset Configuration Wizard?")).to_be_visible(timeout=5000)
    cancel_btn = page.get_by_role("button", name="Cancel")
    expect(cancel_btn).to_be_visible()
    cancel_btn.click()
    expect(cancel_btn).not_to_be_visible(timeout=5000)


@pytest.mark.ui
def test_setup_wizard_restore_backup_dialog(page: Page, live_server_url: str):
    """Verify restore from backup modal dialog."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    restore_btn = page.get_by_role("button", name="Restore Backup")
    expect(restore_btn).to_be_visible(timeout=10000)
    restore_btn.click()

    expect(page.get_by_text("Restore Wizard from Backup")).to_be_visible(timeout=5000)
    page.keyboard.press("Escape")


@pytest.mark.ui
def test_setup_wizard_adjust_step_side_by_side_preview(
    page: Page, live_server_url: str
):
    """Test Step 4 Adjust image dual-card side-by-side comparison mode toggle."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    continue_btn = page.get_by_role("button", name="Continue")
    expect(continue_btn).to_be_visible(timeout=10000)

    # Advance Step 1 -> 2 -> 3 -> 4
    continue_btn.click()  # -> Step 2
    expect(page.get_by_text("Step 2 of 9: Initial rotate")).to_be_visible(timeout=5000)
    continue_btn.click()  # -> Step 3
    expect(page.get_by_text("Step 3 of 9: Draw reference points")).to_be_visible(
        timeout=5000
    )
    continue_btn.click()  # -> Step 4
    expect(page.get_by_text("Step 4 of 9: Adjust image")).to_be_visible(timeout=5000)

    # In Single mode, header displays "Adjusted Image Preview"
    expect(page.get_by_text("Adjusted Image Preview")).to_be_visible(timeout=5000)

    # Click 'Side-by-Side' radio label
    page.get_by_text("Side-by-Side", exact=True).click()

    # Assert both original and adjusted image headers appear
    expect(page.get_by_text("Adjusted Image", exact=True)).to_be_visible(timeout=5000)
    expect(page.get_by_text("Original Image", exact=True)).to_be_visible(timeout=5000)

    # Navigate back one step to Step 3
    back_btn = page.get_by_role("button", name="Back", exact=True)
    back_btn.click()
    expect(page.get_by_text("Step 3 of 9: Draw reference points")).to_be_visible(
        timeout=5000
    )


@pytest.mark.ui
def test_setup_wizard_start_clean_dialog(page: Page, live_server_url: str):
    """Verify start clean configuration dialog and action."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()

    clean_btn = page.get_by_role("button", name="Start Clean")
    expect(clean_btn).to_be_visible(timeout=10000)
    clean_btn.click()

    expect(page.get_by_text("Start Clean Configuration?")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Create safety backup before clearing")).to_be_visible()

    cancel_btn = page.get_by_role("button", name="Cancel")
    expect(cancel_btn).to_be_visible()
    cancel_btn.click()
