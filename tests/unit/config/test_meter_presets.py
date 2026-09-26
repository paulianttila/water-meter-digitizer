"""Unit tests for configuration-driven meter types models and loader."""

import json
from pathlib import Path

from config.meter_presets import (
    DEFAULT_BUILTIN_PRESETS,
    MeterTypePreset,
    PresetMeterConfig,
    load_meter_presets,
    sort_meter_presets,
)


def test_builtin_presets_structure():
    assert len(DEFAULT_BUILTIN_PRESETS) == 5
    ids = [p.id for p in DEFAULT_BUILTIN_PRESETS]
    assert "axioma_qalcosonic_w1" not in ids
    assert "kamstrup_flowiq2200" not in ids
    assert "diehl_hydrus" not in ids
    assert "honeywell_v200" not in ids
    assert "itron_aquadis" not in ids
    assert "bmeters_gsd8" not in ids
    assert "generic_lcd_cumulative" in ids
    assert "generic_lcd_flow" in ids
    assert "generic_mechanical_classic" in ids
    assert "generic_mechanical_drums" in ids
    assert "custom" in ids


def test_load_meter_presets_from_directory():
    # Should load all modular files from config/meter_types/
    presets = load_meter_presets()
    assert len(presets) >= 6
    preset_map = {p.id: p for p in presets}
    assert "mock_camera" in preset_map
    assert "axioma_qalcosonic_w1" in preset_map
    assert "generic_lcd_cumulative" in preset_map
    assert "generic_lcd_flow" in preset_map
    assert "generic_mechanical_classic" in preset_map
    assert "generic_mechanical_drums" in preset_map
    assert "custom" in preset_map

    mock_cam = preset_map["mock_camera"]
    assert mock_cam.default_int_digits == 5
    assert mock_cam.default_analog_count == 4
    assert len(mock_cam.default_rois.digital) == 5
    assert len(mock_cam.default_rois.analog) == 4
    assert len(mock_cam.alignment.references) == 3
    assert mock_cam.digital_category_preference == "class11"
    assert mock_cam.analog_category_preference == "continuous"

    axioma = preset_map["axioma_qalcosonic_w1"]
    assert axioma.brand == "Axioma"
    assert axioma.digital_category_preference == "class11"
    assert axioma.has_secondary_group is True


def test_load_meter_presets_directory_ignores_templates(tmp_path: Path):
    mdir = tmp_path / "meter_types"
    mdir.mkdir()

    # Template file (should be ignored)
    (mdir / "_template.json").write_text(
        json.dumps({"id": "template", "label": "Template"}), encoding="utf-8"
    )
    # Hidden file (should be ignored)
    (mdir / ".hidden.json").write_text(
        json.dumps({"id": "hidden", "label": "Hidden"}), encoding="utf-8"
    )
    # Valid file
    (mdir / "valid_model.json").write_text(
        json.dumps(
            {
                "id": "valid_model",
                "label": "Valid Model",
                "description": "Test",
            }
        ),
        encoding="utf-8",
    )

    presets = load_meter_presets(tmp_path)
    assert len(presets) == 1
    assert presets[0].id == "valid_model"


def test_load_meter_presets_directory_fault_isolation(tmp_path: Path):
    mdir = tmp_path / "meter_types"
    mdir.mkdir()

    # Corrupt file
    (mdir / "corrupted.json").write_text("{ this is broken json", encoding="utf-8")

    # Valid file
    (mdir / "good_model.json").write_text(
        json.dumps(
            {
                "id": "good_model",
                "label": "Good Model",
                "description": "Working model",
            }
        ),
        encoding="utf-8",
    )

    # Corrupt file should be safely skipped; good file should load
    presets = load_meter_presets(tmp_path)
    assert len(presets) == 1
    assert presets[0].id == "good_model"


def test_deterministic_sorting():
    presets = [
        MeterTypePreset(
            id="custom", label="Custom", description="", category="generic"
        ),
        MeterTypePreset(
            id="generic_lcd",
            label="Generic LCD",
            description="",
            brand="Generic",
            category="generic",
        ),
        MeterTypePreset(
            id="honeywell",
            label="Honeywell V200",
            description="",
            brand="Honeywell",
            category="european_mechanical",
        ),
        MeterTypePreset(
            id="axioma",
            label="Axioma Qalcosonic",
            description="",
            brand="Axioma",
            category="european_smart",
        ),
    ]

    sorted_p = sort_meter_presets(presets)
    ids = [p.id for p in sorted_p]
    # European smart first, then European mechanical, then Generic, Custom strictly last
    assert ids == ["axioma", "honeywell", "generic_lcd", "custom"]


def test_load_meter_presets_missing_file_fallback(tmp_path: Path):
    # Non-existent directory should safely fallback to built-ins
    empty_dir = tmp_path / "empty_config"
    empty_dir.mkdir()
    presets = load_meter_presets(empty_dir)
    assert len(presets) == len(DEFAULT_BUILTIN_PRESETS)
    assert presets[0].id == DEFAULT_BUILTIN_PRESETS[0].id


def test_load_meter_presets_corrupted_json_fallback(tmp_path: Path):
    corrupt_file = tmp_path / "meter_types.json"
    corrupt_file.write_text("{ this is invalid json !!!", encoding="utf-8")
    presets = load_meter_presets(tmp_path)
    assert len(presets) == len(DEFAULT_BUILTIN_PRESETS)


def test_load_meter_presets_custom_model_extension(tmp_path: Path):
    custom_content = {
        "version": 1,
        "presets": [
            {
                "id": "my_custom_meter",
                "category": "european_smart",
                "brand": "CustomBrand",
                "model": "X100",
                "label": "Custom Brand X100",
                "description": "A customized water meter model.",
                "icon": "water_drop",
                "meter_technology": "ultrasonic_lcd",
                "default_int_digits": 6,
                "default_dec_digits": 2,
                "default_analog_count": 0,
                "default_unit": "L",
                "layout": {
                    "digital_y_frac": 0.40,
                    "box_width": 50,
                    "box_height": 70,
                },
                "cnn": {
                    "digital_category": "class11",
                    "digital_preferred_model": "dig-class11_1600_s2_q.tflite",
                    "recommendation_reason": "Optimized for custom LCD.",
                },
                "meters": [
                    {
                        "name": "total",
                        "format_template": "{digits}.{decimals}",
                        "unit": "{unit}",
                        "consistency_enabled": True,
                        "use_previous_value": True,
                        "max_rate_value": 0.5,
                    }
                ],
            }
        ],
    }
    config_file = tmp_path / "meter_types.json"
    config_file.write_text(json.dumps(custom_content), encoding="utf-8")

    presets = load_meter_presets(tmp_path)
    assert len(presets) == 1
    p = presets[0]
    assert p.id == "my_custom_meter"
    assert p.label == "Custom Brand X100"
    assert p.brand == "CustomBrand"

    # Test dynamic building of meter configs from custom model
    names = p.get_digital_roi_names(int_digits=6, dec_digits=2)
    assert len(names) == 8
    positions = p.get_digital_roi_positions(names, 640, 480)
    assert len(positions) == 8
    assert positions[0].y == int(480 * 0.40) - (70 // 2)

    configs = p.build_meter_configs(names, [], unit="L")
    assert len(configs) == 1
    assert configs[0].name == "total"
    assert configs[0].unit == "L"
    assert (
        configs[0].format
        == "{digit1}{digit2}{digit3}{digit4}{digit5}{digit6}.{decimal1}{decimal2}"
    )


def test_build_meter_configs_delimiters_and_cleanup():
    preset = MeterTypePreset(
        id="test_format",
        label="Test Format",
        description="Format test",
        meters=[
            PresetMeterConfig(
                name="total",
                format_template="{digits}.{decimals}",
                unit="{unit}",
            )
        ],
    )
    # When decimals is empty, trailing dot is removed
    configs = preset.build_meter_configs(["digit1", "digit2"], [], unit="m³")
    assert len(configs) == 1
    assert configs[0].format == "{digit1}{digit2}"
    assert configs[0].unit == "m³"


def test_declarative_meter_templates_with_flow_group():
    presets = {p.id: p for p in load_meter_presets()}
    preset = presets["axioma_qalcosonic_w1"]
    dig_names = [
        "digit1",
        "digit2",
        "digit3",
        "decimal1",
        "flow1",
        "flow2",
        "flow_dec1",
    ]
    configs = preset.build_meter_configs(dig_names, [], unit="m³")
    assert len(configs) == 2
    assert configs[0].name == "total"
    assert configs[0].format == "{digit1}{digit2}{digit3}.{decimal1}"
    assert configs[0].unit == "m³"

    assert configs[1].name == "flow"
    assert configs[1].format == "{flow1}{flow2}.{flow_dec1}"
    assert configs[1].unit == "m³/h"
    assert configs[1].detect_negative_sign is True


def test_reference_positions_and_resolution_scaling():
    presets = {p.id: p for p in load_meter_presets()}
    mech = presets["generic_mechanical_classic"]
    assert len(mech.alignment.references) == 3

    # Base resolution 640x480
    refs_base = mech.get_reference_positions(640, 480)
    assert len(refs_base) == 3
    ref0 = refs_base[0]
    assert ref0.name == "Ref0"
    assert ref0.x == 110
    assert ref0.y == 220
    assert ref0.w == 32
    assert ref0.h == 32

    # Scaled to 1280x960 (2x)
    refs_2x = mech.get_reference_positions(1280, 960)
    assert len(refs_2x) == 3
    assert refs_2x[0].x == 220
    assert refs_2x[0].y == 440
    assert refs_2x[0].w == 64
    assert refs_2x[0].h == 64


def test_default_rois_2x2_cluster_and_scaling():
    presets = {p.id: p for p in load_meter_presets()}
    mech = presets["generic_mechanical_classic"]

    # 4 dials in 2x2 grid
    ana_names = ["analog1", "analog2", "analog3", "analog4"]
    rois = mech.get_analog_roi_positions(ana_names, 640, 480)
    assert len(rois) == 4
    # analog1 and analog2 on upper row
    assert rois[0].y == rois[1].y
    assert rois[0].x < rois[1].x
    # analog3 and analog4 on lower row
    assert rois[2].y == rois[3].y
    assert rois[2].y > rois[0].y

    # Scaled to 1280x960
    rois_scaled = mech.get_analog_roi_positions(ana_names, 1280, 960)
    assert rois_scaled[0].x == rois[0].x * 2
    assert rois_scaled[0].y == rois[0].y * 2


def test_image_adjustments_and_leak_detection_fields():
    presets = {p.id: p for p in load_meter_presets()}
    mech = presets["generic_mechanical_classic"]
    assert mech.image_adjustments.contrast == 1.2
    assert mech.image_adjustments.sharpness_mode == "unsharp_mask"
    assert mech.image_adjustments.glare_suppression.enabled is True
    assert mech.image_adjustments.glare_suppression.clahe_clip_limit == 2.5
    assert mech.leak_detection.recommended_min_flow_threshold == 0.0005

    axioma = presets["axioma_qalcosonic_w1"]
    assert axioma.image_adjustments.enabled is True
    assert axioma.image_adjustments.contrast == 1.35
    assert axioma.leak_detection.recommended_min_flow_threshold == 0.001


def test_crop_box_scaling():
    from config.meter_presets import PresetCropConfig

    preset = MeterTypePreset(
        id="test_crop",
        label="Test Crop",
        description="",
        crop=PresetCropConfig(enabled=True, x=50, y=50, w=400, h=300),
    )
    crop_base = preset.get_crop_box(640, 480)
    assert crop_base is not None
    assert crop_base.x == 50
    assert crop_base.y == 50
    assert crop_base.w == 400
    assert crop_base.h == 300

    crop_scaled = preset.get_crop_box(1280, 960)
    assert crop_scaled is not None
    assert crop_scaled.x == 100
    assert crop_scaled.y == 100
    assert crop_scaled.w == 800
    assert crop_scaled.h == 600


def test_ini_preset_model_uri_and_faceplate_image():
    from config.meter_presets import get_available_template_images, get_preset_by_id

    axioma = get_preset_by_id("axioma_qalcosonic_w1")
    assert axioma is not None
    assert axioma.model_uri == "model://axioma_qalcosonic_w1"
    assert axioma.has_image is True
    assert axioma.get_image_path() is not None

    mock_cam = get_preset_by_id("mock_camera")
    assert mock_cam is not None
    assert mock_cam.model_uri == "model://mock_camera"
    assert mock_cam.has_image is True

    template_images = get_available_template_images()
    uris = [uri for uri, _ in template_images]
    assert "model://axioma_qalcosonic_w1" in uris
    assert "model://mock_camera" in uris


def test_ini_template_defaults_inheritance(tmp_path: Path):
    from config.meter_presets import _load_preset_from_ini

    ini_file = tmp_path / "minimal_meter.ini"
    ini_file.write_text(
        """[Template]
Id = minimal_meter
Label = Minimal Meter
Description = Minimal test
DefaultIntDigits = 4
DefaultUnit = L
""",
        encoding="utf-8",
    )

    preset = _load_preset_from_ini(ini_file)
    assert preset is not None
    assert preset.id == "minimal_meter"
    assert preset.default_int_digits == 4
    assert preset.default_unit == "L"
    # Verify unmentioned sections inherited defaults
    assert preset.image_adjustments.contrast == 1.0
    assert preset.image_adjustments.brightness == 1.0
    assert preset.crop.enabled is False
    assert preset.leak_detection.recommended_min_flow_threshold == 0.001

    # Disabled crop returns None
    preset.crop.enabled = False
    assert preset.get_crop_box(640, 480) is None


def test_ini_template_interpolation_with_placeholders(tmp_path: Path):
    from config.meter_presets import _load_preset_from_ini

    ini_file = tmp_path / "interpolated_meter.ini"
    ini_file.write_text(
        """[Template]
Id = interp_meter
Label = Interpolated Meter
DefaultIntDigits = 5

[Digits]
Enabled = True
ModelFile = ${ConfigDir}/neuralnets/model.tflite
Names = digit1

[Digits.digit1]
x = 10
y = 10
w = 20
h = 30
""",
        encoding="utf-8",
    )

    preset = _load_preset_from_ini(ini_file)
    assert preset is not None
    assert preset.id == "interp_meter"
    assert len(preset.default_rois.digital) == 1


def test_presets_caching_and_hot_reload(tmp_path: Path):
    from config.meter_presets import (
        clear_presets_cache,
        get_available_template_images,
        get_preset_by_id,
        load_meter_presets,
        reload_meter_presets,
    )

    clear_presets_cache()
    mdir = tmp_path / "meter_types"
    mdir.mkdir()

    # 1. Create first preset
    (mdir / "first_meter.ini").write_text(
        """[Template]
Id = first_meter
Label = First Meter
DefaultIntDigits = 5
DefaultUnit = m3
""",
        encoding="utf-8",
    )

    # First load
    presets1 = load_meter_presets(tmp_path)
    assert len(presets1) == 1
    assert presets1[0].id == "first_meter"

    # Add second preset to directory while cached
    (mdir / "second_meter.ini").write_text(
        """[Template]
Id = second_meter
Label = Second Meter
DefaultIntDigits = 6
DefaultUnit = m3
""",
        encoding="utf-8",
    )

    # Calling without force_reload returns cached version
    presets_cached = load_meter_presets(tmp_path)
    assert len(presets_cached) == 1
    assert get_preset_by_id("second_meter", config_dir=tmp_path) is None

    # Calling with force_reload=True picks up the new preset
    presets_reloaded = load_meter_presets(tmp_path, force_reload=True)
    assert len(presets_reloaded) == 2
    ids = [p.id for p in presets_reloaded]
    assert "first_meter" in ids
    assert "second_meter" in ids

    # reload_meter_presets also picks up updates
    (mdir / "third_meter.ini").write_text(
        """[Template]
Id = third_meter
Label = Third Meter
DefaultIntDigits = 4
DefaultUnit = L
""",
        encoding="utf-8",
    )
    presets_reloaded2 = reload_meter_presets(tmp_path)
    assert len(presets_reloaded2) == 3
    assert get_preset_by_id("third_meter", config_dir=tmp_path) is not None

    # Add a fourth preset and image file for fourth_meter and test get_available_template_images
    (mdir / "fourth_meter.ini").write_text(
        """[Template]
Id = fourth_meter
Label = Fourth Meter
""",
        encoding="utf-8",
    )
    (mdir / "fourth_meter.png").write_bytes(b"dummy image data")
    images_cached = get_available_template_images(tmp_path, force_reload=False)
    # Should not have fourth_meter image yet because fourth_meter preset is not in cache
    assert "model://fourth_meter" not in [uri for uri, _ in images_cached]
    # With force_reload=True:
    images_reloaded = get_available_template_images(tmp_path, force_reload=True)
    image_uris = [uri for uri, _ in images_reloaded]
    assert "model://fourth_meter" in image_uris

    # clear_presets_cache cleans the cache
    clear_presets_cache()
    presets_after_clear = load_meter_presets(tmp_path)
    assert len(presets_after_clear) == 4
