"""Unit tests for WizardNavigator."""

from unittest.mock import MagicMock

from gui.wizard_navigator import (
    NAME_ADJUST,
    NAME_DOWNLOAD_IMAGE,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_REFS,
    NAME_FINAL,
    NAME_INITIAL_ROTATE,
    NAME_METERS,
    NAME_SERVICES,
    WizardNavigator,
)


def test_wizard_navigator_is_step_forward():
    assert (
        WizardNavigator.is_step_forward(NAME_INITIAL_ROTATE, NAME_DOWNLOAD_IMAGE)
        is True
    )
    assert (
        WizardNavigator.is_step_forward(NAME_DOWNLOAD_IMAGE, NAME_INITIAL_ROTATE)
        is False
    )
    assert WizardNavigator.is_step_forward(NAME_FINAL, NAME_SERVICES) is True
    assert WizardNavigator.is_step_forward("unknown", NAME_SERVICES) is False


def test_wizard_navigator_get_source_image():
    download_step = MagicMock()
    download_step.get_image.return_value = "img_download"
    rotate_step = MagicMock()
    rotate_step.get_image.return_value = "img_rotate"
    adjust_step = MagicMock()
    adjust_step.get_image.return_value = "img_adjust"

    # For download & initial rotate, source is download
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_DOWNLOAD_IMAGE, download_step, rotate_step, adjust_step
        )
        == "img_download"
    )
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_INITIAL_ROTATE, download_step, rotate_step, adjust_step
        )
        == "img_download"
    )

    # For refs and adjust, source is rotated image
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_DRAW_REFS, download_step, rotate_step, adjust_step
        )
        == "img_rotate"
    )
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_ADJUST, download_step, rotate_step, adjust_step
        )
        == "img_rotate"
    )

    # For subsequent steps, source is adjusted image
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_DRAW_DIGITAL_ROIS, download_step, rotate_step, adjust_step
        )
        == "img_adjust"
    )
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_METERS, download_step, rotate_step, adjust_step
        )
        == "img_adjust"
    )


def test_wizard_navigator_update_wizard_nav():
    prev_btn = MagicMock()
    badge = MagicMock()
    next_btn = MagicMock()

    # Step 1
    WizardNavigator.update_wizard_nav(NAME_DOWNLOAD_IMAGE, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(False)
    assert "Step 1 of 9" in badge.text
    next_btn.set_visibility.assert_called_with(True)
    assert next_btn.text == "Continue"

    # Step 5
    WizardNavigator.update_wizard_nav(NAME_DRAW_DIGITAL_ROIS, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(True)
    assert "Step 5 of 9" in badge.text
    next_btn.set_visibility.assert_called_with(True)

    # Step 9 (Final)
    WizardNavigator.update_wizard_nav(NAME_FINAL, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(True)
    assert "Step 9 of 9" in badge.text
    next_btn.set_visibility.assert_called_with(False)


def test_wizard_navigator_handle_stepper_change():
    callbacks = MagicMock()
    callbacks.get_config.return_value.config_dir = "/tmp/config"
    navigator = WizardNavigator(callbacks=callbacks)

    download_step = MagicMock()
    download_step.get_image.return_value = "img1"
    rotate_step = MagicMock()
    rotate_step.get_image.return_value = "img2"
    refs_step = MagicMock(rois=[])
    refs_step.get_image.return_value = "img3"
    adjust_step = MagicMock()
    adjust_step.get_image.return_value = "img4"
    adjust_step.autocontrast_cut_images_enabled = MagicMock(value=False)
    adjust_step.autocontrast_cut_images_cutoff_low = MagicMock(value=2.0)
    adjust_step.autocontrast_cut_images_cutoff_high = MagicMock(value=45.0)
    adjust_step.glare_enabled = MagicMock(value=False)
    adjust_step.glare_apply_to_cut_images = MagicMock(value=False)
    adjust_step.glare_mode = MagicMock(value="clahe")
    adjust_step.glare_inpaint_threshold = MagicMock(value=230)
    adjust_step.glare_inpaint_radius = MagicMock(value=3)
    adjust_step.glare_clahe_clip_limit = MagicMock(value=2.0)
    adjust_step.glare_clahe_grid_size = MagicMock(value=8)
    adjust_step.adjust_enabled = MagicMock(value=False)
    adjust_step.auto_sharpen_cut_images = MagicMock(value=False)
    adjust_step.unsharp_radius = MagicMock(value=1.0)
    adjust_step.unsharp_amount = MagicMock(value=1.5)
    adjust_step.unsharp_threshold = MagicMock(value=3)

    digital_step = MagicMock()
    digital_step.get_image.return_value = "img5"
    analog_step = MagicMock()
    analog_step.get_image.return_value = "img6"
    meters_step = MagicMock()
    meters_step.get_image.return_value = "img7"
    services_step = MagicMock()
    services_step.get_image.return_value = "img8"
    final_step = MagicMock()
    final_step.get_image.return_value = "img9"

    set_image_fn = MagicMock()
    set_comparison_fn = MagicMock()
    update_svg_fn = MagicMock()
    gather_config_fn = MagicMock()

    prev_btn = MagicMock()
    badge = MagicMock()
    next_btn = MagicMock()

    # Change to draw refs
    navigator.handle_stepper_change(
        step=NAME_DRAW_REFS,
        download_image_step=download_step,
        initial_rotate_step=rotate_step,
        draw_refs_step=refs_step,
        adjust_step=adjust_step,
        draw_digital_rois_step=digital_step,
        draw_analog_rois_step=analog_step,
        meters_step=meters_step,
        services_step=services_step,
        final_step=final_step,
        set_image_fn=set_image_fn,
        set_comparison_image_fn=set_comparison_fn,
        update_svg_fn=update_svg_fn,
        gather_config_fn=gather_config_fn,
        wizard_prev_btn=prev_btn,
        wizard_step_badge=badge,
        wizard_next_btn=next_btn,
    )

    assert navigator.refs_enabled_in_image is True
    assert navigator.digital_rois_enabled_in_image is False
    assert navigator.analog_rois_enabled_in_image is False
    refs_step._show_rois.assert_called_once()
    assert navigator.previous_step == NAME_DRAW_REFS
