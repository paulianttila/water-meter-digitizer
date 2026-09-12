"""Unit tests for meter readout, ROI visualization, baseline settings, and image cache endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from configuration import Config, MeterConfig, ZeroFlowMonitor
from main import app
from processor.digitizer import MeterResult, MeterValue
from utils.download import DownloadFailure


@pytest.fixture(autouse=True)
def restore_app_state():
    orig_config = getattr(app.state, "config", None)
    orig_storage = getattr(app.state, "storage", None)
    orig_mqtt = getattr(app.state, "mqtt_service", None)
    orig_tracker = getattr(app.state, "zero_flow_tracker", None)
    yield
    app.state.config = orig_config
    app.state.storage = orig_storage
    app.state.mqtt_service = orig_mqtt
    app.state.zero_flow_tracker = orig_tracker


def test_get_image_endpoint():
    client = TestClient(app)

    # 1. Miss -> 404
    resp_404 = client.get("/image/nonexistent_image")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"] == "Image not found"

    # 2. Hit with PIL Image in cache
    test_img = Image.new("RGB", (60, 60), color="blue")
    app.state.image_cache.set("cached_test", test_img)

    resp_hit = client.get("/image/cached_test.jpg")
    assert resp_hit.status_code == 200
    assert resp_hit.headers["content-type"] == "image/jpeg"
    assert len(resp_hit.content) > 0


def test_get_roi_endpoint():
    client = TestClient(app)

    # Success case with mocked ImageProcessor
    dummy_img = Image.new("RGB", (100, 100), color="red")
    with patch("api.routes_meter.ImageProcessor") as mock_proc_cls:
        mock_proc = MagicMock()
        mock_proc.download_image.return_value = mock_proc
        mock_proc.rotate_image.return_value = mock_proc
        mock_proc.align_image.return_value = mock_proc
        mock_proc.draw_meter_rois.return_value = mock_proc
        mock_proc.get_image.return_value = dummy_img
        mock_proc_cls.return_value = mock_proc

        resp = client.get(
            "/roi?url=http://example.com/meter.jpg&draw_refs=true&draw_digital=true&draw_analog=false"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert len(resp.content) > 0

    # DownloadFailure -> 502
    with patch("api.routes_meter.ImageProcessor") as mock_proc_cls:
        mock_proc = MagicMock()
        mock_proc.download_image.side_effect = DownloadFailure("Connection timeout")
        mock_proc_cls.return_value = mock_proc

        resp_fail = client.get("/roi?url=http://bad.url/meter.jpg")
        assert resp_fail.status_code == 502
        assert "Connection timeout" in resp_fail.json()["error"]

    # General Exception -> 500
    with patch("api.routes_meter.ImageProcessor") as mock_proc_cls:
        mock_proc = MagicMock()
        mock_proc.download_image.side_effect = RuntimeError("Unexpected internal bug")
        mock_proc_cls.return_value = mock_proc

        resp_err = client.get("/roi?url=http://bad.url/meter.jpg")
        assert resp_err.status_code == 500
        assert "Unexpected internal bug" in resp_err.json()["error"]


def test_set_previous_value_validation(tmp_path):
    client = TestClient(app)
    prev_file = tmp_path / "prevalue.ini"
    app.state.config.previous_value_file = str(prev_file)

    # 1. Valid setting
    resp = client.get("/setPreviousValue?name=total&value=123.456")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["meter"] == "total"
    assert body["value"] == "123.456"

    # 2. Empty value -> 400
    resp_empty = client.get("/set_previous_value?name=total&value=")
    assert resp_empty.status_code == 400
    assert "empty" in resp_empty.json()["message"].lower()

    # 3. Non-numeric value -> 400
    resp_nonnum = client.get("/setPreviousValue?name=total&value=abc")
    assert resp_nonnum.status_code == 400
    assert "not a number" in resp_nonnum.json()["message"].lower()

    # 4. Negative value -> 400
    resp_neg = client.get("/setPreviousValue?name=total&value=-10.5")
    assert resp_neg.status_code == 400
    assert "negative" in resp_neg.json()["message"].lower()

    # 5. Empty meter name -> 400
    resp_noname = client.get("/setPreviousValue?name=&value=100.0")
    assert resp_noname.status_code == 400
    assert "meter name cannot be empty" in resp_noname.json()["message"].lower()


def test_get_previous_values_endpoint(tmp_path):
    client = TestClient(app)
    prev_file = tmp_path / "prevalue.ini"
    app.state.config.previous_value_file = str(prev_file)

    # Configure meter with use_previous_value
    app.state.config.meter_configs = [
        MeterConfig(
            name="total",
            format="{d1}",
            use_previous_value=True,
            unit="m3",
            pre_value_from_file_max_age=60,
        ),
        MeterConfig(name="flow", format="{d1}", use_previous_value=False, unit="l/min"),
    ]

    with patch(
        "previous_value.get_all_previous_values",
        return_value={
            "total": {"value": "200.500", "time": "2026-09-12 10:00:00"},
            "flow": {"value": "1.2", "time": "2026-09-12 10:00:00"},
        },
    ):
        resp = client.get("/get_previous_values")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["meters"]) == 1
        assert data["meters"][0]["name"] == "total"
        assert data["meters"][0]["value"] == "200.500"

    # When no meters have use_previous_value=True, fallback finds 'total'
    app.state.config.meter_configs = [
        MeterConfig(name="total", format="{d1}", use_previous_value=False, unit="m3")
    ]
    with patch(
        "previous_value.get_all_previous_values",
        return_value={"total": {"value": "300.000", "time": "2026-09-12 10:00:00"}},
    ):
        resp2 = client.get("/getPreviousValues")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["meters"]) == 1
        assert data2["meters"][0]["name"] == "total"


def test_get_meters_endpoint_formatting():
    client = TestClient(app)

    dummy_result = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="543.210",
                unit="m3",
                quality="good",
                confidence=99.0,
            )
        ],
        digital_results={"0": "5"},
        analog_results={},
        error="",
    )

    # 1. Invalid format -> 400
    resp_inv = client.get("/meter?format=xml")
    assert resp_inv.status_code == 400
    assert "Invalid format" in resp_inv.json()["error"]

    # 2. JSON format -> 200 JSON
    with patch("api.routes_meter.get_meter_data", return_value=dummy_result):
        resp_json = client.get("/meter?format=json")
        assert resp_json.status_code == 200
        assert resp_json.json()["meters"][0]["value"] == "543.210"

    # 3. Value format -> 200 plain text
    with patch("api.routes_meter.get_meter_data", return_value=dummy_result):
        resp_val = client.get("/meter?format=value")
        assert resp_val.status_code == 200
        assert resp_val.text == "543.210"
        assert resp_val.headers["content-type"].startswith("text/plain")

    # 4. Raw format -> 200 plain text
    with patch("api.routes_meter.get_meter_data", return_value=dummy_result):
        resp_raw = client.get("/meter?format=raw")
        assert resp_raw.status_code == 200
        assert resp_raw.text == "543.210"

    # 5. Error in get_meter_data -> 500
    with patch(
        "api.routes_meter.get_meter_data", side_effect=RuntimeError("Camera offline")
    ):
        resp_err = client.get("/meter")
        assert resp_err.status_code == 500
        assert "Camera offline" in resp_err.json()["error"]


def test_get_meter_data_pipeline(tmp_path):
    from api.routes_meter import get_meter_data

    # Setup config with image source, storage, mqtt, zero flow monitor
    cfg = Config()
    cfg.image_source.url = "http://fake-camera.local/stream.jpg"
    cfg.zero_flow_monitor = ZeroFlowMonitor(enabled=True, meter_name="total")
    cfg.mqtt.enabled = True

    app.state.config = cfg

    # Mock storage, mqtt, tracker
    mock_storage = MagicMock()
    mock_mqtt = MagicMock()
    mock_tracker = MagicMock()

    app.state.storage = mock_storage
    app.state.mqtt_service = mock_mqtt
    app.state.zero_flow_tracker = mock_tracker

    dummy_frame = Image.new("RGB", (100, 100), color="green")
    dummy_result = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="100.250",
                unit="m3",
                quality="good",
                confidence=98.0,
            )
        ],
        digital_results={},
        analog_results={},
        error="",
    )

    with (
        patch("api.routes_meter.ImageProcessor") as mock_proc_cls,
        patch("api.routes_meter.DigitizerProcessor") as mock_dig_cls,
    ):
        mock_proc = MagicMock()
        mock_proc.enable_image_saving.return_value = mock_proc
        mock_proc.download_image.return_value = mock_proc
        mock_proc.save_image.return_value = mock_proc
        mock_proc.rotate_image.return_value = mock_proc
        mock_proc.align_image.return_value = mock_proc
        mock_proc.if_.return_value = mock_proc
        mock_proc.crop_image.return_value = mock_proc
        mock_proc.endif_.return_value = mock_proc
        mock_proc.resize_image.return_value = mock_proc
        mock_proc.to_gray_scale.return_value = mock_proc
        mock_proc.adjust_image.return_value = mock_proc
        mock_proc.autocontrast_image.return_value = mock_proc
        mock_proc.suppress_glare.return_value = mock_proc
        mock_proc.start_image_cutting.return_value = mock_proc
        mock_proc.cut_images.return_value = mock_proc
        mock_proc.stop_image_cutting.return_value = mock_proc
        mock_proc.save_cut_images.return_value = mock_proc
        mock_proc.get_cut_images.return_value = {}
        mock_proc.pictures = {"final": dummy_frame}
        mock_proc.get_pictures.return_value = {"final": dummy_frame}
        mock_proc_cls.return_value = mock_proc

        mock_dig = MagicMock()
        mock_dig.set_min_confidence_threshold.return_value = mock_dig
        mock_dig.init_analog_model.return_value = mock_dig
        mock_dig.init_digital_model.return_value = mock_dig
        mock_dig.use_previous_value_file.return_value = mock_dig
        mock_dig.process.return_value = dummy_result
        mock_dig_cls.return_value = mock_dig

        res = get_meter_data(url="", saveimages=True, app_instance=app)
        assert res == dummy_result

        # Check storage recorded
        mock_storage.record_meter_result.assert_called_once()
        # Check MQTT published
        mock_mqtt.publish_meter_result.assert_called_once_with(dummy_result)
        # Check zero-flow tracker evaluated
        mock_tracker.evaluate_reading.assert_called_once()
        # Check zero-flow status published to MQTT
        mock_mqtt.publish_zero_flow_status.assert_called_once()


def test_get_meter_data_no_url():
    from api.routes_meter import get_meter_data

    cfg = Config()
    cfg.image_source.url = ""
    app.state.config = cfg

    import pytest

    with pytest.raises(ValueError, match="No camera or image URL configured"):
        get_meter_data(url="", app_instance=app)
