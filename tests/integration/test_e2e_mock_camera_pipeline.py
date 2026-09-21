"""End-to-End integration test: Mock Camera image ingestion, ROI slicing, and readout pipeline."""

import io
import time

import PIL.Image
import pytest
import requests

from processor.image import ImageProcessor
from services.simulator.meter_generator import MeterImageGenerator


def test_e2e_mock_camera_direct_endpoint_and_headers():
    base_url = "http://localhost:3000"

    try:
        resp = requests.get(
            f"{base_url}/api/mock_camera?value=00123.4567",
            timeout=5,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Test application server is not running on http://localhost:3000")

    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "image/jpeg"
    assert resp.headers.get("x-mock-meter-value") == "00123.4567"
    assert resp.headers.get("x-mock-digital-value") == "00123"
    assert resp.headers.get("x-mock-analog-value") == "4567"

    # Verify image integrity
    img = PIL.Image.open(io.BytesIO(resp.content))
    img.verify()
    assert img.size == (640, 480)


def test_e2e_mock_camera_ticker_sequence_progression():
    base_url = "http://localhost:3000"

    try:
        resp_reset = requests.post(
            f"{base_url}/api/mock_camera/reset?start_value=350.0", timeout=5
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Test application server is not running on http://localhost:3000")

    assert resp_reset.status_code == 200

    readings = []
    for _ in range(3):
        resp = requests.get(
            f"{base_url}/api/mock_camera?mode=ticker&rate=0.025", timeout=5
        )
        assert resp.status_code == 200
        val_str = resp.headers.get("x-mock-meter-value")
        assert val_str is not None
        readings.append(float(val_str))
        time.sleep(0.05)

    assert len(readings) == 3
    # Assert monotonic increase
    assert readings[0] < readings[1] < readings[2]


def test_e2e_mock_camera_synthetic_pipeline_digitization():
    """End-to-end validation of synthetic template generation and ROI extraction."""
    img, synth_cfg = MeterImageGenerator.create_synthetic_template()

    proc = ImageProcessor()
    proc.image = img

    # Extract 5 digital cutouts
    proc_dig = ImageProcessor()
    proc_dig.image = img
    cut_digs = proc_dig.cut_images(
        synth_cfg.digital_readout.cut_images
    ).get_cut_images()
    assert len(cut_digs) == 5
    for cd in cut_digs:
        assert cd.image.size[0] > 0 and cd.image.size[1] > 0

    # Extract 4 analog cutouts
    proc_ana = ImageProcessor()
    proc_ana.image = img
    cut_anas = proc_ana.cut_images(synth_cfg.analog_readout.cut_images).get_cut_images()
    assert len(cut_anas) == 4
    for ca in cut_anas:
        assert ca.image.size[0] > 0 and ca.image.size[1] > 0


def test_e2e_mock_camera_server_readout_and_roi_endpoints():
    base_url = "http://localhost:3000"

    try:
        resp_meter = requests.get(
            f"{base_url}/meter?format=json&saveimages=true",
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Test application server is not running on http://localhost:3000")

    assert resp_meter.status_code == 200
    data = resp_meter.json()

    assert "meters" in data
    assert "digital_results" in data
    assert "analog_results" in data
    assert "confidence_scores" in data
    assert "error" in data

    # Verify /roi endpoint produces valid image
    resp_roi = requests.get(f"{base_url}/roi", timeout=5)
    assert resp_roi.status_code == 200
    assert resp_roi.headers.get("content-type") == "image/jpeg"
    roi_img = PIL.Image.open(io.BytesIO(resp_roi.content))
    roi_img.verify()
    assert roi_img.size[0] > 0 and roi_img.size[1] > 0
