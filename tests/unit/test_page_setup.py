from unittest.mock import AsyncMock, MagicMock, patch
from configuration import Config
from gui.page_setup import SetupPage


def test_setup_page_init():
    callbacks = MagicMock()
    config = Config()
    callbacks.get_config.return_value = config
    callbacks.load_config_file.return_value = config.save_to_string()

    page = SetupPage(callbacks=callbacks)
    assert page.callbacks == callbacks
    assert page.image == ""


@patch("gui.page_setup.ImageUtils.image_size_from_file", return_value=(50, 50))
def test_setup_page_reset_from_config(mock_size):
    callbacks = MagicMock()
    config = Config()
    config.image_source.url = "http://test-cam/snap.jpg"
    config.crop.enabled = True
    config.crop.x = 10
    config.crop.y = 20
    config.crop.w = 100
    config.crop.h = 100
    config_ini_str = config.save_to_string()

    callbacks.get_config.return_value = config
    callbacks.load_config_file.return_value = config_ini_str

    page = SetupPage(callbacks=callbacks)

    # Initialize mocked steps
    page.download_image_step = MagicMock()
    page.download_image_step.download = AsyncMock()
    page.initial_rotate_step = MagicMock()
    page.draw_refs_step = MagicMock()
    page.adjust_step = MagicMock()
    page.draw_digital_rois_step = MagicMock()
    page.draw_analog_rois_step = MagicMock()
    page.meters_step = MagicMock()
    page.services_step = MagicMock()
    page.stepper = MagicMock()

    # Create fresh config from string
    fresh_config = Config()
    fresh_config.load_from_string(config_ini_str)

    # Call load_from_config across steps
    page.download_image_step.load_from_config(fresh_config.image_source)
    page.initial_rotate_step.load_from_config(fresh_config.alignment)
    page.draw_refs_step.load_from_config(fresh_config.alignment.ref_images)
    page.adjust_step.load_from_config(fresh_config)
    page.draw_digital_rois_step.load_from_config(fresh_config.digital_readout)
    page.draw_analog_rois_step.load_from_config(fresh_config.analog_readout)
    page.meters_step.load_from_config(fresh_config.meter_configs)
    page.services_step.load_from_config(fresh_config)

    page.download_image_step.load_from_config.assert_called_once_with(
        fresh_config.image_source
    )
    page.adjust_step.load_from_config.assert_called_once_with(fresh_config)
    page.services_step.load_from_config.assert_called_once_with(fresh_config)


def test_wizard_navigation_flow():
    callbacks = MagicMock()
    page = SetupPage(callbacks=callbacks)

    # Initialize navigation controls
    page.wizard_prev_btn = MagicMock()
    page.wizard_step_badge = MagicMock()
    page.wizard_next_btn = MagicMock()
    page.stepper = MagicMock()
    page.final_step = MagicMock()

    # Define update helper inside test mirroring implementation
    from gui.page_setup import steps_order, NAME_DOWNLOAD_IMAGE, NAME_FINAL

    def update_wizard_nav(current_step: str) -> None:
        idx = steps_order.index(current_step) if current_step in steps_order else 0
        total = len(steps_order)
        page.wizard_prev_btn.set_visibility(idx > 0)
        page.wizard_step_badge.text = f"Step {idx + 1} of {total}: {current_step}"
        if idx == total - 1:
            page.wizard_next_btn.text = "Save Config"
        else:
            page.wizard_next_btn.text = "Continue"

    # Step 1: Download Image
    update_wizard_nav(NAME_DOWNLOAD_IMAGE)
    page.wizard_prev_btn.set_visibility.assert_called_with(False)
    assert "Step 1 of 9" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Continue"

    # Step 5: Draw Digital ROIs
    update_wizard_nav("Draw digital region of interest")
    page.wizard_prev_btn.set_visibility.assert_called_with(True)
    assert "Step 5 of 9" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Continue"

    # Step 9: Final
    update_wizard_nav(NAME_FINAL)
    page.wizard_prev_btn.set_visibility.assert_called_with(True)
    assert "Step 9 of 9" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Save Config"
