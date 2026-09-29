"""Unit tests for WizardNavigator."""

from unittest.mock import MagicMock

from gui.wizard.navigator import (
    NAME_ADJUST,
    NAME_DOWNLOAD_IMAGE,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_REFS,
    NAME_FINAL,
    NAME_INITIAL_ROTATE,
    NAME_METER_TYPE,
    NAME_METERS,
    NAME_SERVICES,
    WizardNavigator,
)


def test_wizard_navigator_is_step_forward():
    assert WizardNavigator.is_step_forward(NAME_DOWNLOAD_IMAGE, NAME_METER_TYPE) is True
    assert (
        WizardNavigator.is_step_forward(NAME_METER_TYPE, NAME_DOWNLOAD_IMAGE) is False
    )
    assert (
        WizardNavigator.is_step_forward(NAME_INITIAL_ROTATE, NAME_DOWNLOAD_IMAGE)
        is True
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

    # For download, meter type, & initial rotate, source is download
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_DOWNLOAD_IMAGE, download_step, rotate_step, adjust_step
        )
        == "img_download"
    )
    assert (
        WizardNavigator.get_source_image_for_step(
            NAME_METER_TYPE, download_step, rotate_step, adjust_step
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
    WizardNavigator.update_wizard_nav(NAME_METER_TYPE, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(False)
    assert "Step 1 of 10" in badge.text
    next_btn.set_visibility.assert_called_with(True)
    assert next_btn.text == "Continue"

    # Step 2
    WizardNavigator.update_wizard_nav(NAME_DOWNLOAD_IMAGE, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(True)
    assert "Step 2 of 10" in badge.text

    # Step 6
    WizardNavigator.update_wizard_nav(NAME_DRAW_DIGITAL_ROIS, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(True)
    assert "Step 6 of 10" in badge.text
    next_btn.set_visibility.assert_called_with(True)

    # Step 10 (Final)
    WizardNavigator.update_wizard_nav(NAME_FINAL, prev_btn, badge, next_btn)
    prev_btn.set_visibility.assert_called_with(True)
    assert "Step 10 of 10" in badge.text
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


def test_wizard_navigator_validate_transition():
    callbacks = MagicMock()
    navigator = WizardNavigator(callbacks)

    # 1. Backwards transition always allowed
    can_move, msg = navigator.validate_transition(
        current_step=NAME_DRAW_REFS,
        target_step=NAME_DOWNLOAD_IMAGE,
        step_getter=lambda name: None,
    )
    assert can_move is True
    assert msg == ""

    # 2. Blocked if current step validate() fails
    bad_step = MagicMock()
    bad_step.validate.return_value = (False, "Please configure items")
    can_move, msg = navigator.validate_transition(
        current_step=NAME_METER_TYPE,
        target_step=NAME_DOWNLOAD_IMAGE,
        step_getter=lambda name: bad_step,
    )
    assert can_move is False
    assert msg == "Please configure items"

    # 3. Blocked if target step is after Download image and download step has no image
    good_step = MagicMock()
    good_step.validate.return_value = (True, "")
    dl_step = MagicMock()
    dl_step.get_image.return_value = ""

    def getter(name: str):
        if name == NAME_INITIAL_ROTATE:
            return good_step
        if name == NAME_DOWNLOAD_IMAGE:
            return dl_step
        return None

    can_move, msg = navigator.validate_transition(
        current_step=NAME_INITIAL_ROTATE,
        target_step=NAME_DRAW_REFS,
        step_getter=getter,
    )
    assert can_move is False
    assert "Please download an image" in msg

    # 4. Success when current step valid and download has image
    dl_step.get_image.return_value = "base64data"
    can_move, msg = navigator.validate_transition(
        current_step=NAME_INITIAL_ROTATE,
        target_step=NAME_DRAW_REFS,
        step_getter=getter,
    )
    assert can_move is True
    assert msg == ""


def test_step_validation_methods():
    from gui.wizard.steps.base import BaseStep
    from gui.wizard.steps.download import DownloadImageStep
    from gui.wizard.steps.draw_refs import DrawRefsStep
    from gui.wizard.steps.draw_rois_base import DrawRoisBaseStep, Roi
    from gui.wizard.steps.meters import Meter, MeterStep

    # BaseStep returns (True, "")
    base = BaseStep("base")
    assert base.validate() == (True, "")

    # DownloadImageStep requires image
    dl = DownloadImageStep("dl", set_image_callback=MagicMock())
    assert dl.validate()[0] is False
    dl.image = "sample_base64"
    assert dl.validate() == (True, "")

    # DrawRefsStep requires 0 or 3 points
    refs = DrawRefsStep(
        "refs",
        "ref",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    assert refs.validate() == (True, "")  # 0 points is valid (alignment skipped)
    refs.rois = [Roi(name="ref1", w=10, h=10)]
    assert refs.validate()[0] is False  # 1 point invalid
    refs.rois = [
        Roi(name="ref1", w=10, h=10),
        Roi(name="ref2", w=10, h=10),
        Roi(name="ref3", w=10, h=10),
    ]
    assert refs.validate() == (True, "")  # 3 points valid
    refs.rois.append(Roi(name="ref4", w=10, h=10))
    assert refs.validate()[0] is False  # 4 points invalid

    # DrawRoisBaseStep checks positive dimensions
    rois_step = DrawRoisBaseStep(
        "rois",
        "roi",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value=""),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    rois_step.rois = [Roi(name="r1", w=0, h=10)]
    assert rois_step.validate()[0] is False
    rois_step.rois = [Roi(name="r1", w=10, h=10)]
    assert rois_step.validate() == (True, "")

    # MeterStep requires at least 1 meter, valid names, and sequences
    m_step = MeterStep(
        "meters",
        set_image_callback=MagicMock(),
        get_digit_names_func=MagicMock(return_value=["digit1"]),
    )
    assert m_step.validate()[0] is False  # no meters

    m = Meter(["digit1"], "total")
    m.meter.name = "total"
    m.digits.value = []
    m_step.meters = [m]
    assert m_step.validate()[0] is False  # no sequence

    m.digits.value = ["digit1"]
    assert m_step.validate() == (True, "")  # valid!
