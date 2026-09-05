from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import requests

from main import app, VERSION
from utils.diagnostics import (
    format_uptime,
    get_process_memory_info,
    check_camera_reachability,
    get_models_info,
    get_system_info,
)


def test_format_uptime():
    assert format_uptime(45) == "45s"
    assert format_uptime(125) == "2m 5s"
    assert format_uptime(3665) == "1h 1m 5s"
    assert format_uptime(90061) == "1d 1h 1m 1s"
    assert format_uptime(-5) == "0s"


def test_get_process_memory_info():
    info = get_process_memory_info()
    assert "rss_mb" in info
    assert "peak_rss_mb" in info
    assert "platform" in info
    assert isinstance(info["rss_mb"], (int, float))
    assert isinstance(info["peak_rss_mb"], (int, float))
    assert info["rss_mb"] >= 0
    assert info["peak_rss_mb"] >= 0


def test_get_system_info():
    info = get_system_info(VERSION)
    assert info["version"] == VERSION
    assert "python_version" in info
    assert "platform" in info


def test_check_camera_reachability_empty():
    res = check_camera_reachability("")
    assert res["reachable"] is False
    assert res["error"] == "No camera URL configured"


def test_check_camera_reachability_file(tmp_path):
    existing_file = tmp_path / "test.jpg"
    existing_file.write_bytes(b"image data")

    res = check_camera_reachability(f"file://{existing_file}")
    assert res["reachable"] is True
    assert res["status_code"] == 200
    assert res["latency_ms"] is not None
    assert res["error"] is None

    res_missing = check_camera_reachability(f"file://{tmp_path}/missing.jpg")
    assert res_missing["reachable"] is False
    assert res_missing["status_code"] == 404
    assert "Local file not found" in res_missing["error"]


def test_check_camera_reachability_http_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("requests.head", return_value=mock_resp):
        res = check_camera_reachability("http://192.168.1.50/capture")
        assert res["reachable"] is True
        assert res["status_code"] == 200
        assert res["error"] is None
        assert isinstance(res["latency_ms"], float)


def test_check_camera_reachability_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("requests.head", return_value=mock_resp):
        res = check_camera_reachability("http://192.168.1.50/capture")
        assert res["reachable"] is False
        assert res["status_code"] == 500
        assert "HTTP error 500" in res["error"]


def test_check_camera_reachability_http_exception():
    with patch(
        "requests.head", side_effect=requests.RequestException("Connection refused")
    ):
        res = check_camera_reachability("http://192.168.1.50/capture")
        assert res["reachable"] is False
        assert res["status_code"] is None
        assert "Connection refused" in res["error"]


def test_get_models_info(tmp_path):
    model_file = tmp_path / "model.tflite"
    model_file.write_bytes(b"dummy model bytes 12345")

    res = get_models_info(
        digital_enabled=True,
        digital_modelfile=str(model_file),
        analog_enabled=False,
        analog_modelfile="/nonexistent/path.tflite",
    )

    assert res["digital"]["enabled"] is True
    assert res["digital"]["exists"] is True
    assert res["digital"]["size_bytes"] == len(b"dummy model bytes 12345")

    assert res["analog"]["enabled"] is False
    assert res["analog"]["exists"] is False
    assert res["analog"]["size_bytes"] is None


def test_get_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")

    assert "uptime" in data
    assert "uptime_seconds" in data["uptime"]
    assert "uptime_human" in data["uptime"]
    assert "started_at" in data["uptime"]

    assert "camera" in data
    assert "url" in data["camera"]
    assert "reachable" in data["camera"]

    assert "memory" in data
    assert "rss_mb" in data["memory"]
    assert "peak_rss_mb" in data["memory"]

    assert "cache" in data
    assert "hits" in data["cache"]
    assert "misses" in data["cache"]
    assert "hit_ratio_percent" in data["cache"]
    assert "current_size" in data["cache"]

    assert "models" in data
    assert "digital" in data["models"]
    assert "analog" in data["models"]

    assert "system" in data
    assert data["system"]["version"] == VERSION
