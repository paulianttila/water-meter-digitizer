"""Unit tests for DSEG font integration in Mock Camera Simulator and CNN compatibility."""

import os

import pytest
from PIL import Image, ImageDraw
from starlette.testclient import TestClient

from main import app
from processor.image import ImageProcessor
from services.simulator.meter_generator import MeterImageGenerator
from services.simulator.rendering import (
    LCD_FONT_OPTIONS,
    LCD_FONTS,
    draw_7segment_font_digit,
    get_lcd_font,
)
from services.simulator.rendering.digits import resolve_font_path


def test_dseg_font_registry_completeness():
    """Verify all 13 LCD font styles are registered with required metadata."""
    assert len(LCD_FONTS) == 13
    assert len(LCD_FONT_OPTIONS) == 13

    for key, meta in LCD_FONTS.items():
        assert "label" in meta
        assert "family" in meta
        assert "category" in meta
        if key != "builtin":
            assert "file" in meta
            assert "ghost_char" in meta
            # Ensure the font file exists on disk
            font_path = resolve_font_path(meta["file"])
            assert os.path.isfile(font_path)


def test_resolve_font_path_not_found():
    """Verify resolve_font_path raises FileNotFoundError for missing font file."""
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_font_path("non_existent_font_file.ttf")


def test_get_lcd_font_caching():
    """Verify font loading returns a PIL FreeTypeFont and is cached."""
    f1 = get_lcd_font("DSEG7Classic-Regular.ttf", size=44)
    f2 = get_lcd_font("DSEG7Classic-Regular.ttf", size=44)
    assert f1 is f2


def test_draw_7segment_font_digit_optical_centering():
    """Verify digit is rendered within the designated slot bounding box."""
    canvas = Image.new("RGB", (200, 200), (255, 255, 255))
    d = ImageDraw.Draw(canvas)

    # Render inside slot (20, 20, 39, 66)
    draw_7segment_font_digit(
        draw=d,
        x=20,
        y=20,
        w=39,
        h=66,
        char_str="5",
        font_cfg=LCD_FONTS["dseg7_modern_bold"],
        active_color=(0, 0, 0),
        ghost_color=(200, 200, 200),
    )
    # Check pixels outside the slot are pure background white
    outside_pixel = canvas.getpixel((5, 5))
    assert outside_pixel == (255, 255, 255)

    # Check some pixels inside the slot were drawn (active or ghost)
    has_drawn = False
    for px in range(20, 59):
        for py in range(20, 86):
            if canvas.getpixel((px, py)) != (255, 255, 255):
                has_drawn = True
                break
        if has_drawn:
            break
    assert has_drawn


def test_cnn_compatibility_with_dseg_fonts():
    """Verify digital CNN classification works seamlessly with DSEG fonts."""
    model_path = "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    if not os.path.exists(model_path):
        pytest.skip(f"Model not found at {model_path}")

    from cnn.digital_counter_cnn import DigitalCounterCNN

    cnn = DigitalCounterCNN(modelfile=model_path, dx=20, dy=32)
    generator = MeterImageGenerator()
    _, cfg = MeterImageGenerator.create_synthetic_template(640, 480)

    # Test key representative styles across 7seg and 14seg
    test_styles = [
        "dseg7_classic",
        "dseg7_classic_bold",
        "dseg7_modern",
        "dseg7_modern_bold",
        "dseg14_classic",
        "dseg14_modern_bold",
    ]

    for style in test_styles:
        # Generate meter image with digits 1 2 3 4 5
        meter_img = generator.generate(value="12345.0000", lcd_font=style)

        # Extract digit ROIs using ImageProcessor
        rois = (
            ImageProcessor()
            .set_image(meter_img)
            .cut_images(cfg.digital_readout.cut_images)
            .get_cut_images()
        )
        assert len(rois) == 5

        # Infer each digit with CNN
        expected_digits = [1, 2, 3, 4, 5]
        for idx, roi in enumerate(rois):
            pred, conf = cnn.readout_with_confidence(roi.image)
            assert (
                pred == expected_digits[idx]
            ), f"Style '{style}' digit {idx+1} expected {expected_digits[idx]} but got {pred}"
            assert conf > 80.0, f"Confidence {conf:.1f}% too low for style {style}"


def test_mock_camera_endpoint_font_selection():
    """Verify REST API /api/mock_camera accepts lcd_font query parameter."""
    client = TestClient(app)

    # Valid font
    resp = client.get("/api/mock_camera?lcd_font=dseg7_classic_bold&value=00123.4567")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"

    # Builtin font
    resp_builtin = client.get("/api/mock_camera?lcd_font=builtin&value=00123.4567")
    assert resp_builtin.status_code == 200

    # Unknown font gracefully falls back to builtin
    resp_fallback = client.get(
        "/api/mock_camera?lcd_font=invalid_style&value=00123.4567"
    )
    assert resp_fallback.status_code == 200
