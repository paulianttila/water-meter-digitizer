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
    expect(page.get_by_role("button", name="Test Config")).to_be_visible()
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
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

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
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

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
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

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
    side_by_side_label = page.get_by_text("Side-by-Side", exact=True)
    expect(side_by_side_label).to_be_visible()
    side_by_side_label.click()

    # In Side-by-Side mode, both "Original Image" and "Adjusted Image" headers are visible
    expect(page.get_by_text("Original Image", exact=True)).to_be_visible(timeout=5000)
    expect(page.get_by_text("Adjusted Image", exact=True)).to_be_visible()


@pytest.mark.ui
def test_setup_wizard_start_clean_dialog(page: Page, live_server_url: str):
    """Verify start clean configuration dialog and action."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    clean_btn = page.get_by_role("button", name="Start Clean")
    expect(clean_btn).to_be_visible(timeout=10000)
    clean_btn.click(force=True)

    expect(page.get_by_text("Start Clean Configuration?")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Create safety backup before clearing")).to_be_visible()

    cancel_btn = page.get_by_role("button", name="Cancel")
    expect(cancel_btn).to_be_visible()
    cancel_btn.click()


@pytest.mark.ui
def test_setup_wizard_tall_step_scrollability(page: Page, live_server_url: str):
    """Verify that on tall wizard steps (like Step 4 Adjust image):
    - The main page and left image panel remain fixed in view.
    - Only the wizard step container scrolls independently.
    - Docked navigation buttons (Back/Continue) remain visible and functional.
    """
    page.set_viewport_size({"width": 1024, "height": 600})
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    continue_btn = page.get_by_role("button", name="Continue")
    back_btn = page.get_by_role("button", name="Back", exact=True)

    # Advance to Step 4 (Adjust image) which has many sub-cards and exceeds 600px height
    continue_btn.click()
    expect(page.get_by_text("Step 2 of 9: Initial rotate")).to_be_visible(timeout=5000)
    continue_btn.click()
    expect(page.get_by_text("Step 3 of 9: Draw reference points")).to_be_visible(
        timeout=5000
    )
    continue_btn.click()
    expect(page.get_by_text("Step 4 of 9: Adjust image")).to_be_visible(timeout=5000)

    # Verify that the body is not scrolling, the left panel stays pinned, and the stepper scrolls
    layout_info = page.evaluate("""() => {
        const body = document.body;
        const leftPanel = document.querySelector('.q-splitter__before');
        const stepper = document.querySelector('.q-stepper');
        const stepperContainer = stepper ? stepper.parentElement : null;
        const leftRect = leftPanel ? leftPanel.getBoundingClientRect() : null;

        return {
            windowHeight: window.innerHeight,
            bodyScrollHeight: body.scrollHeight,
            bodyClientHeight: body.clientHeight,
            leftPanelTop: leftRect ? leftRect.top : 0,
            stepperScrollable: stepperContainer ? stepperContainer.scrollHeight > stepperContainer.clientHeight : false
        };
    }""")

    # Body must not be scrolling
    assert layout_info["bodyScrollHeight"] <= layout_info["windowHeight"]
    # Left image panel stays pinned right below the top navbar (~56px)
    assert 50 <= layout_info["leftPanelTop"] <= 70
    # The stepper content container inside the right panel must be scrollable
    assert layout_info["stepperScrollable"] is True

    # Continue and Back buttons remain docked and directly visible in the viewport
    expect(continue_btn).to_be_visible()
    continue_btn.click()

    # Verify advance to Step 5
    expect(
        page.get_by_text("Step 5 of 9: Draw digital region of interest")
    ).to_be_visible(timeout=5000)

    # Back button remains docked and directly visible
    expect(back_btn).to_be_visible()
    back_btn.click()
    expect(page.get_by_text("Step 4 of 9: Adjust image")).to_be_visible(timeout=5000)


@pytest.mark.ui
def test_setup_wizard_roi_shift_move(page: Page, live_server_url: str):
    """Verify that Shift+dragging on the image canvas translates the selected ROI
    without changing its dimensions and syncs X/Y number fields.
    """
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    continue_btn = page.get_by_role("button", name="Continue")

    # Advance to Step 3: Draw reference points
    continue_btn.click()  # -> Step 2
    expect(page.get_by_text("Step 2 of 9: Initial rotate")).to_be_visible(timeout=5000)
    continue_btn.click()  # -> Step 3
    expect(page.get_by_text("Step 3 of 9: Draw reference points")).to_be_visible(
        timeout=5000
    )

    # Click the '+' button to add a new reference ROI
    add_btn = page.get_by_role("button", name="Add", exact=True)
    if not add_btn.is_visible():
        add_btn = page.locator('button:has-text("Add")')
    add_btn.click()
    page.wait_for_timeout(500)

    # Get the last ROI row inputs for X, Y, W, H
    x_inputs = page.locator('input[aria-label="X"]')
    y_inputs = page.locator('input[aria-label="Y"]')
    w_inputs = page.locator('input[aria-label="W"]')
    h_inputs = page.locator('input[aria-label="H"]')

    last_idx = x_inputs.count() - 1
    init_x = int(float(x_inputs.nth(last_idx).input_value()))
    init_y = int(float(y_inputs.nth(last_idx).input_value()))
    init_w = int(float(w_inputs.nth(last_idx).input_value()))
    init_h = int(float(h_inputs.nth(last_idx).input_value()))

    # Find the image element inside splitter.before
    img = page.locator(".q-splitter__before img")
    expect(img).to_be_visible()

    # Perform Shift+drag gesture on the canvas
    box = img.bounding_box()
    assert box is not None

    start_x = box["x"] + 100
    start_y = box["y"] + 100
    end_x = start_x + 50
    end_y = start_y + 40

    page.keyboard.down("Shift")
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(end_x, end_y, steps=5)
    page.mouse.up()
    page.keyboard.up("Shift")
    page.wait_for_timeout(500)

    # Verify that X and Y coordinates changed, while W and H remained exactly the same
    new_x = int(float(x_inputs.nth(last_idx).input_value()))
    new_y = int(float(y_inputs.nth(last_idx).input_value()))
    new_w = int(float(w_inputs.nth(last_idx).input_value()))
    new_h = int(float(h_inputs.nth(last_idx).input_value()))

    assert (new_x != init_x) or (new_y != init_y)
    assert new_w == init_w
    assert new_h == init_h


@pytest.mark.ui
def test_setup_wizard_shift_move_cursor_and_hud_indicator(
    page: Page, live_server_url: str
):
    """Verify that holding Shift activates move cursor and displays the MOVE MODE HUD badge."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    # Initial state: shift-move-active class absent, indicator hidden
    indicator = page.locator("#roi-move-indicator")
    expect(indicator).not_to_be_visible()

    img = page.locator(".q-splitter__before img")
    expect(img).to_be_visible()

    initial_cursor = img.evaluate("el => window.getComputedStyle(el).cursor")
    assert initial_cursor != "move"

    # Press Shift key down
    page.keyboard.down("Shift")
    page.wait_for_timeout(200)

    # Indicator should become visible and body should have shift-move-active class
    expect(indicator).to_be_visible()
    has_class = page.evaluate(
        "() => document.body.classList.contains('shift-move-active')"
    )
    assert has_class is True

    # Image element cursor should now evaluate to "move"
    active_cursor = img.evaluate("el => window.getComputedStyle(el).cursor")
    assert active_cursor == "move"

    # Release Shift key
    page.keyboard.up("Shift")
    page.wait_for_timeout(200)

    # Indicator hidden and cursor restored
    expect(indicator).not_to_be_visible()
    restored_cursor = img.evaluate("el => window.getComputedStyle(el).cursor")
    assert restored_cursor != "move"


@pytest.mark.ui
def test_setup_wizard_canvas_shortcuts_bar(page: Page, live_server_url: str):
    """Verify that the quick canvas shortcuts bar displays in drawing steps and reacts to Shift."""
    page.goto(f"{live_server_url}/gui", wait_until="domcontentloaded")
    page.get_by_role("tab", name="Setup").click()
    expect(page.get_by_text("Step 1 of 9: Download image")).to_be_visible(timeout=10000)

    continue_btn = page.get_by_role("button", name="Continue")
    # Step 1 -> Step 2 (Initial rotate)
    continue_btn.click()
    expect(page.get_by_text("Step 2 of 9: Initial rotate")).to_be_visible(timeout=5000)

    # Step 2 -> Step 3 (Draw reference points)
    continue_btn.click()
    expect(
        page.get_by_text("Step 3 of 9: Draw reference points", exact=False)
    ).to_be_visible(timeout=5000)

    # Verify shortcut bar elements
    shortcut_bar = page.locator(".roi-shortcut-bar")
    expect(shortcut_bar).to_be_visible()

    draw_chip = shortcut_bar.locator(".shortcut-chip-draw")
    expect(draw_chip).to_be_visible()
    expect(draw_chip).to_contain_text("Draw / Resize")

    move_chip = shortcut_bar.locator(".shortcut-chip-move")
    expect(move_chip).to_be_visible()
    expect(move_chip).to_contain_text("Move")

    active_tag = move_chip.locator(".shortcut-move-active-tag")
    expect(active_tag).not_to_be_visible()

    # Press Shift down -> active tag becomes visible
    page.keyboard.down("Shift")
    page.wait_for_timeout(200)
    expect(active_tag).to_be_visible()

    # Release Shift -> active tag hidden again
    page.keyboard.up("Shift")
    page.wait_for_timeout(200)
    expect(active_tag).not_to_be_visible()
