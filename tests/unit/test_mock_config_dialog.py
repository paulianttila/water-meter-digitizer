from unittest.mock import MagicMock, patch

import pytest

from configuration import Config
from gui.api_console.mock_config_dialog import (
    ANALOG_MODELS,
    DIGITAL_MODELS,
    MockConfigDialog,
)
from simulator.meter_generator import MeterImageGenerator


@pytest.fixture
def mock_callbacks():
    cb = MagicMock()
    cb.get_config.return_value = Config()
    return cb


def test_config_to_ini_string_and_from_ini_string():
    cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
    cfg.meter_configs[0].name = "test_meter"
    cfg.meter_configs[0].unit = "gal"
    cfg.image_processing.autocontrast.enabled = True

    ini_text = cfg.to_ini_string()
    assert "[ImageSource]" in ini_text
    assert "[Meter.test_meter]" in ini_text
    assert "[Digits.digit1]" in ini_text
    assert "[Analog.analog1]" in ini_text

    loaded = Config.from_ini_string(ini_text)
    assert loaded.meter_configs[0].name == "test_meter"
    assert loaded.meter_configs[0].unit == "gal"
    assert loaded.image_processing.autocontrast.enabled is True
    assert len(loaded.digital_readout.cut_images) == 5
    assert len(loaded.analog_readout.cut_images) == 4


def test_mock_config_dialog_initialization():
    cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
    dialog = MockConfigDialog(
        current_config=cfg,
        width=640,
        height=480,
        mock_url="http://localhost:3000/api/mock_camera/feed.jpg",
    )
    assert dialog.width == 640
    assert dialog.height == 480
    assert dialog.is_custom is False
    assert len(DIGITAL_MODELS) >= 3
    assert len(ANALOG_MODELS) >= 2


def test_mock_config_dialog_open_and_structured_changes():
    cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
    dialog = MockConfigDialog(
        current_config=cfg,
        width=640,
        height=480,
        mock_url="http://localhost:3000/api/mock_camera/feed.jpg",
    )

    with (
        patch("gui.api_console.mock_config_dialog.ui.dialog") as mock_dlg,
        patch("gui.api_console.mock_config_dialog.ui.card"),
        patch("gui.api_console.mock_config_dialog.ui.tabs"),
        patch("gui.api_console.mock_config_dialog.ui.tab"),
        patch("gui.api_console.mock_config_dialog.ui.tab_panels"),
        patch("gui.api_console.mock_config_dialog.ui.tab_panel"),
        patch("gui.api_console.mock_config_dialog.ui.row"),
        patch("gui.api_console.mock_config_dialog.ui.column"),
        patch("gui.api_console.mock_config_dialog.ui.label"),
        patch("gui.api_console.mock_config_dialog.ui.badge"),
        patch("gui.api_console.mock_config_dialog.ui.select"),
        patch("gui.api_console.mock_config_dialog.ui.input"),
        patch("gui.api_console.mock_config_dialog.ui.switch"),
        patch("gui.api_console.mock_config_dialog.ui.textarea"),
        patch("gui.api_console.mock_config_dialog.ui.button"),
        patch("gui.api_console.mock_config_dialog.ui.table"),
        patch("gui.api_console.mock_config_dialog.ui.image"),
        patch("gui.api_console.mock_config_dialog.ui.icon"),
    ):
        mock_dlg.return_value.__enter__ = MagicMock()
        mock_dlg.return_value.__exit__ = MagicMock()
        dialog.open()

        # Simulate user changing structured inputs
        dig_key = next(iter(DIGITAL_MODELS.keys()))
        ana_key = next(iter(ANALOG_MODELS.keys()))
        dialog.dig_model_select = MagicMock(value=dig_key)
        dialog.ana_model_select = MagicMock(value=ana_key)
        dialog.meter_name_input = MagicMock(value="water_main")
        dialog.meter_unit_input = MagicMock(value="L")
        dialog.meter_format_input = MagicMock(
            value="{digit1}{digit2}{digit3}.{analog1}"
        )
        dialog.detect_neg_switch = MagicMock(value=True)
        dialog.consistency_switch = MagicMock(value=True)
        dialog.allow_neg_rates_switch = MagicMock(value=False)
        dialog.proc_enabled_switch = MagicMock(value=True)
        dialog.autocontrast_switch = MagicMock(value=True)
        dialog.glare_switch = MagicMock(value=True)
        dialog.glare_mode_select = MagicMock(value="average")
        dialog.sharpening_switch = MagicMock(value=True)

        dialog._on_structured_change()
        assert dialog.is_custom is True
        assert dialog.config.meter_configs[0].name == "water_main"
        assert dialog.config.meter_configs[0].unit == "L"
        assert dialog.config.meter_configs[0].consistency_enabled is True
        assert dialog.config.meter_configs[0].allow_negative_rates is False
        assert dialog.config.digital_readout.detect_negative_sign is True
        assert dialog.config.image_processing.autocontrast.enabled is True
        assert dialog.config.image_processing.glare_suppression.mode == "average"
        assert dialog.config.image_processing.sharpness_mode == "unsharp_mask"


def test_mock_config_dialog_ini_validation_and_apply():
    applied_config = None
    applied_custom_flag = None

    def on_apply(cfg: Config, is_custom: bool):
        nonlocal applied_config, applied_custom_flag
        applied_config = cfg
        applied_custom_flag = is_custom

    cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
    dialog = MockConfigDialog(
        current_config=cfg,
        width=640,
        height=480,
        mock_url="http://localhost:3000/api/mock_camera/feed.jpg",
        on_apply=on_apply,
    )

    # Valid INI
    ini_str = cfg.to_ini_string()
    dialog.raw_ini_editor = MagicMock(
        value=ini_str.replace("URL=\n", "URL=http://cam.lan/raw.jpg\n")
    )
    dialog.validation_banner = MagicMock()
    dialog.validation_label = MagicMock()
    valid = dialog._validate_ini_editor()
    assert valid is True
    assert dialog.is_custom is True
    assert dialog.config.image_source.url == "http://cam.lan/raw.jpg"

    # Invalid INI
    dialog.raw_ini_editor.value = "INVALID INI [[[["
    invalid = dialog._validate_ini_editor()
    assert invalid is False

    # Apply to Studio
    with patch("gui.api_console.mock_config_dialog.ui.notify"):
        dialog._apply_to_studio()
        assert applied_config is not None
        assert applied_custom_flag is True


def test_mock_config_dialog_reset_and_download(mock_callbacks):
    cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
    dialog = MockConfigDialog(
        current_config=cfg,
        width=640,
        height=480,
        mock_url="http://localhost:3000/api/mock_camera/feed.jpg",
        callbacks=mock_callbacks,
        is_custom=True,
    )

    with patch("gui.api_console.mock_config_dialog.ui.notify"):
        dialog._reset_to_canvas_sync()
        assert dialog.is_custom is False

    with (
        patch("gui.api_console.mock_config_dialog.ui.download") as mock_dl,
        patch("gui.api_console.mock_config_dialog.ui.notify"),
    ):
        dialog._download_ini()
        mock_dl.assert_called_once()
        assert mock_dl.call_args[1]["filename"] == "mock_config.ini"
