"""Unit tests for procedural Water Meter Generator and Mock Camera endpoint."""

import os

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from testing.cli import main as cli_main
from testing.meter_generator import MeterImageGenerator


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


def test_generator_synthetic_template():
    img, cfg = MeterImageGenerator.create_synthetic_template(640, 480)

    assert isinstance(img, Image.Image)
    assert img.size == (640, 480)
    assert len(cfg.digital_readout.cut_images) == 5
    assert len(cfg.analog_readout.cut_images) == 4
    assert len(cfg.alignment.ref_images) == 3
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
    resp = client.get("/api/mock_camera?value=00789.1234")
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
        "/api/mock_camera?value=00123.4567&lcd_color=amber&lcd_bg=dark&needle_color=black&digit1=5&analog1=9"
    )
    assert resp_custom.status_code == 200
