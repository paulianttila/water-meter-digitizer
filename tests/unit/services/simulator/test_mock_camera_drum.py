"""Unit tests for mechanical odometer drum counter in Mock Camera Simulator."""

import os

import pytest
from PIL import Image
from starlette.testclient import TestClient

from main import app
from processor.image import ImageProcessor
from services.simulator.meter_generator import MeterImageGenerator
from services.simulator.rendering import (
    DRUM_THEME_OPTIONS,
    DRUM_THEMES,
    compute_drum_wheel_positions,
    draw_drum_wheel,
    get_drum_font,
)
from services.simulator.rendering.drum import resolve_drum_font_path


def test_drum_theme_registry():
    """Verify drum themes and options are properly defined."""
    assert len(DRUM_THEMES) >= 5
    assert "standard" in DRUM_THEMES
    assert "classic_black" in DRUM_THEMES
    assert "classic_white" in DRUM_THEMES
    assert "red_decimals_2" in DRUM_THEMES
    assert "industrial" in DRUM_THEMES

    for key, theme in DRUM_THEMES.items():
        assert "label" in theme
        assert "int_bg" in theme
        assert "int_fg" in theme
        assert "dec_bg" in theme
        assert "dec_fg" in theme
        assert "decimal_wheels" in theme
        assert key in DRUM_THEME_OPTIONS


def test_resolve_drum_font_path():
    """Verify font path resolution and missing file error."""
    path = resolve_drum_font_path("Arimo.ttf")
    assert os.path.isfile(path)
    assert path.endswith("Arimo.ttf")

    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_drum_font_path("NonExistentDrumFont.ttf")


def test_get_drum_font_caching():
    """Verify drum font caching."""
    f1 = get_drum_font(48)
    f2 = get_drum_font(48)
    assert f1 is f2


def test_geneva_carry_mechanics():
    """Verify Geneva carry mechanism calculates correct rollover progression."""
    # Case 1: All stationary whole integers
    states = {"digit1": 0.0, "digit2": 0.0, "digit3": 4.0, "digit4": 5.0, "digit5": 2.0}
    positions = compute_drum_wheel_positions(states, carry_mode="geneva")
    assert positions == [0.0, 0.0, 4.0, 5.0, 2.0]

    # Case 2: digit5 is rolling before turnover threshold (e.g. 2.7)
    states_mid = {
        "digit1": 0.0,
        "digit2": 0.0,
        "digit3": 4.0,
        "digit4": 5.0,
        "digit5": 2.7,
    }
    pos_mid = compute_drum_wheel_positions(states_mid, carry_mode="geneva")
    assert pos_mid[4] == 2.7
    assert pos_mid[3] == 5.0  # digit4 does not roll yet

    # Case 3: digit5 is in rollover turnover window (e.g. 9.4)
    states_roll = {
        "digit1": 0.0,
        "digit2": 0.0,
        "digit3": 4.0,
        "digit4": 5.0,
        "digit5": 9.4,
    }
    pos_roll = compute_drum_wheel_positions(states_roll, carry_mode="geneva")
    assert pos_roll[4] == 9.4
    assert pytest.approx(pos_roll[3], rel=1e-3) == 5.4  # digit4 has rolled by 0.4!

    # Case 4: Continuous carry mode passes raw float states directly
    pos_cont = compute_drum_wheel_positions(states_mid, carry_mode="continuous")
    assert pos_cont == [0.0, 0.0, 4.0, 5.0, 2.7]


def test_draw_drum_wheel_rendering():
    """Verify single drum wheel rendering with 3D curvature shading."""
    canvas = Image.new("RGB", (100, 100), (255, 255, 255))
    font = get_drum_font(48)

    # Render wheel in slot (10, 10, 39, 66) at position 4.5
    draw_drum_wheel(
        canvas=canvas,
        x=10,
        y=10,
        w=39,
        h=66,
        roll_val=4.5,
        bg_color=(20, 20, 20),
        fg_color=(240, 240, 240),
        font=font,
        pitch=48,
    )

    # Check that inside slot is non-white
    assert canvas.getpixel((25, 25)) != (255, 255, 255)
    # Check top/bottom shadows darken the edge pixels
    top_shadow_pixel = canvas.getpixel((25, 11))
    center_pixel = canvas.getpixel((25, 43))
    # Top edge should be darker than or equal to base drum due to shading
    assert sum(top_shadow_pixel) <= sum(center_pixel) + 100


def test_drum_wheel_transition_clipped_to_aperture():
    """Verify that during rollover transitions (e.g. 2.9), both numerals are strictly clipped to slot."""
    canvas = Image.new("RGB", (100, 100), (0, 0, 0))
    font = get_drum_font(48)

    # Slot from x: 10 to 49, y: 10 to 76 (w=39, h=66)
    draw_drum_wheel(
        canvas=canvas,
        x=10,
        y=10,
        w=39,
        h=66,
        roll_val=2.91241,
        bg_color=(22, 24, 28),
        fg_color=(255, 255, 255),
        font=font,
        pitch=48,
    )

    # Any pixel strictly outside the slot bounds (0 <= x < 10 or 49 <= x < 100, 0 <= y < 10 or 76 <= y < 100)
    # MUST remain untouched (0, 0, 0)
    for px in range(100):
        for py in range(100):
            if not (10 <= px < 49 and 10 <= py < 76):
                assert canvas.getpixel((px, py)) == (
                    0,
                    0,
                    0,
                ), f"Pixel at ({px}, {py}) spilled outside wheel slot bounds!"

    # Also test full meter generation for 00452.91241: no text spill above/below bezel
    generator = MeterImageGenerator()
    meter_img = generator.generate(
        value="00452.91241",
        counter_type="drum",
        drum_style="standard",
    )
    # Bezel window is y: 144 to 228. Check region well above (y: 110-140) in digit5 column (x: 398 to 437)
    # to ensure digits '2' or '3' did not bleed onto the meter faceplate
    for y_check in range(110, 140):
        for x_check in range(398, 437):
            r, g, b = meter_img.getpixel((x_check, y_check))
            # Digit text foreground is bright white (255, 255, 255); faceplate is off-white/beige (~230-245)
            # Make sure no pure white digit text pixels exist above bezel
            assert not (
                r > 250 and g > 250 and b > 250
            ), f"Digit spilled at ({x_check}, {y_check})"


def test_meter_generator_with_drum_counter():
    """Verify MeterImageGenerator renders complete frames with mechanical drum counter."""
    generator = MeterImageGenerator()

    # Render each drum theme
    for theme_name in DRUM_THEMES:
        img = generator.generate(
            value="00452.75000",
            counter_type="drum",
            drum_style=theme_name,
            drum_carry="geneva",
        )
        assert isinstance(img, Image.Image)
        assert img.size == (640, 480)

    # Compare drum counter pixels vs LCD counter pixels
    img_lcd = generator.generate(value="00452.00000", counter_type="lcd")
    img_drum = generator.generate(value="00452.00000", counter_type="drum")
    assert img_lcd.tobytes() != img_drum.tobytes()


def test_cnn_accuracy_on_drum_digits():
    """Verify DigitalCounterCNN recognizes whole drum numerals with high confidence."""
    model_path = "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    if not os.path.exists(model_path):
        pytest.skip(f"Model not found at {model_path}")

    from cnn.digital_counter_cnn import DigitalCounterCNN

    cnn = DigitalCounterCNN(modelfile=model_path, dx=20, dy=32)
    generator = MeterImageGenerator()
    _, cfg = MeterImageGenerator.create_synthetic_template(640, 480)

    meter_img = generator.generate(
        value="01234.00000",
        counter_type="drum",
        drum_style="standard",
    )

    rois = (
        ImageProcessor()
        .set_image(meter_img)
        .cut_images(cfg.digital_readout.cut_images)
        .get_cut_images()
    )
    assert len(rois) == 5

    expected_digits = [0, 1, 2, 3, 4]
    for idx, roi in enumerate(rois):
        pred, conf = cnn.readout_with_confidence(roi.image)
        assert (
            pred == expected_digits[idx]
        ), f"Digit {idx+1} expected {expected_digits[idx]} but got {pred}"
        assert (
            conf > 90.0
        ), f"Confidence {conf:.1f}% too low for drum digit {expected_digits[idx]}"


def test_mock_camera_endpoint_drum_counter():
    """Verify REST API endpoint accepts counter_type and drum parameters."""
    client = TestClient(app)

    # Standard drum request
    resp = client.get(
        "/api/mock_camera?counter_type=drum&drum_style=standard&drum_carry=geneva&value=00789.4"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) > 1000

    # Vintage all-white drum
    resp_white = client.get(
        "/api/mock_camera?counter_type=drum&drum_style=classic_white&value=12345.0"
    )
    assert resp_white.status_code == 200
    assert len(resp_white.content) > 1000
