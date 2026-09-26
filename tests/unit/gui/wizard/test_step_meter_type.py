"""Unit tests for MeterTypeStep, MeterTypePreset, and select_best_model."""

from unittest.mock import MagicMock

from gui.wizard.steps.meter_type import (
    PRESET_BY_ID,
    PRESETS,
    MeterTypeStep,
    select_best_model,
)


def test_presets_definitions():
    assert len(PRESETS) >= 6
    assert "axioma_qalcosonic_w1" in PRESET_BY_ID
    assert "generic_lcd_cumulative" in PRESET_BY_ID
    assert "custom" in PRESET_BY_ID

    axioma = PRESET_BY_ID["axioma_qalcosonic_w1"]
    assert axioma.digital_category_preference == "class11"
    assert axioma.analog_category_preference is None
    assert axioma.has_secondary_group is True


def test_digital_roi_names_axioma_qalcosonic():
    preset = PRESET_BY_ID["axioma_qalcosonic_w1"]
    names = preset.get_digital_roi_names(
        int_digits=5, dec_digits=3, flow_int_digits=3, flow_dec_digits=2
    )
    assert names == [
        "digit1",
        "digit2",
        "digit3",
        "digit4",
        "digit5",
        "decimal1",
        "decimal2",
        "decimal3",
        "flow1",
        "flow2",
        "flow3",
        "flow_dec1",
        "flow_dec2",
    ]


def test_digital_roi_names_custom():
    preset = PRESET_BY_ID["custom"]
    assert preset.get_digital_roi_names(int_digits=5, dec_digits=3) == []


def test_analog_roi_names():
    preset = PRESET_BY_ID["generic_mechanical_classic"]
    assert preset.get_analog_roi_names(4) == [
        "analog1",
        "analog2",
        "analog3",
        "analog4",
    ]
    assert preset.get_analog_roi_names(0) == []

    preset_lcd = PRESET_BY_ID["generic_lcd_cumulative"]
    assert preset_lcd.get_analog_roi_names(4) == []


def test_get_digital_roi_positions_dual_group():
    preset = PRESET_BY_ID["axioma_qalcosonic_w1"]
    names = ["d1", "d2", "d3", "f1", "f2"]
    positions = preset.get_digital_roi_positions(
        names, img_w=640, img_h=480, flow_split=2
    )
    assert len(positions) == 5

    main_positions = positions[:3]
    flow_positions = positions[3:]

    # Main group should be vertically above flow group
    assert main_positions[0].y < flow_positions[0].y


def test_build_meter_configs_generic_lcd():
    preset = PRESET_BY_ID["generic_lcd_cumulative"]
    dig_names = ["digit1", "digit2", "digit3", "decimal1", "decimal2"]
    configs = preset.build_meter_configs(dig_names, [], unit="m³")

    assert len(configs) == 1
    cfg = configs[0]
    assert cfg.name == "total"
    assert cfg.format == "{digit1}{digit2}{digit3}.{decimal1}{decimal2}"
    assert cfg.unit == "m³"
    assert cfg.consistency_enabled is True
    assert cfg.use_previous_value is True


def test_build_meter_configs_axioma_dual():
    preset = PRESET_BY_ID["axioma_qalcosonic_w1"]
    dig_names = ["digit1", "digit2", "decimal1", "flow1", "flow2", "flow_dec1"]
    configs = preset.build_meter_configs(dig_names, [], unit="m³")

    assert len(configs) == 2
    total_cfg = configs[0]
    flow_cfg = configs[1]

    assert total_cfg.name == "total"
    assert total_cfg.format == "{digit1}{digit2}.{decimal1}"
    assert total_cfg.unit == "m³"

    assert flow_cfg.name == "flow"
    assert flow_cfg.format == "{flow1}{flow2}.{flow_dec1}"
    assert flow_cfg.unit == "m³/h"
    assert flow_cfg.detect_negative_sign is True


def test_build_meter_configs_custom():
    preset = PRESET_BY_ID["custom"]
    configs = preset.build_meter_configs(["d1"], ["a1"])
    assert configs == []


def test_select_best_model():
    assert select_best_model({}, "class11") is None

    options = {
        "/models/digital/class100/dig-class100_0168_s2.tflite": "class100/model1",
        "/models/digital/class100/dig-class100_0168_s2_q.tflite": "class100/model1_q",
        "/models/digital/class11/dig-class11_1600_s2.tflite": "class11/model2",
        "/models/digital/class11/dig-class11_1600_s2_q.tflite": "class11/model2_q",
        "/models/digital/class11/dig-class11_2000_s2_q.tflite": "class11/model3_q",
    }

    matched = select_best_model(
        options, "class11", preferred_filename="dig-class11_1600_s2_q.tflite"
    )
    assert matched == "/models/digital/class11/dig-class11_1600_s2_q.tflite"

    matched = select_best_model(options, "class11")
    assert matched == "/models/digital/class11/dig-class11_2000_s2_q.tflite"

    matched = select_best_model(options, "class100")
    assert matched == "/models/digital/class100/dig-class100_0168_s2_q.tflite"

    matched = select_best_model(options, "non_existent_category")
    assert matched == "/models/digital/class100/dig-class100_0168_s2.tflite"


def test_meter_type_step_state_and_selection():
    step = MeterTypeStep(name="Meter type")
    assert step.selected_preset_id == "custom"
    assert step.selected_preset == PRESET_BY_ID["custom"]

    # Select Axioma Qalcosonic W1
    step._select_preset("axioma_qalcosonic_w1")
    assert step.selected_preset_id == "axioma_qalcosonic_w1"
    assert step.int_digits == 6
    assert step.dec_digits == 3
    assert step.analog_count == 0
    assert step.flow_int_digits == 2
    assert step.flow_dec_digits == 3
    assert len(step.effective_digital_roi_names) == 14
    assert len(step.effective_analog_roi_names) == 0

    # Preview label update test with mock
    mock_preview = MagicMock()
    step._preview_label = mock_preview
    step._update_preview()
    mock_preview.set_text.assert_called_once()
    assert "total" in mock_preview.set_text.call_args[0][0]


def test_category_filtering():
    step = MeterTypeStep(name="Meter type")
    all_options = step._get_filtered_preset_options()
    assert len(all_options) >= 6

    # Filter by smart
    step.active_category = "smart"
    smart_options = step._get_filtered_preset_options()
    assert "axioma_qalcosonic_w1" in smart_options

    # Filter by mechanical
    step.active_category = "mechanical"
    mech_options = step._get_filtered_preset_options()
    assert "axioma_qalcosonic_w1" not in mech_options

    # Filter by generic
    step.active_category = "generic"
    generic_options = step._get_filtered_preset_options()
    assert "generic_lcd_cumulative" in generic_options
    assert "axioma_qalcosonic_w1" not in generic_options


def test_meter_type_step_refresh_and_reload(tmp_path):
    from unittest.mock import patch

    from gui.wizard.steps.meter_type import reload_presets

    step = MeterTypeStep(name="Meter type", config_dir=tmp_path)
    initial_count = len(step.presets)

    # Mock ui.select and notify
    mock_select = MagicMock()
    mock_select.options = {}
    step._preset_select = mock_select

    # Refreshing without new files
    step.refresh_presets(force_reload=False)
    assert len(step.presets) == initial_count
    assert mock_select.options

    # Create new preset in tmp_path
    mdir = tmp_path / "meter_types"
    mdir.mkdir()
    (mdir / "dynamic_test.ini").write_text(
        """[Template]
Id = dynamic_test
Label = Dynamic Test Meter
DefaultIntDigits = 7
DefaultUnit = m3
""",
        encoding="utf-8",
    )

    # Calling refresh_presets(force_reload=True) picks it up
    step.refresh_presets(force_reload=True)
    assert "dynamic_test" in step.preset_by_id
    assert "dynamic_test" in mock_select.options

    # Test _handle_refresh_click
    with patch("gui.wizard.steps.meter_type.ui.notify") as mock_notify:
        step._handle_refresh_click()
        mock_notify.assert_called_once()
        assert "reloaded" in mock_notify.call_args[0][0].lower()

    # Module-level reload_presets updates PRESETS in place
    loaded = reload_presets(tmp_path)
    assert any(p.id == "dynamic_test" for p in loaded)
