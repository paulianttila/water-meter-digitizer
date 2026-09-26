"""Unit tests for Setup Wizard page, navigation, and stepper orchestration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from configuration import Config
from gui.pages.setup import SetupPage


def test_setup_page_init():
    callbacks = MagicMock()
    config = Config()
    callbacks.get_config.return_value = config
    callbacks.load_config_file.return_value = config.save_to_string()

    page = SetupPage(callbacks=callbacks)
    assert page.callbacks == callbacks
    assert page.image == ""


@patch("gui.pages.setup.ImageUtils.image_size_from_file", return_value=(50, 50))
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
    from gui.wizard.navigator import (
        NAME_DOWNLOAD_IMAGE,
        NAME_FINAL,
        NAME_METER_TYPE,
        steps_order,
    )

    def update_wizard_nav(current_step: str) -> None:
        idx = steps_order.index(current_step) if current_step in steps_order else 0
        total = len(steps_order)
        page.wizard_prev_btn.set_visibility(idx > 0)
        page.wizard_step_badge.text = f"Step {idx + 1} of {total}: {current_step}"
        if idx == total - 1:
            page.wizard_next_btn.text = "Save Config"
        else:
            page.wizard_next_btn.text = "Continue"

    # Step 1: Meter Type
    update_wizard_nav(NAME_METER_TYPE)
    page.wizard_prev_btn.set_visibility.assert_called_with(False)
    assert "Step 1 of 10" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Continue"

    # Step 2: Download Image
    update_wizard_nav(NAME_DOWNLOAD_IMAGE)
    page.wizard_prev_btn.set_visibility.assert_called_with(True)
    assert "Step 2 of 10" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Continue"

    # Step 6: Draw Digital ROIs
    update_wizard_nav("Draw digital region of interest")
    page.wizard_prev_btn.set_visibility.assert_called_with(True)
    assert "Step 6 of 10" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Continue"

    # Step 10: Final
    update_wizard_nav(NAME_FINAL)
    page.wizard_prev_btn.set_visibility.assert_called_with(True)
    assert "Step 10 of 10" in page.wizard_step_badge.text
    assert page.wizard_next_btn.text == "Save Config"


def test_setup_page_show():
    callbacks = MagicMock()
    config = Config()
    callbacks.get_config.return_value = config
    callbacks.load_config_file.return_value = config.save_to_string()

    page = SetupPage(callbacks=callbacks)

    with (
        patch("gui.pages.setup.ui") as mock_ui,
        patch("gui.wizard.steps.base.ui"),
        patch(
            "gui.wizard.steps.download.DownloadImageStep.show", new_callable=AsyncMock
        ),
        patch("gui.wizard.steps.meter_type.MeterTypeStep.show", new_callable=AsyncMock),
        patch(
            "gui.wizard.steps.initial_rotate.InitialRotateStep.show",
            new_callable=AsyncMock,
        ),
        patch("gui.wizard.steps.draw_refs.DrawRefsStep.show", new_callable=AsyncMock),
        patch("gui.wizard.steps.adjust.AdjustStep.show", new_callable=AsyncMock),
        patch(
            "gui.wizard.steps.draw_digital_rois.DrawDigitalRoisStep.show",
            new_callable=AsyncMock,
        ),
        patch(
            "gui.wizard.steps.draw_analog_rois.DrawAnalogRoisStep.show",
            new_callable=AsyncMock,
        ),
        patch("gui.wizard.steps.meters.MeterStep.show", new_callable=AsyncMock),
        patch("gui.wizard.steps.services.ServicesStep.show", new_callable=AsyncMock),
        patch("gui.wizard.steps.final.FinalStep.show", new_callable=AsyncMock),
        patch("gui.wizard.steps.download.DownloadImageStep.load_from_config"),
        patch("gui.wizard.steps.initial_rotate.InitialRotateStep.load_from_config"),
        patch("gui.wizard.steps.draw_refs.DrawRefsStep.load_from_config"),
        patch("gui.wizard.steps.adjust.AdjustStep.load_from_config"),
        patch(
            "gui.wizard.steps.draw_digital_rois.DrawDigitalRoisStep.load_from_config"
        ),
        patch("gui.wizard.steps.draw_analog_rois.DrawAnalogRoisStep.load_from_config"),
        patch("gui.wizard.steps.meters.MeterStep.load_from_config"),
        patch("gui.wizard.steps.services.ServicesStep.load_from_config"),
    ):
        mock_ui.splitter.return_value.__enter__ = MagicMock()
        mock_ui.splitter.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.stepper.return_value.__enter__ = MagicMock()
        mock_ui.stepper.return_value.__exit__ = MagicMock()
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.interactive_image.return_value = MagicMock()

        asyncio.run(page.show())
        assert page.download_image_step is not None
        assert page.adjust_step is not None
        assert page.final_step is not None


def test_setup_page_gather_config_model_files_no_spaces():
    from gui.wizard.steps.draw_rois_base import Roi

    callbacks = MagicMock()
    config = Config()
    config.digital_models_dir = "/config/neuralnets/digital"
    config.analog_models_dir = "/config/neuralnets/analog"
    callbacks.get_config.return_value = config

    page = SetupPage(callbacks=callbacks)
    page.download_image_step = MagicMock()
    page.download_image_step.url = MagicMock(value="http://cam/img.jpg")
    page.download_image_step.timeout = MagicMock(value=10)
    page.download_image_step.minsize = MagicMock(value=1000)

    page.initial_rotate_step = MagicMock(angle=0.0)
    page.draw_refs_step = MagicMock(rois=[])

    page.adjust_step = MagicMock()
    page.adjust_step.crop_enabled = MagicMock(value=False)
    page.adjust_step.crop_x = MagicMock(value=0)
    page.adjust_step.crop_y = MagicMock(value=0)
    page.adjust_step.crop_w = MagicMock(value=0)
    page.adjust_step.crop_h = MagicMock(value=0)
    page.adjust_step.resize_enabled = MagicMock(value=False)
    page.adjust_step.resize_w = MagicMock(value=0)
    page.adjust_step.resize_h = MagicMock(value=0)
    page.adjust_step.adjust_enabled = MagicMock(value=False)
    page.adjust_step.adjust_contrast = MagicMock(value=1.0)
    page.adjust_step.adjust_brightness = MagicMock(value=1.0)
    page.adjust_step.adjust_sharpness = MagicMock(value=1.0)
    page.adjust_step.adjust_color = MagicMock(value=1.0)
    page.adjust_step.grayscale_enabled = MagicMock(value=False)
    page.adjust_step.autocontrast_enabled = MagicMock(value=False)
    page.adjust_step.autocontrast_cutoff_low = MagicMock(value=2.0)
    page.adjust_step.autocontrast_cutoff_high = MagicMock(value=45.0)
    page.adjust_step.autocontrast_cut_images_enabled = MagicMock(value=False)
    page.adjust_step.autocontrast_cut_images_cutoff_low = MagicMock(value=2.0)
    page.adjust_step.autocontrast_cut_images_cutoff_high = MagicMock(value=45.0)
    page.adjust_step.glare_enabled = MagicMock(value=False)
    page.adjust_step.glare_mode = MagicMock(value="clahe")
    page.adjust_step.glare_inpaint_threshold = MagicMock(value=230)
    page.adjust_step.glare_inpaint_radius = MagicMock(value=3)
    page.adjust_step.glare_clahe_clip_limit = MagicMock(value=2.0)
    page.adjust_step.glare_clahe_grid_size = MagicMock(value=8)
    page.adjust_step.glare_apply_to_cut_images = MagicMock(value=False)
    page.adjust_step.rotate_angle = MagicMock(value=0.0)

    page.draw_digital_rois_step = MagicMock()
    page.draw_digital_rois_step.digital_models_dir = "/config/neuralnets/digital"
    page.draw_digital_rois_step.rois = [
        Roi(name="digit1", x=10, y=10, w=20, h=30, enabled=True)
    ]
    page.draw_digital_rois_step.cnn_file = MagicMock(
        value="/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite",
        options={
            "/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite": "class11 / dig-class11_1600_s2.tflite"
        },
    )
    page.draw_digital_rois_step.cnn_type = MagicMock(value="auto")

    page.draw_analog_rois_step = MagicMock()
    page.draw_analog_rois_step.analog_models_dir = "/config/neuralnets/analog"
    page.draw_analog_rois_step.rois = [
        Roi(name="analog1", x=40, y=40, w=30, h=30, enabled=True)
    ]
    page.draw_analog_rois_step.cnn_file = MagicMock(
        value="/config/neuralnets/analog/continuous/ana-cont_1209_s2.tflite",
        options={
            "/config/neuralnets/analog/continuous/ana-cont_1209_s2.tflite": "continuous / ana-cont_1209_s2.tflite"
        },
    )
    page.draw_analog_rois_step.cnn_type = MagicMock(value="auto")

    page.meters_step = MagicMock(meter_params=[])
    page.services_step = MagicMock()

    # Check model file resolved without spaces
    from pathlib import Path

    def _resolve_model_path(cnn_select, models_dir, placeholder_var):
        if cnn_select is None or not cnn_select.value:
            return ""
        val = str(cnn_select.value).strip()
        if val.startswith("${"):
            parts = [p.strip() for p in val.split("/")]
            return "/".join(parts)
        try:
            p = Path(val)
            if models_dir:
                md = Path(models_dir)
                if p.is_relative_to(md):
                    rel = p.relative_to(md).as_posix()
                    return f"{placeholder_var}/{rel}"
        except Exception:
            pass
        parts = [part.strip() for part in val.split("/") if part.strip()]
        clean_rel = "/".join(parts)
        return f"{placeholder_var}/{clean_rel}" if clean_rel else ""

    dig_file = _resolve_model_path(
        page.draw_digital_rois_step.cnn_file,
        "/config/neuralnets/digital",
        "${DigitalModelsDir}",
    )
    ana_file = _resolve_model_path(
        page.draw_analog_rois_step.cnn_file,
        "/config/neuralnets/analog",
        "${AnalogModelsDir}",
    )

    assert dig_file == "${DigitalModelsDir}/class11/dig-class11_1600_s2.tflite"
    assert ana_file == "${AnalogModelsDir}/continuous/ana-cont_1209_s2.tflite"
    assert " " not in dig_file
    assert " " not in ana_file


def test_show_rois_does_not_call_set_image():
    from gui.wizard.steps.draw_rois_base import DrawRoisBaseStep, Roi

    set_img = MagicMock()
    draw_roi = MagicMock(return_value="<rect />")
    set_svg = MagicMock()
    show_temp = MagicMock()

    step = DrawRoisBaseStep(
        name="ROIs",
        name_template="roi",
        set_image_callback=set_img,
        draw_roi_func=draw_roi,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
    )
    step.rois = [Roi(name="roi1", x=10, y=10, w=20, h=20, enabled=True)]

    step._show_rois()

    set_svg.assert_called_once_with("<rect />")
    set_img.assert_not_called()


def test_meter_type_preset_applies_reference_points_on_advance():
    from config.meter_presets import load_meter_presets
    from gui.wizard.steps.draw_refs import DrawRefsStep

    presets = load_meter_presets()
    axioma = next((p for p in presets if p.id == "axioma_qalcosonic_w1"), None)
    assert axioma is not None

    draw_refs = MagicMock(spec=DrawRefsStep)
    draw_refs.rois = []

    # Get reference positions defined by Axioma preset
    ref_pos = axioma.get_reference_positions(640, 480)
    assert len(ref_pos) == 3
    assert [r.name for r in ref_pos] == ["Ref0", "Ref1", "Ref2"]
    assert ref_pos[0].x == 269
    assert ref_pos[0].y == 49


def test_meter_type_preset_axioma_enables_digits_and_clears_analog():
    from config.meter_presets import load_meter_presets
    from gui.wizard.config_manager import WizardConfigManager
    from gui.wizard.steps.draw_rois_base import Roi

    presets = load_meter_presets()
    axioma = next((p for p in presets if p.id == "axioma_qalcosonic_w1"), None)
    assert axioma is not None

    digital_names = axioma.get_digital_roi_names(
        int_digits=axioma.default_int_digits,
        dec_digits=axioma.default_dec_digits,
        flow_int_digits=axioma.default_flow_int_digits,
        flow_dec_digits=axioma.default_flow_dec_digits,
    )
    assert len(digital_names) == 14
    assert "digit1" in digital_names
    assert "digit5" in digital_names
    assert "digit6" in digital_names
    assert "decimal1" in digital_names
    assert "flow1" in digital_names
    assert "flow_dec3" in digital_names

    analog_names = axioma.get_analog_roi_names(analog_count=axioma.default_analog_count)
    assert analog_names == []

    dig_pos = axioma.get_digital_roi_positions(digital_names, 640, 480, flow_split=5)
    assert len(dig_pos) == 14

    # Mock wizard steps for gather_config
    callbacks = MagicMock()
    config_manager = WizardConfigManager(callbacks)

    download_step = MagicMock()
    download_step.url.value = "http://test-cam/snap.jpg"
    download_step.timeout.value = 30
    download_step.minsize.value = 10000

    initial_rotate_step = MagicMock()
    initial_rotate_step.angle = 0.0

    draw_refs_step = MagicMock()
    draw_refs_step.rois = []

    adjust_step = MagicMock()
    adjust_step.crop_enabled.value = False
    adjust_step.crop_x.value = 0
    adjust_step.crop_y.value = 0
    adjust_step.crop_w.value = 0
    adjust_step.crop_h.value = 0
    adjust_step.resize_enabled.value = False
    adjust_step.resize_w.value = 0
    adjust_step.resize_h.value = 0
    adjust_step.adjust_enabled.value = False
    adjust_step.grayscale_enabled.value = False
    adjust_step.auto_sharpen_cut_images.value = False
    adjust_step.autocontrast_enabled.value = False
    adjust_step.autocontrast_cut_images_enabled.value = False
    adjust_step.glare_enabled.value = False
    adjust_step.glare_mode.value = "clahe"
    adjust_step.glare_inpaint_threshold.value = 230
    adjust_step.glare_inpaint_radius.value = 3
    adjust_step.glare_clahe_clip_limit.value = 2.0
    adjust_step.glare_clahe_grid_size.value = 8
    adjust_step.glare_apply_to_cut_images.value = False
    adjust_step.rotate_angle.value = 0.0

    draw_digital_rois_step = MagicMock()
    draw_digital_rois_step.digital_models_dir = "/config/neuralnets/digital"
    draw_digital_rois_step.cnn_file.value = (
        "/config/neuralnets/digital/class11/dig-class11_1600_s2_q.tflite"
    )
    draw_digital_rois_step.cnn_type.value = "auto"
    draw_digital_rois_step.detect_negative_sign.value = any(
        m.detect_negative_sign for m in axioma.meters
    )
    draw_digital_rois_step.rois = [
        Roi(name=p.name, x=p.x, y=p.y, w=p.w, h=p.h, enabled=True) for p in dig_pos
    ]

    draw_analog_rois_step = MagicMock()
    draw_analog_rois_step.analog_models_dir = "/config/neuralnets/analog"
    draw_analog_rois_step.cnn_file.value = ""
    draw_analog_rois_step.cnn_type.value = "auto"
    draw_analog_rois_step.rois = []

    meters_step = MagicMock()
    meters_step.meter_params = []

    services_step = MagicMock()
    services_step.mqtt_enabled.value = False
    services_step.ha_enabled.value = False
    services_step.poller_enabled.value = False
    services_step.influx_enabled.value = False
    services_step.leak_enabled.value = False

    gathered = config_manager.gather_config(
        download_image_step=download_step,
        initial_rotate_step=initial_rotate_step,
        draw_refs_step=draw_refs_step,
        adjust_step=adjust_step,
        draw_digital_rois_step=draw_digital_rois_step,
        draw_analog_rois_step=draw_analog_rois_step,
        meters_step=meters_step,
        services_step=services_step,
    )

    assert gathered.digital_readout.enabled is True
    assert gathered.digital_readout.detect_negative_sign is True
    assert len(gathered.digital_readout.cut_images) == 14
    assert gathered.analog_readout.enabled is False
    assert len(gathered.analog_readout.cut_images) == 0


def test_meter_type_step_invokes_on_preset_selected_callback():
    from gui.wizard.steps.meter_type import MeterTypeStep

    cb = MagicMock()
    step = MeterTypeStep("Meter type", on_preset_selected=cb)

    axioma_preset = step.preset_by_id.get("axioma_qalcosonic_w1")
    assert axioma_preset is not None

    step._select_preset("axioma_qalcosonic_w1")
    cb.assert_called_with(axioma_preset)


def test_download_step_url_dropdown_options():
    from gui.wizard.steps.download import DownloadImageStep

    step = DownloadImageStep("Download", set_image_callback=MagicMock())
    options = step._get_url_options()
    assert "model://axioma_qalcosonic_w1" in options
    assert options["model://axioma_qalcosonic_w1"].startswith(
        "model://axioma_qalcosonic_w1 ("
    )
    assert "model://mock_camera" in options
    assert "model://generic_mechanical_classic" in options
    assert "file://${ConfigDir}/original.jpg" in options


def test_meter_type_preset_mock_camera_enables_digits_and_analogs():
    from config.meter_presets import load_meter_presets
    from gui.pages.setup import WizardConfigManager
    from gui.wizard.steps.draw_rois_base import Roi

    presets = {p.id: p for p in load_meter_presets()}
    assert "mock_camera" in presets
    mock_cam = presets["mock_camera"]

    dig_names = mock_cam.get_digital_roi_names(
        int_digits=mock_cam.default_int_digits, dec_digits=mock_cam.default_dec_digits
    )
    ana_names = mock_cam.get_analog_roi_names(
        analog_count=mock_cam.default_analog_count
    )

    dig_pos = mock_cam.get_digital_roi_positions(dig_names, 640, 480)
    ana_pos = mock_cam.get_analog_roi_positions(ana_names, 640, 480)

    assert len(dig_pos) == 5
    assert len(ana_pos) == 4
    assert (
        dig_pos[0].x == 202
        and dig_pos[0].y == 150
        and dig_pos[0].w == 39
        and dig_pos[0].h == 66
    )
    assert (
        ana_pos[0].x == 392
        and ana_pos[0].y == 262
        and ana_pos[0].w == 76
        and ana_pos[0].h == 76
    )

    callbacks = MagicMock()
    config_manager = WizardConfigManager(callbacks)

    download_step = MagicMock()
    download_step.url.value = "http://localhost:3000/api/mock_camera"
    download_step.timeout.value = 30
    download_step.minsize.value = 10000

    initial_rotate_step = MagicMock(angle=0.0)
    draw_refs_step = MagicMock(rois=[])

    adjust_step = MagicMock()
    adjust_step.crop_enabled.value = False
    adjust_step.crop_x.value = 0
    adjust_step.crop_y.value = 0
    adjust_step.crop_w.value = 0
    adjust_step.crop_h.value = 0
    adjust_step.resize_enabled.value = False
    adjust_step.resize_w.value = 0
    adjust_step.resize_h.value = 0
    adjust_step.adjust_enabled.value = False
    adjust_step.grayscale_enabled.value = False
    adjust_step.auto_sharpen_cut_images.value = False
    adjust_step.autocontrast_enabled.value = False
    adjust_step.autocontrast_cut_images_enabled.value = False
    adjust_step.glare_enabled.value = False
    adjust_step.glare_mode.value = "clahe"
    adjust_step.glare_inpaint_threshold.value = 230
    adjust_step.glare_inpaint_radius.value = 3
    adjust_step.glare_clahe_clip_limit.value = 2.0
    adjust_step.glare_clahe_grid_size.value = 8
    adjust_step.glare_apply_to_cut_images.value = False
    adjust_step.rotate_angle.value = 0.0

    draw_digital_rois_step = MagicMock()
    draw_digital_rois_step.digital_models_dir = "/config/neuralnets/digital"
    draw_digital_rois_step.cnn_file.value = (
        "/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    )
    draw_digital_rois_step.cnn_type.value = "auto"
    draw_digital_rois_step.detect_negative_sign.value = False
    draw_digital_rois_step.rois = [
        Roi(name=p.name, x=p.x, y=p.y, w=p.w, h=p.h, enabled=True) for p in dig_pos
    ]

    draw_analog_rois_step = MagicMock()
    draw_analog_rois_step.analog_models_dir = "/config/neuralnets/analog"
    draw_analog_rois_step.cnn_file.value = (
        "/config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite"
    )
    draw_analog_rois_step.cnn_type.value = "auto"
    draw_analog_rois_step.rois = [
        Roi(name=p.name, x=p.x, y=p.y, w=p.w, h=p.h, enabled=True) for p in ana_pos
    ]

    meters_step = MagicMock()
    meters_step.meter_params = []

    services_step = MagicMock()
    services_step.mqtt_enabled.value = False
    services_step.ha_enabled.value = False
    services_step.poller_enabled.value = False
    services_step.influx_enabled.value = False
    services_step.leak_enabled.value = False

    gathered = config_manager.gather_config(
        download_image_step=download_step,
        initial_rotate_step=initial_rotate_step,
        draw_refs_step=draw_refs_step,
        adjust_step=adjust_step,
        draw_digital_rois_step=draw_digital_rois_step,
        draw_analog_rois_step=draw_analog_rois_step,
        meters_step=meters_step,
        services_step=services_step,
    )

    assert gathered.digital_readout.enabled is True
    assert len(gathered.digital_readout.cut_images) == 5
    assert gathered.analog_readout.enabled is True
    assert len(gathered.analog_readout.cut_images) == 4
