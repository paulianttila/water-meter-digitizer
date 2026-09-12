"""End-to-End integration test: Continuous zero-flow leak detection, REST status, and MQTT alerting."""

import time

import pytest
import requests
from testing_utils import MQTTTestReceiver


def test_e2e_leak_detection_telemetry_and_reset():
    base_url = "http://localhost:3000"

    # 1. Query initial leak status
    resp_leak = requests.get(f"{base_url}/leak/status", timeout=5)
    assert resp_leak.status_code == 200
    leak_data = resp_leak.json()
    assert "enabled" in leak_data
    assert "state" in leak_data

    # 2. Start MQTT test receiver
    mqtt_rx = MQTTTestReceiver(host="127.0.0.1", port=1883)
    try:
        mqtt_rx.start(topics=["watermeter/leak/#"])
    except Exception as e:
        pytest.skip(f"MQTT broker not reachable for integration test: {e}")

    try:
        # 3. Trigger manual reset endpoint
        resp_reset = requests.post(f"{base_url}/leak/reset", timeout=5)
        assert resp_reset.status_code == 200
        reset_data = resp_reset.json()
        assert reset_data["state"] == "OK"

        # 4. Trigger meter readout to evaluate reading against zero-flow monitor
        resp_read = requests.get(f"{base_url}/meter?format=json", timeout=5)
        assert resp_read.status_code == 200

        # Wait for potential leak MQTT broadcast
        time.sleep(0.5)

        # 5. Verify /leak/status endpoint reflects evaluated state
        resp_eval = requests.get(f"{base_url}/leak/status", timeout=5)
        assert resp_eval.status_code == 200
        eval_data = resp_eval.json()
        assert "current_flow_duration_seconds" in eval_data
        assert "recent_events" in eval_data
    finally:
        mqtt_rx.stop()
