import base64
import io
import re

import PIL.Image
import requests


def verify_image(data: bytes, width: int, height: int, format: str = "JPEG") -> bool:
    try:
        image = PIL.Image.open(io.BytesIO(data))
        image.verify()
        return False if image.size != (width, height) else image.format == format
    except Exception:
        return False


def find_between(s, start, end):
    return s.split(start)[1].split(end)[0]


def check_roi_image(response: requests.Response):
    assert len(response.text) > 50000
    assert response.text.startswith("<!DOCTYPE html>")

    match = re.search(r'data:image/jpeg;base64,\s*([^" >]+)', response.text)
    assert match is not None
    base64image = match[1]
    decodedImage = base64.b64decode(base64image)
    assert verify_image(decodedImage, 800, 600) or verify_image(
        decodedImage, 640, 480
    ), "JPEG"


def check_image(response: requests.Response):
    image = PIL.Image.open(io.BytesIO(response.content))
    image.verify()
    assert image.format == "JPEG"


def check_health_response(response: requests.Response):
    data = response.json()
    assert "status" in data
    assert "uptime" in data
    assert "camera" in data
    assert "memory" in data
    assert "cache" in data
    assert "models" in data
    assert "system" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert isinstance(data["uptime"]["uptime_seconds"], (int, float))
    assert isinstance(data["memory"]["rss_mb"], (int, float))
    assert isinstance(data["cache"]["hits"], int)
    assert isinstance(data["models"]["digital"]["enabled"], bool)


def check_mqtt_status_response(response: requests.Response):
    data = response.json()
    assert "enabled" in data
    assert "connected" in data
    assert "broker" in data
    assert "topic_prefix" in data
    assert "homeassistant_discovery" in data
    assert isinstance(data["enabled"], bool)
    assert isinstance(data["connected"], bool)
    assert isinstance(data["broker"], str)


def check_poller_status_response(response: requests.Response):
    data = response.json()
    assert "enabled" in data
    assert "running" in data
    assert "interval_seconds" in data
    assert "total_runs" in data
    assert isinstance(data["enabled"], bool)
    assert isinstance(data["running"], bool)
    assert isinstance(data["interval_seconds"], int)
    assert isinstance(data["total_runs"], int)


def check_mqtt_meter_data(response: requests.Response):
    data = response.json()
    assert data["enabled"] is True
    assert "last_published_topics" in data
    topics = data["last_published_topics"]

    assert topics.get("watermeter/digital/value") == "00452"
    assert topics.get("watermeter/analog/value") == "91241"
    assert topics.get("watermeter/total/value") == "00452.91241"
    assert topics.get("watermeter/total/confidence") == "96.2"
    assert "watermeter/readout/json" in topics

    readout = data.get("last_published_readout")
    assert readout is not None
    assert readout["error"] == ""
    assert readout["digital_results"]["digit1"] == "0.0"
    assert readout["digital_results"]["digit5"] == "2.6"
    assert readout["analog_results"]["analog1"] == "0.00"
    assert readout["analog_results"]["analog4"] == "4.10"
    total_meter = next((m for m in readout["meters"] if m["name"] == "total"), None)
    assert total_meter is not None
    assert total_meter["value"] == "00452.91241"
    assert total_meter["confidence"] == 96.2
    assert readout["confidence_scores"]["digit1"] == 85.2
    assert readout["confidence_scores"]["analog1"] == 99.2
