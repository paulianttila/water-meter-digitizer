"""Unit tests for MeterTypeStep, MeterTypePreset, and select_best_model."""

from unittest.mock import MagicMock

from gui.wizard.steps.meter_type import (
    PRESET_BY_ID,
    PRESETS,
    MeterTypeStep,
    _make_positions_row,
    select_best_model,
)


def test_presets_definitions():
    assert len(PRESETS) == 5
    assert set(PRESET_BY_ID.keys()) == {
        "lcd_cumulative",
        "lcd_cumulative_flow",
        "analog_classic",
        "analog_drums_only",
        "custom",
    }
    lcd = PRESET_BY_ID["lcd_cumulative"]
    assert lcd.digital_category_preference == "class11"
    assert lcd.analog_category_preference is None

    mech = PRESET_BY_ID["analog_classic"]
    assert mech.digital_category_preference == "class100"
    assert mech.analog_category_preference == "continuous"


def test_digital_roi_names_lcd_cumulative():
    preset = PRESET_BY_ID["lcd_cumulative"]
    names = preset.get_digital_roi_names(int_digits=5, dec_digits=3)
    assert names == [
        "digit1",
        "digit2",
        "digit3",
        "digit4",
        "digit5",
        "decimal1",
        "decimal2",
        "decimal3",
    ]


def test_digital_roi_names_lcd_cumulative_flow():
    preset = PRESET_BY_ID["lcd_cumulative_flow"]
    names = preset.get_digital_roi_names(
        int_digits=5, dec_digits=2, flow_int_digits=3, flow_dec_digits=1
    )
    assert names == [
        "digit1",
        "digit2",
        "digit3",
        "digit4",
        "digit5",
        "decimal1",
        "decimal2",
        "flow1",
        "flow2",
        "flow3",
        "flow_dec1",
    ]


def test_digital_roi_names_analog_classic():
    preset = PRESET_BY_ID["analog_classic"]
    names = preset.get_digital_roi_names(int_digits=5, dec_digits=0)
    assert names == ["digit1", "digit2", "digit3", "digit4", "digit5"]


def test_digital_roi_names_custom():
    preset = PRESET_BY_ID["custom"]
    assert preset.get_digital_roi_names(int_digits=5, dec_digits=3) == []


def test_analog_roi_names():
    preset = PRESET_BY_ID["analog_classic"]
    assert preset.get_analog_roi_names(4) == [
        "analog1",
        "analog2",
        "analog3",
        "analog4",
    ]
    assert preset.get_analog_roi_names(0) == []

    preset_lcd = PRESET_BY_ID["lcd_cumulative"]
    assert preset_lcd.get_analog_roi_names(4) == []


def test_make_positions_row():
    # Empty case
    assert _make_positions_row([], 640, 480) == []

    # Centered boxes
    names = ["d1", "d2", "d3", "d4", "d5"]
    positions = _make_positions_row(names, 640, 480, y_frac=0.5)
    assert len(positions) == 5

    # Check non-overlap and monotonic x
    for i in range(len(positions) - 1):
        assert positions[i].x + positions[i].w < positions[i + 1].x

    # Check in bounds
    for pos in positions:
        assert pos.x >= 0
        assert pos.y >= 0
        assert pos.x + pos.w <= 640
        assert pos.y + pos.h <= 480


def test_get_digital_roi_positions_dual_group():
    preset = PRESET_BY_ID["lcd_cumulative_flow"]
    names = ["d1", "d2", "d3", "f1", "f2"]
    positions = preset.get_digital_roi_positions(
        names, img_w=640, img_h=480, flow_split=2
    )
    assert len(positions) == 5

    main_positions = positions[:3]
    flow_positions = positions[3:]

    # Main group should be vertically above flow group
    assert main_positions[0].y < flow_positions[0].y


def test_get_analog_roi_positions_below_digital():
    preset = PRESET_BY_ID["analog_classic"]
    dig_names = ["d1", "d2", "d3", "d4", "d5"]
    ana_names = ["a1", "a2", "a3", "a4"]

    dig_pos = preset.get_digital_roi_positions(dig_names, 640, 480)
    ana_pos = preset.get_analog_roi_positions(ana_names, 640, 480)

    assert len(dig_pos) == 5
    assert len(ana_pos) == 4
    # Analog dials are placed lower in the frame
    assert ana_pos[0].y > dig_pos[0].y


def test_build_meter_configs_lcd_cumulative():
    preset = PRESET_BY_ID["lcd_cumulative"]
    dig_names = ["digit1", "digit2", "digit3", "decimal1", "decimal2"]
    configs = preset.build_meter_configs(dig_names, [], unit="㎥")

    assert len(configs) == 1
    cfg = configs[0]
    assert cfg.name == "total"
    assert cfg.format == "{digit1}{digit2}{digit3}.{decimal1}{decimal2}"
    assert cfg.unit == "㎥"
    assert cfg.consistency_enabled is True
    assert cfg.use_previous_value is True


def test_build_meter_configs_lcd_cumulative_flow():
    preset = PRESET_BY_ID["lcd_cumulative_flow"]
    dig_names = ["digit1", "digit2", "decimal1", "flow1", "flow2", "flow_dec1"]
    configs = preset.build_meter_configs(dig_names, [], unit="㎥")

    assert len(configs) == 2
    total_cfg = configs[0]
    flow_cfg = configs[1]

    assert total_cfg.name == "total"
    assert total_cfg.format == "{digit1}{digit2}.{decimal1}"
    assert total_cfg.unit == "㎥"

    assert flow_cfg.name == "flow"
    assert flow_cfg.format == "{flow1}{flow2}.{flow_dec1}"
    assert flow_cfg.unit == "㎥/h"
    assert flow_cfg.detect_negative_sign is True


def test_build_meter_configs_analog_classic():
    preset = PRESET_BY_ID["analog_classic"]
    dig_names = ["digit1", "digit2", "digit3"]
    ana_names = ["analog1", "analog2"]
    configs = preset.build_meter_configs(dig_names, ana_names, unit="㎥")

    assert len(configs) == 1
    cfg = configs[0]
    assert cfg.name == "total"
    assert cfg.format == "{digit1}{digit2}{digit3}.{analog1}{analog2}"
    assert cfg.use_extended_resolution is True


def test_build_meter_configs_analog_drums_only():
    preset = PRESET_BY_ID["analog_drums_only"]
    dig_names = ["digit1", "digit2", "digit3", "digit4"]
    configs = preset.build_meter_configs(dig_names, [], unit="L")

    assert len(configs) == 1
    cfg = configs[0]
    assert cfg.name == "total"
    assert cfg.format == "{digit1}{digit2}{digit3}{digit4}"
    assert cfg.unit == "L"


def test_build_meter_configs_custom():
    preset = PRESET_BY_ID["custom"]
    configs = preset.build_meter_configs(["d1"], ["a1"])
    assert configs == []


def test_select_best_model():
    # Empty options
    assert select_best_model({}, "class11") is None

    options = {
        "/models/digital/class100/dig-class100_0168_s2.tflite": "class100/model1",
        "/models/digital/class100/dig-class100_0168_s2_q.tflite": "class100/model1_q",
        "/models/digital/class11/dig-class11_1600_s2.tflite": "class11/model2",
        "/models/digital/class11/dig-class11_1600_s2_q.tflite": "class11/model2_q",
        "/models/digital/class11/dig-class11_2000_s2_q.tflite": "class11/model3_q",
    }

    # Exact filename match
    matched = select_best_model(
        options, "class11", preferred_filename="dig-class11_1600_s2_q.tflite"
    )
    assert matched == "/models/digital/class11/dig-class11_1600_s2_q.tflite"

    # Quantized preference when preferred_filename not specified or missing
    matched = select_best_model(options, "class11")
    assert matched == "/models/digital/class11/dig-class11_2000_s2_q.tflite"

    # Category preference for class100
    matched = select_best_model(options, "class100")
    assert matched == "/models/digital/class100/dig-class100_0168_s2_q.tflite"

    # Fallback to first available if category not found
    matched = select_best_model(options, "non_existent_category")
    assert matched == "/models/digital/class100/dig-class100_0168_s2.tflite"


def test_meter_type_step_state():
    step = MeterTypeStep(name="Meter type")
    assert step.selected_preset_id == "custom"
    assert step.selected_preset == PRESET_BY_ID["custom"]
    assert step.effective_digital_roi_names == []
    assert step.effective_analog_roi_names == []

    # Select LCD cumulative
    step._select_preset("lcd_cumulative")
    assert step.selected_preset_id == "lcd_cumulative"
    assert step.int_digits == 5
    assert step.dec_digits == 3
    assert step.analog_count == 0
    assert len(step.effective_digital_roi_names) == 8
    assert len(step.effective_analog_roi_names) == 0

    # Select Mechanical classic
    step._select_preset("analog_classic")
    assert step.selected_preset_id == "analog_classic"
    assert step.int_digits == 5
    assert step.dec_digits == 0
    assert step.analog_count == 4
    assert len(step.effective_digital_roi_names) == 5
    assert len(step.effective_analog_roi_names) == 4

    # Preview label update test with mock
    mock_preview = MagicMock()
    step._preview_label = mock_preview
    step._update_preview()
    mock_preview.set_text.assert_called_once()
    assert "total" in mock_preview.set_text.call_args[0][0]
