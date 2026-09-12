import asyncio
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
    from gui.page_setup import NAME_DOWNLOAD_IMAGE, NAME_FINAL, steps_order

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


def test_setup_page_show():
    callbacks = MagicMock()
    config = Config()
    callbacks.get_config.return_value = config
    callbacks.load_config_file.return_value = config.save_to_string()

    page = SetupPage(callbacks=callbacks)

    with (
        patch("gui.page_setup.ui") as mock_ui,
        patch("gui.step_base.ui"),
        patch("gui.step_download.DownloadImageStep.show", new_callable=AsyncMock),
        patch("gui.step_initial_rotate.InitialRotateStep.show", new_callable=AsyncMock),
        patch("gui.step_draw_refs.DrawRefsStep.show", new_callable=AsyncMock),
        patch("gui.step_adjust.AdjustStep.show", new_callable=AsyncMock),
        patch(
            "gui.step_draw_digital_rois.DrawDigitalRoisStep.show",
            new_callable=AsyncMock,
        ),
        patch(
            "gui.step_draw_analog_rois.DrawAnalogRoisStep.show", new_callable=AsyncMock
        ),
        patch("gui.step_meters.MeterStep.show", new_callable=AsyncMock),
        patch("gui.step_services.ServicesStep.show", new_callable=AsyncMock),
        patch("gui.step_final.FinalStep.show", new_callable=AsyncMock),
        patch("gui.step_download.DownloadImageStep.load_from_config"),
        patch("gui.step_initial_rotate.InitialRotateStep.load_from_config"),
        patch("gui.step_draw_refs.DrawRefsStep.load_from_config"),
        patch("gui.step_adjust.AdjustStep.load_from_config"),
        patch("gui.step_draw_digital_rois.DrawDigitalRoisStep.load_from_config"),
        patch("gui.step_draw_analog_rois.DrawAnalogRoisStep.load_from_config"),
        patch("gui.step_meters.MeterStep.load_from_config"),
        patch("gui.step_services.ServicesStep.load_from_config"),
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
    from gui.step_draw_rois_base import Roi

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
