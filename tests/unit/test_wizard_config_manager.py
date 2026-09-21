"""Unit tests for WizardConfigManager."""

from unittest.mock import MagicMock, patch

from configuration import Config
from data_classes import RefImage
from gui.wizard.config_manager import WizardConfigManager, resolve_model_path
from gui.wizard.steps.draw_rois_base import Roi


def test_resolve_model_path_empty_or_none():
    assert resolve_model_path(None, "/models", "${Var}") == ""
    mock_select = MagicMock(value="")
    assert resolve_model_path(mock_select, "/models", "${Var}") == ""


def test_resolve_model_path_already_templated():
    mock_select = MagicMock(value="${DigitalModelsDir}/class11/model.tflite")
    assert (
        resolve_model_path(mock_select, "/models", "${DigitalModelsDir}")
        == "${DigitalModelsDir}/class11/model.tflite"
    )


def test_resolve_model_path_relative_to_dir():
    mock_select = MagicMock(
        value="/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    )
    res = resolve_model_path(
        mock_select,
        "/config/neuralnets/digital",
        "${DigitalModelsDir}",
    )
    assert res == "${DigitalModelsDir}/class11/dig-class11_1600_s2.tflite"


def test_resolve_model_path_strips_spaces():
    mock_select = MagicMock(value="  class11 / model.tflite  ")
    res = resolve_model_path(mock_select, "/models", "${Var}")
    assert res == "${Var}/class11/model.tflite"


def test_wizard_config_manager_gather_config():
    callbacks = MagicMock()
    orig_config = Config()
    orig_config.log_level = "DEBUG"
    orig_config.config_dir = "/config"
    orig_config.digital_models_dir = "/config/neuralnets/digital"
    orig_config.analog_models_dir = "/config/neuralnets/analog"
    callbacks.get_config.return_value = orig_config

    manager = WizardConfigManager(callbacks=callbacks)

    download_step = MagicMock()
    download_step.url = MagicMock(value="http://cam/snap.jpg")
    download_step.timeout = MagicMock(value=15)
    download_step.minsize = MagicMock(value=5000)

    initial_rotate_step = MagicMock(angle=90.0)

    draw_refs_step = MagicMock(
        rois=[Roi(name="ref1", x=10, y=20, w=30, h=40, enabled=True)]
    )

    adjust_step = MagicMock()
    adjust_step.crop_enabled = MagicMock(value=True)
    adjust_step.crop_x = MagicMock(value=5)
    adjust_step.crop_y = MagicMock(value=10)
    adjust_step.crop_w = MagicMock(value=200)
    adjust_step.crop_h = MagicMock(value=150)
    adjust_step.resize_enabled = MagicMock(value=True)
    adjust_step.resize_w = MagicMock(value=640)
    adjust_step.resize_h = MagicMock(value=480)
    adjust_step.adjust_enabled = MagicMock(value=True)
    adjust_step.adjust_gamma = MagicMock(value=1.2)
    adjust_step.adjust_contrast = MagicMock(value=1.5)
    adjust_step.adjust_brightness = MagicMock(value=1.1)
    adjust_step.adjust_sharpness = MagicMock(value=1.3)
    adjust_step.adjust_color = MagicMock(value=0.8)
    adjust_step.grayscale_enabled = MagicMock(value=True)
    adjust_step.sharpness_mode = MagicMock(value="unsharp")
    adjust_step.unsharp_radius = MagicMock(value=1.5)
    adjust_step.unsharp_amount = MagicMock(value=2.0)
    adjust_step.unsharp_threshold = MagicMock(value=4)
    adjust_step.auto_sharpen_cut_images = MagicMock(value=True)
    adjust_step.autocontrast_enabled = MagicMock(value=True)
    adjust_step.autocontrast_cutoff_low = MagicMock(value=1.0)
    adjust_step.autocontrast_cutoff_high = MagicMock(value=40.0)
    adjust_step.autocontrast_cut_images_enabled = MagicMock(value=True)
    adjust_step.autocontrast_cut_images_cutoff_low = MagicMock(value=1.5)
    adjust_step.autocontrast_cut_images_cutoff_high = MagicMock(value=42.0)
    adjust_step.glare_enabled = MagicMock(value=True)
    adjust_step.glare_mode = MagicMock(value="clahe")
    adjust_step.glare_inpaint_threshold = MagicMock(value=240)
    adjust_step.glare_inpaint_radius = MagicMock(value=4)
    adjust_step.glare_clahe_clip_limit = MagicMock(value=2.5)
    adjust_step.glare_clahe_grid_size = MagicMock(value=10)
    adjust_step.glare_apply_to_cut_images = MagicMock(value=True)
    adjust_step.rotate_angle = MagicMock(value=1.5)

    draw_digital_rois_step = MagicMock()
    draw_digital_rois_step.digital_models_dir = "/config/neuralnets/digital"
    draw_digital_rois_step.rois = [
        Roi(name="digit1", x=10, y=10, w=20, h=30, enabled=True)
    ]
    draw_digital_rois_step.cnn_file = MagicMock(
        value="/config/neuralnets/digital/dig.tflite"
    )
    draw_digital_rois_step.cnn_type = MagicMock(value="class11")
    draw_digital_rois_step.detect_negative_sign = MagicMock(value=True)

    draw_analog_rois_step = MagicMock()
    draw_analog_rois_step.analog_models_dir = "/config/neuralnets/analog"
    draw_analog_rois_step.rois = [
        Roi(name="analog1", x=50, y=50, w=30, h=30, enabled=True)
    ]
    draw_analog_rois_step.cnn_file = MagicMock(
        value="/config/neuralnets/analog/ana.tflite"
    )
    draw_analog_rois_step.cnn_type = MagicMock(value="continuous")

    meter_mock = MagicMock()
    meter_mock.name = "main"
    meter_mock.value = "{digit1}.{analog1}"
    meter_mock.consistency_enabled = True
    meter_mock.allow_negative_rates = False
    meter_mock.max_rate_value = 0.5
    meter_mock.use_previous_value = True
    meter_mock.prevalue_from_file_max_age = 100
    meter_mock.use_extended_resolution = True
    meter_mock.unit = "m3"
    meter_mock.detect_negative_sign = False

    meters_step = MagicMock(meter_params=[meter_mock])
    services_step = MagicMock()

    cfg = manager.gather_config(
        download_image_step=download_step,
        initial_rotate_step=initial_rotate_step,
        draw_refs_step=draw_refs_step,
        adjust_step=adjust_step,
        draw_digital_rois_step=draw_digital_rois_step,
        draw_analog_rois_step=draw_analog_rois_step,
        meters_step=meters_step,
        services_step=services_step,
    )

    assert cfg.image_source.url == "http://cam/snap.jpg"
    assert cfg.image_source.timeout == 15
    assert cfg.image_source.min_size == 5000
    assert cfg.crop.enabled is True
    assert cfg.crop.x == 5
    assert cfg.alignment.rotate_angle == 90.0
    assert cfg.alignment.post_rotate_angle == 1.5
    assert len(cfg.alignment.ref_images) == 1
    assert cfg.alignment.ref_images[0].name == "ref1"
    assert cfg.digital_readout.enabled is True
    assert cfg.digital_readout.detect_negative_sign is True
    assert cfg.analog_readout.enabled is True
    assert len(cfg.meter_configs) == 1
    assert cfg.meter_configs[0].name == "main"
    services_step.apply_to_config.assert_called_once_with(cfg)


def test_wizard_config_manager_save_refs():
    callbacks = MagicMock()
    callbacks.get_config.return_value.config_dir = "/tmp/config"
    manager = WizardConfigManager(callbacks=callbacks)

    draw_refs = MagicMock()
    draw_refs.get_image.return_value = "b64image"
    draw_refs.rois = [Roi(name="ref1", x=10, y=10, w=20, h=20, enabled=True)]

    initial_rotate = MagicMock()
    initial_rotate.get_image.return_value = ""

    with (
        patch("utils.image.convert_base64_str_to_image", return_value=MagicMock()),
        patch("utils.image.cut_image", return_value=MagicMock()),
        patch("utils.image.save_image") as mock_save,
    ):
        manager.save_refs(draw_refs, initial_rotate)
        mock_save.assert_called_once()


def test_wizard_config_manager_helpers():
    callbacks = MagicMock()
    ref = RefImage(name="r1", x=5, y=10, w=20, h=30, file_name="/tmp/r1.jpg")
    callbacks.get_config.return_value.alignment.ref_images = [ref]

    svg = WizardConfigManager.get_refs_from_config(callbacks)
    assert 'x="5"' in svg
    assert 'y="10"' in svg

    dig_step = MagicMock(rois=[Roi(name="d1", x=0, y=0, w=10, h=10, enabled=True)])
    ana_step = MagicMock(rois=[Roi(name="a1", x=0, y=0, w=10, h=10, enabled=True)])
    names = WizardConfigManager.get_digit_names(dig_step, ana_step)
    assert names == ["d1", "a1"]
