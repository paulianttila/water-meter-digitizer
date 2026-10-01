"""Unit tests for mock camera meter templates and modular archetypes."""

from __future__ import annotations

import io

from PIL import Image

from api.routes_mock_camera import render_mock_camera_frame
from config.meter_presets import load_meter_presets
from services.simulator import MeterImageGenerator
from services.simulator.rendering import DigitalFlowScreenLayout
from services.simulator.templates import (
    STANDARD_DIAL_CONFIGS,
    MeterTemplate,
    get_meter_template,
    list_meter_templates,
)


class TestMeterTemplates:
    """Tests for MeterTemplate registry and retrieval."""

    def test_list_templates_returns_all_registered(self) -> None:
        templates = list_meter_templates()
        ids = [t.id for t in templates]
        assert "mechanical_dials" in ids
        assert "mechanical_roller" in ids
        assert "digital_single" in ids
        assert "digital_flow" in ids

    def test_get_template_known(self) -> None:
        t = get_meter_template("mechanical_roller")
        assert isinstance(t, MeterTemplate)
        assert t.id == "mechanical_roller"
        assert t.counter_type == "drum"
        assert t.has_dials is False
        assert t.drum_decimals == 1
        assert t.has_decimal_dot is True

    def test_get_template_unknown_fallback(self) -> None:
        t = get_meter_template("unknown_preset_xyz")
        assert t.id == "mechanical_dials"
        assert t.has_dials is True

    def test_get_template_digital_flow(self) -> None:
        t = get_meter_template("digital_flow")
        assert isinstance(t, MeterTemplate)
        assert t.id == "digital_flow"
        assert t.counter_type == "lcd"
        assert t.has_dials is False
        assert t.has_flow_display is True
        assert (
            t.has_flow_indicator is False
        )  # Ultrasonic meter has no mechanical wheel/spinner
        assert t.digit_count == 9

    def test_get_template_digital_single(self) -> None:
        t = get_meter_template("digital_single")
        assert isinstance(t, MeterTemplate)
        assert t.id == "digital_single"
        assert t.counter_type == "lcd"
        assert t.has_dials is False
        assert t.has_flow_indicator is False
        assert t.digit_count == 5


class TestMeterGeneratorTemplates:
    """Tests for synthetic frame generation across meter templates."""

    def test_generate_image_mechanical_dials(self) -> None:
        gen = MeterImageGenerator()
        img = gen.generate(
            value="00452.91241",
            meter_type="mechanical_dials",
        )
        assert isinstance(img, Image.Image)
        assert img.size == (640, 480)

    def test_render_frame_mechanical_dials(self) -> None:
        jpeg_bytes, headers = render_mock_camera_frame(
            value="00452.91241",
            meter_type="mechanical_dials",
        )
        assert isinstance(jpeg_bytes, bytes)
        assert headers.get("X-Mock-Meter-Value") == "00452.91241"
        assert headers.get("X-Mock-Digital-Value") == "00452"
        assert headers.get("X-Mock-Analog-Value") == "9124"

        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.size == (640, 480)

    def test_render_frame_mechanical_roller(self) -> None:
        jpeg_bytes, headers = render_mock_camera_frame(
            value="00452.9",
            meter_type="mechanical_roller",
        )
        assert isinstance(jpeg_bytes, bytes)
        assert headers.get("X-Mock-Analog-Value") == ""
        assert "0045" in headers.get("X-Mock-Digital-Value", "")

    def test_render_frame_digital_single(self) -> None:
        jpeg_bytes, headers = render_mock_camera_frame(
            value="12345",
            meter_type="digital_single",
        )
        assert isinstance(jpeg_bytes, bytes)
        assert headers.get("X-Mock-Digital-Value") == "12345"
        assert headers.get("X-Mock-Analog-Value") == ""

    def test_render_frame_digital_flow(self) -> None:
        jpeg_bytes, headers = render_mock_camera_frame(
            value="000123.456",
            meter_type="digital_flow",
            flow_value="01.250",
        )
        assert isinstance(jpeg_bytes, bytes)
        assert headers.get("X-Mock-Flow-Value") == "01.250"
        assert headers.get("X-Mock-Digital-Value") == "000123"
        assert headers.get("X-Mock-Analog-Value") == ""


class TestMockMeterConfigTemplates:
    """Tests for generating matching Config objects for each meter type."""

    def test_create_config_mechanical_dials(self) -> None:
        cfg = MeterImageGenerator.create_mock_meter_config(
            meter_type="mechanical_dials"
        )
        assert cfg.digital_readout.enabled is True
        assert len(cfg.digital_readout.cut_images) == 5
        assert cfg.analog_readout.enabled is True
        assert len(cfg.analog_readout.cut_images) == 4
        meter_names = [m.name for m in cfg.meter_configs]
        assert "total" in meter_names
        total_cfg = next(m for m in cfg.meter_configs if m.name == "total")
        assert "analog" in total_cfg.format

    def test_create_config_mechanical_roller(self) -> None:
        cfg = MeterImageGenerator.create_mock_meter_config(
            meter_type="mechanical_roller"
        )
        assert cfg.digital_readout.enabled is True
        assert len(cfg.digital_readout.cut_images) == 5
        assert cfg.analog_readout.enabled is False
        assert len(cfg.analog_readout.cut_images) == 0
        meter_names = [m.name for m in cfg.meter_configs]
        assert "total" in meter_names
        total_cfg = next(m for m in cfg.meter_configs if m.name == "total")
        assert "analog" not in total_cfg.format

    def test_create_config_digital_flow(self) -> None:
        cfg = MeterImageGenerator.create_mock_meter_config(meter_type="digital_flow")
        assert cfg.digital_readout.enabled is True
        # 6 int + 3 dec + 2 flow + 3 flow_dec = 14
        assert len(cfg.digital_readout.cut_images) == 14
        assert cfg.analog_readout.enabled is False
        meter_names = [m.name for m in cfg.meter_configs]
        assert "total" in meter_names
        assert "flow" in meter_names

    def test_standard_rois_match_layout_constants(self) -> None:
        """Verify standard ROI bounding boxes match DigitalFlowScreenLayout definitions."""
        cfg = MeterImageGenerator.create_mock_meter_config(meter_type="digital_flow")
        rois = {p.name: p for p in cfg.digital_readout.cut_images}

        # Check volume integer boxes
        for i in range(DigitalFlowScreenLayout.VOLUME_INTEGER.count):
            name = DigitalFlowScreenLayout.VOLUME_INTEGER.digit_name(i)
            box = DigitalFlowScreenLayout.VOLUME_INTEGER.get_box(i)
            assert name in rois
            p = rois[name]
            assert (p.x, p.y, p.w, p.h) == box

        # Check volume decimal boxes
        for i in range(DigitalFlowScreenLayout.VOLUME_DECIMAL.count):
            name = DigitalFlowScreenLayout.VOLUME_DECIMAL.digit_name(i)
            box = DigitalFlowScreenLayout.VOLUME_DECIMAL.get_box(i)
            assert name in rois
            p = rois[name]
            assert (p.x, p.y, p.w, p.h) == box

        # Check flow integer boxes
        for i in range(DigitalFlowScreenLayout.FLOW_INTEGER.count):
            name = DigitalFlowScreenLayout.FLOW_INTEGER.digit_name(i)
            box = DigitalFlowScreenLayout.FLOW_INTEGER.get_box(i)
            assert name in rois
            p = rois[name]
            assert (p.x, p.y, p.w, p.h) == box

        # Check flow decimal boxes
        for i in range(DigitalFlowScreenLayout.FLOW_DECIMAL.count):
            name = DigitalFlowScreenLayout.FLOW_DECIMAL.digit_name(i)
            box = DigitalFlowScreenLayout.FLOW_DECIMAL.get_box(i)
            assert name in rois
            p = rois[name]
            assert (p.x, p.y, p.w, p.h) == box

        # Check analog dial ROIs against STANDARD_DIAL_CONFIGS
        mech_cfg = MeterImageGenerator.create_mock_meter_config(
            meter_type="mechanical_dials"
        )
        dial_rois = {p.name: p for p in mech_cfg.analog_readout.cut_images}
        dial_size = 76
        for i, (cx, cy, _mult) in enumerate(STANDARD_DIAL_CONFIGS):
            name = f"analog{i+1}"
            assert name in dial_rois
            p = dial_rois[name]
            assert (p.x, p.y, p.w, p.h) == (
                cx - dial_size // 2,
                cy - dial_size // 2,
                dial_size,
                dial_size,
            )


class TestWizardPresetFiles:
    """Tests that wizard preset files for all templates exist and parse cleanly."""

    def test_load_all_presets_includes_mock_camera_variants(self) -> None:
        presets = load_meter_presets()
        preset_ids = {p.id for p in presets}
        assert "mock_camera" in preset_ids
        assert "mock_camera_roller" in preset_ids
        assert "mock_camera_digital_single" in preset_ids
        assert "mock_camera_digital_flow" in preset_ids
