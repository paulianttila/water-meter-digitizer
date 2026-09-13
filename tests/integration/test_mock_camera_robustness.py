"""Tests for mock camera perturbations, glare injection, rotation, and theme rendering."""

import PIL.Image

from processor.image import ImageProcessor
from testing.meter_generator import MeterImageGenerator


def test_mock_camera_glare_suppression():
    """Verify mock camera glare injection and CV glare suppression."""
    generator = MeterImageGenerator()
    glare_img = generator.generate(
        value="00452.91241",
        glare=True,
        glare_intensity=1.8,
        glare_pos=(0.5, 0.35),
    )

    proc = ImageProcessor()
    proc.image = glare_img

    # Apply CLAHE glare suppression
    proc.suppress_glare(mode="clahe", clahe_clip_limit=2.0)
    clahe_out = proc.get_image()
    assert clahe_out.size == (640, 480)

    # Apply Inpaint glare suppression
    proc.image = glare_img
    proc.suppress_glare(mode="inpaint", inpaint_threshold=230, inpaint_radius=3)
    inpaint_out = proc.get_image()
    assert inpaint_out.size == (640, 480)


def test_mock_camera_rotation_and_noise():
    """Verify camera tilt, noise, and image filtering."""
    generator = MeterImageGenerator()

    for rot in (5.0, -5.0, 15.0):
        tilted_img = generator.generate(
            value="00452.91241",
            rotate=rot,
            noise=10.0,
            blur=1.0,
        )

        proc = ImageProcessor()
        proc.image = tilted_img
        proc.rotate_image(-rot)
        proc.adjust_image(brightness=1.1, contrast=1.2)

        out = proc.get_image()
        assert isinstance(out, PIL.Image.Image)
        assert out.size[0] > 0 and out.size[1] > 0


def test_mock_camera_lcd_themes_and_overrides():
    """Verify LCD color styling and custom digit/dial overrides."""
    generator = MeterImageGenerator()

    themes = [
        ("amber", "dark", "red"),
        ("green", "grey", "black"),
        ("black", "green", "blue"),
    ]

    for lcd_c, lcd_bg, needle_c in themes:
        img = generator.generate(
            value="00555.2222",
            lcd_color=lcd_c,
            lcd_bg=lcd_bg,
            needle_color=needle_c,
            custom_digital_values={"digit1": 8.0},
            custom_analog_values={"analog1": 4.0},
        )

        assert isinstance(img, PIL.Image.Image)
        assert img.size == (640, 480)


def test_mock_camera_cnn_digit_and_analog_recognition():
    """Verify class11 digit and top continuous analog neural networks recognize mock meter outputs."""
    from processor.digitizer import DigitizerProcessor

    dig_model = "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    ana_model = "config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite"

    target = "14568.4157"
    generator = MeterImageGenerator()
    img = generator.generate(value=target)
    _, synth_cfg = MeterImageGenerator.create_synthetic_template()

    proc_dig = ImageProcessor().set_image(img)
    cut_digs = proc_dig.cut_images(
        synth_cfg.digital_readout.cut_images
    ).get_cut_images()

    proc_ana = ImageProcessor().set_image(img)
    cut_anas = proc_ana.cut_images(synth_cfg.analog_readout.cut_images).get_cut_images()

    dp = (
        DigitizerProcessor()
        .init_digital_model(dig_model, "digital")
        .init_analog_model(ana_model, "analog")
    )
    dp.execute_digital_cnn(cut_digs)
    dp.execute_analog_cnn(cut_anas)

    # 1. Verify digital digits match target (1, 4, 5, 6, 8) with >= 90% confidence
    for d, exp in zip(dp.cnn_digital_results, [1, 4, 5, 6, 8], strict=True):
        assert round(d.value) == exp, f"{d.name} expected {exp}, got {d.value}"
        assert (
            d.confidence >= 90.0
        ), f"{d.name} confidence {d.confidence}% below threshold"

    # 2. Verify analog needles match target angles (~4, 1, 5, 7) with >= 90% confidence
    for a, exp in zip(dp.cnn_analog_results, [4, 1, 5, 7], strict=True):
        assert abs(a.value - exp) <= 1.0, f"{a.name} expected ~{exp}, got {a.value}"
        assert (
            a.confidence >= 90.0
        ), f"{a.name} confidence {a.confidence}% below threshold"
