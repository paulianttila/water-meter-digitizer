"""End-to-End integration test: Multi-frame time-series consumption and timeline tracking."""

import time

import pytest
import requests
from testing_utils import MQTTTestReceiver


def test_e2e_time_series_progression():
    base_url = "http://localhost:3000"

    # Verify server is responding
    resp_health = requests.get(f"{base_url}/health", timeout=5)
    assert resp_health.status_code == 200

    # Start MQTT receiver to listen for real-time published telemetry
    mqtt_rx = MQTTTestReceiver(host="127.0.0.1", port=1883)
    try:
        mqtt_rx.start(topics=["watermeter/#"])
    except Exception as e:
        pytest.skip(f"MQTT broker not reachable for integration test: {e}")

    try:
        # 1. Clear existing history for a clean test baseline
        requests.post(f"{base_url}/history/clear", timeout=5)

        # 2. Trigger 3 successive meter readouts synchronously
        for _i in range(3):
            resp_r = requests.get(
                f"{base_url}/meter?format=json&saveimages=true", timeout=10
            )
            assert resp_r.status_code == 200
            data = resp_r.json()
            assert len(data["meters"]) > 0
            time.sleep(0.2)

        # 3. Verify history storage has accumulated records
        resp_stats = requests.get(f"{base_url}/history/stats", timeout=5)
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert stats["total_records"] >= 3

        # 4. Verify readings endpoint returns chronologically indexed records
        resp_readings = requests.get(f"{base_url}/history/readings?limit=10", timeout=5)
        assert resp_readings.status_code == 200
        readings = resp_readings.json()
        assert len(readings) >= 3

        # Verify attributes exist on records
        assert "meters" in readings[0]
        assert "timestamp" in readings[0]

        # 5. Verify timeline endpoint contains snapshots
        resp_timeline = requests.get(f"{base_url}/history/timeline?limit=10", timeout=5)
        assert resp_timeline.status_code == 200
        timeline = resp_timeline.json()
        assert len(timeline) >= 3

        # 6. Verify MQTT receiver captured live messages
        msg_val = mqtt_rx.wait_for_message(topic_suffix="/value", timeout=3.0)
        assert msg_val is not None
        assert "watermeter" in msg_val["topic"]
    finally:
        mqtt_rx.stop()
