"""Unit tests for procedural Water Meter Generator and Mock Camera endpoint."""

import os

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from simulator.cli import main as cli_main
from simulator.meter_generator import MeterImageGenerator


def test_generator_initialization_and_default_generate():
    generator = MeterImageGenerator()
    img = generator.generate(value="00452.91241")

    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.size == (640, 480)


def test_generator_value_parsing():
    generator = MeterImageGenerator()
    dig_states, dial_states = generator._parse_meter_values("00789.1234")

    assert dig_states["digit1"] == 0.0
    assert dig_states["digit2"] == 0.0
    assert dig_states["digit3"] == 7.0
    assert dig_states["digit4"] == 8.0
    assert dig_states["digit5"] == 9.0

    assert dial_states["analog1"] == 1.2
    assert dial_states["analog2"] == 2.3
    assert dial_states["analog3"] == 3.4
    assert dial_states["analog4"] == 4.0


def test_generator_lcd_digits_overlay():
    generator = MeterImageGenerator()
    img = generator.generate(
        value="00789.1234",
        lcd_color="amber",
        lcd_bg="dark",
    )
    assert isinstance(img, Image.Image)
    assert img.size == (640, 480)


def test_generator_meter_bg_themes():
    generator = MeterImageGenerator()
    themes = ["white", "grey", "blue", "brass", "dark", "aged", "silver", "gold"]
    for theme_name in themes:
        img = generator.generate(value="00123.4567", meter_bg=theme_name)
        assert isinstance(img, Image.Image)
        assert img.size == (640, 480)

    # Verify dark background has different pixel characteristics from white
    img_white = generator.generate(value="00000.0000", meter_bg="white")
    img_dark = generator.generate(value="00000.0000", meter_bg="dark")
    # Dial face area (320, 80) is above the LCD window
    p_white = img_white.getpixel((320, 80))
    p_dark = img_dark.getpixel((320, 80))
    assert sum(p_white) > sum(p_dark)


def test_generator_synthetic_template():
    img, cfg = MeterImageGenerator.create_synthetic_template(640, 480)

    assert isinstance(img, Image.Image)
    assert img.size == (640, 480)
    assert len(cfg.digital_readout.cut_images) == 5
    assert len(cfg.analog_readout.cut_images) == 4
    assert len(cfg.alignment.ref_images) == 3
    assert len(cfg.meter_configs) == 1
    assert cfg.meter_configs[0].name == "total"


def test_generator_create_mock_meter_config():
    cfg = MeterImageGenerator.create_mock_meter_config(
        width=800,
        height=600,
        url="http://localhost:3000/api/mock_camera",
    )

    assert len(cfg.digital_readout.cut_images) == 5
    assert len(cfg.analog_readout.cut_images) == 4
    assert cfg.digital_readout.enabled is True
    assert cfg.analog_readout.enabled is True
    assert cfg.crop.enabled is False
    assert cfg.resize.enabled is False
    assert cfg.image_source.url == "http://localhost:3000/api/mock_camera"
    assert len(cfg.meter_configs) == 1
    assert cfg.meter_configs[0].name == "total"


def test_generator_perturbations():
    generator = MeterImageGenerator()
    base_img = Image.new("RGB", (200, 200), (128, 128, 128))

    rot_img = generator.apply_perturbations(base_img, rotate=15.0)
    assert rot_img.size == (200, 200)

    glare_img = generator.apply_perturbations(base_img, glare=True, glare_intensity=1.5)
    assert glare_img.size == (200, 200)

    noise_img = generator.apply_perturbations(base_img, noise=10.0)
    assert noise_img.size == (200, 200)

    bright_img = generator.apply_perturbations(base_img, brightness=1.3, contrast=1.2)
    assert bright_img.size == (200, 200)

    blur_img = generator.apply_perturbations(base_img, blur=2.0)
    assert blur_img.size == (200, 200)


def test_generator_sequence():
    generator = MeterImageGenerator()
    frames = generator.generate_sequence(
        start_value=100.0,
        rate_per_frame=0.01,
        count=3,
    )
    assert len(frames) == 3
    for f in frames:
        assert isinstance(f, Image.Image)


def test_generator_cli_execution(tmp_path, monkeypatch):
    out_file = str(tmp_path / "test_out.jpg")
    test_args = [
        "meter-generator",
        "--value",
        "00789.1234",
        "--meter-bg",
        "brass",
        "--output",
        out_file,
    ]
    monkeypatch.setattr("sys.argv", test_args)
    cli_main()

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000


def test_generator_cli_synthetic_template(tmp_path, monkeypatch):
    out_file = str(tmp_path / "synthetic.jpg")
    test_args = [
        "meter-generator",
        "--synthetic-template",
        "--output",
        out_file,
    ]
    monkeypatch.setattr("sys.argv", test_args)
    cli_main()

    assert os.path.exists(out_file)
    assert os.path.exists(str(tmp_path / "synthetic.ini"))


def test_mock_camera_endpoint():
    client = TestClient(app)

    # 1. Fixed value frame
    resp = client.get("/api/mock_camera?value=00789.1234&meter_bg=dark")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.headers.get("x-mock-meter-value") == "00789.1234"
    assert resp.headers.get("x-mock-digital-value") == "00789"
    assert resp.headers.get("x-mock-analog-value") == "1234"
    assert len(resp.content) > 1000

    # 2. Ticker mode
    client.post("/api/mock_camera/reset?start_value=500.0")
    resp_tick1 = client.get("/api/mock_camera?mode=ticker&rate=1.0")
    assert resp_tick1.status_code == 200
    val1 = resp_tick1.headers.get("x-mock-meter-value")

    resp_tick2 = client.get("/api/mock_camera?mode=ticker&rate=1.0")
    assert resp_tick2.status_code == 200
    val2 = resp_tick2.headers.get("x-mock-meter-value")

    assert val1 != val2

    # 3. Random mode
    resp_rand = client.get("/api/mock_camera?mode=random")
    assert resp_rand.status_code == 200

    # 4. Custom overrides and colors
    resp_custom = client.get(
        "/api/mock_camera?value=00123.4567&lcd_color=amber&lcd_bg=dark&meter_bg=blue&needle_color=black&digit1=5&analog1=9"
    )
    assert resp_custom.status_code == 200


def test_generator_standard_resolutions():
    generator = MeterImageGenerator()
    standard_sizes = [
        (640, 480),
        (800, 600),
        (1024, 768),
        (1600, 1200),
    ]
    for w, h in standard_sizes:
        img = generator.generate(
            value="00452.91241",
            width=w,
            height=h,
            glare=True,
            glare_pos=(320, 240),
            noise=5.0,
        )
        assert isinstance(img, Image.Image)
        assert img.size == (w, h)


def test_create_synthetic_template_scaling():
    # 640x480 base
    img_base, cfg_base = MeterImageGenerator.create_synthetic_template(640, 480)
    assert img_base.size == (640, 480)

    # 1600x1200 scaled
    img_scaled, cfg_scaled = MeterImageGenerator.create_synthetic_template(1600, 1200)
    assert img_scaled.size == (1600, 1200)

    # Ratio should be 2.5x (1600/640)
    ratio_x = 1600 / 640.0
    ratio_y = 1200 / 480.0

    assert cfg_scaled.digital_readout.cut_images[0].x == round(
        cfg_base.digital_readout.cut_images[0].x * ratio_x
    )
    assert cfg_scaled.digital_readout.cut_images[0].w == round(
        cfg_base.digital_readout.cut_images[0].w * ratio_x
    )
    assert cfg_scaled.analog_readout.cut_images[0].y == round(
        cfg_base.analog_readout.cut_images[0].y * ratio_y
    )
    assert cfg_scaled.alignment.ref_images[0].x == round(
        cfg_base.alignment.ref_images[0].x * ratio_x
    )


def test_meter_generator_glare_injection():
    import numpy as np

    generator = MeterImageGenerator()
    img_no_glare = generator.generate(
        value="00452.91241", width=640, height=480, glare=False
    )
    img_glare_pixel = generator.generate(
        value="00452.91241",
        width=640,
        height=480,
        glare=True,
        glare_pos=(320, 240),
        glare_intensity=1.5,
    )
    img_glare_norm = generator.generate(
        value="00452.91241",
        width=640,
        height=480,
        glare=True,
        glare_pos=(0.5, 0.5),
        glare_intensity=1.5,
    )

    arr_no_glare = np.array(img_no_glare, dtype=np.float32)
    arr_glare_pixel = np.array(img_glare_pixel, dtype=np.float32)
    arr_glare_norm = np.array(img_glare_norm, dtype=np.float32)

    # Hotspot center region (320, 240) must be significantly brighter with glare
    assert np.mean(arr_glare_pixel[235:245, 315:325]) > np.mean(
        arr_no_glare[235:245, 315:325]
    )
    # Normalized (0.5, 0.5) and absolute (320, 240) on 640x480 should be identical
    np.testing.assert_allclose(arr_glare_pixel, arr_glare_norm, atol=1.0)
