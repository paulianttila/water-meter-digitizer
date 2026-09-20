from PIL import Image, ImageDraw

from configuration import MeterConfig
from processor.digitizer import (
    MODEL_DIGITAL,
    DigitizerProcessor,
    ReadoutResult,
)
from processor.sign_detector import detect_minus_sign
from simulator.meter_generator import MeterImageGenerator


def _create_synthetic_minus_image(
    w: int = 35,
    h: int = 55,
    bg_color: tuple[int, int, int] = (205, 218, 205),
    stroke_color: tuple[int, int, int] = (15, 20, 25),
    bar_width: int = 22,
    bar_height: int = 6,
) -> Image.Image:
    """Create a synthetic digit ROI with a central horizontal minus bar."""
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    x0 = (w - bar_width) // 2
    y0 = (h - bar_height) // 2
    draw.rectangle([x0, y0, x0 + bar_width, y0 + bar_height], fill=stroke_color)
    return img


def _create_synthetic_digit_8_image(
    w: int = 35,
    h: int = 55,
    bg_color: tuple[int, int, int] = (205, 218, 205),
    stroke_color: tuple[int, int, int] = (15, 20, 25),
) -> Image.Image:
    """Create a synthetic '8' digit image (should NOT be detected as minus sign)."""
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    # Outer box + middle bar
    draw.rectangle([6, 6, w - 6, h - 6], outline=stroke_color, width=4)
    draw.line([6, h // 2, w - 6, h // 2], fill=stroke_color, width=4)
    return img


def _create_synthetic_vertical_line_image(
    w: int = 35,
    h: int = 55,
    bg_color: tuple[int, int, int] = (205, 218, 205),
    stroke_color: tuple[int, int, int] = (15, 20, 25),
) -> Image.Image:
    """Create a synthetic '1' / vertical bar image (should NOT be detected as minus sign)."""
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(w // 2) - 2, 6, (w // 2) + 2, h - 6], fill=stroke_color)
    return img


class TestSignDetector:
    """Tests for the detect_minus_sign CV morphology function."""

    def test_detect_minus_sign_positive(self):
        img = _create_synthetic_minus_image()
        is_minus, conf = detect_minus_sign(img)
        assert is_minus is True
        assert conf >= 60.0

    def test_detect_minus_sign_inverted_polarity(self):
        # Light LCD text on dark background
        img = _create_synthetic_minus_image(
            bg_color=(20, 30, 20), stroke_color=(220, 250, 220)
        )
        is_minus, conf = detect_minus_sign(img)
        assert is_minus is True
        assert conf >= 60.0

    def test_detect_minus_sign_rejects_digit_8(self):
        img = _create_synthetic_digit_8_image()
        is_minus, _conf = detect_minus_sign(img)
        assert is_minus is False

    def test_detect_minus_sign_rejects_vertical_line(self):
        img = _create_synthetic_vertical_line_image()
        is_minus, _conf = detect_minus_sign(img)
        assert is_minus is False

    def test_detect_minus_sign_rejects_blank_image(self):
        img = Image.new("RGB", (35, 55), (205, 218, 205))
        is_minus, conf = detect_minus_sign(img)
        assert is_minus is False
        assert conf == 0.0

    def test_detect_minus_sign_empty_or_tiny(self):
        img = Image.new("RGB", (2, 2), (0, 0, 0))
        is_minus, conf = detect_minus_sign(img)
        assert is_minus is False
        assert conf == 0.0

    def test_detect_minus_sign_from_meter_generator(self):
        gen = MeterImageGenerator()
        # Generate negative reading image
        img = gen.generate(value="-0012.3456")
        # Crop digit1 (which is rendered with a 7-segment minus sign)
        # LCD digit1 position: (202, 150, 39, 66)
        digit1_crop = img.crop((202, 150, 202 + 39, 150 + 66))
        is_minus, conf = detect_minus_sign(digit1_crop)
        assert is_minus is True
        assert conf >= 60.0

        # Crop digit2 (which is rendered with digit '0') -> should be False
        digit2_crop = img.crop((202 + 49, 150, 202 + 49 + 39, 150 + 66))
        is_minus_d2, _ = detect_minus_sign(digit2_crop)
        assert is_minus_d2 is False


class TestDigitizerProcessorMinusSign:
    """Tests for minus sign handling in DigitizerProcessor."""

    def test_evaluate_counters_with_minus_sign(self):
        processor = DigitizerProcessor()
        values = [
            ReadoutResult(
                name="digit1", value="-", model=MODEL_DIGITAL, confidence=95.0
            ),
            ReadoutResult(
                name="digit2", value=0.0, model=MODEL_DIGITAL, confidence=99.0
            ),
            ReadoutResult(
                name="digit3", value=4.0, model=MODEL_DIGITAL, confidence=99.0
            ),
            ReadoutResult(
                name="digit4", value=2.0, model=MODEL_DIGITAL, confidence=99.0
            ),
        ]
        evaluated = processor._evaluate_counters(values)
        assert evaluated == {
            "digit1": "-",
            "digit2": "0",
            "digit3": "4",
            "digit4": "2",
        }

    def test_template_formatting_with_minus_sign(self):
        meter_cfg = MeterConfig(
            name="total",
            format="{digit1}{digit2}{digit3}{digit4}",
        )
        values = {
            "digit1": "-",
            "digit2": "0",
            "digit3": "4",
            "digit4": "2",
        }
        meter_val = meter_cfg.format.format(**values)
        assert meter_val == "-042"

    def test_rate_consistency_with_negative_reading(self):
        meter_cfg = MeterConfig(
            name="total",
            format="{digit1}{digit2}",
            consistency_enabled=True,
            allow_negative_rates=True,
            max_rate_value=5.0,
        )
        from processor.consistency_validator import ConsistencyValidator

        # Negative rate check: previous is -10.0, current is -12.0 (delta = -2.0 <= 5.0)
        ConsistencyValidator.validate_reading(
            meter_cfg, current_value="-12.0", previous_value="-10.0"
        )

    def test_detect_negative_sign_toggle(self):
        processor = DigitizerProcessor()
        assert processor.detect_negative_sign is False
        processor.set_detect_negative_sign(True)
        assert processor.detect_negative_sign is True
