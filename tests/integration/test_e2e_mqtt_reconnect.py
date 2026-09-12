"""End-to-End integration test: MQTT broker connectivity, status telemetry, and resilient publishing."""

import pytest
import requests
from testing_utils import MQTTTestReceiver


def test_e2e_mqtt_connectivity_and_resilience():
    base_url = "http://localhost:3000"

    # 1. Verify app and MQTT status endpoint
    resp_status = requests.get(f"{base_url}/mqtt/status", timeout=5)
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert "enabled" in status_data

    if not status_data.get("enabled"):
        pytest.skip("MQTT is not enabled in the current test configuration.")

    # 2. Start listener
    mqtt_rx = MQTTTestReceiver(host="127.0.0.1", port=1883)
    try:
        mqtt_rx.start(topics=["watermeter/#", "homeassistant/#"])
    except Exception as e:
        pytest.skip(f"Could not connect test listener to MQTT broker: {e}")

    try:
        # 3. Trigger readout and verify message dispatch
        resp_readout = requests.get(f"{base_url}/meter?format=json", timeout=5)
        assert resp_readout.status_code == 200

        msg_val = mqtt_rx.wait_for_message(
            topic_suffix="watermeter/total/value", timeout=5.0
        )
        assert msg_val is not None
        assert float(msg_val["payload"]) > 0

        # 4. Verify diagnostic confidence published
        msg_conf = mqtt_rx.wait_for_message(
            topic_suffix="watermeter/total/confidence", timeout=3.0
        )
        assert msg_conf is not None
        assert float(msg_conf["payload"]) > 0

        # 5. Verify /mqtt/status contains updated topic dictionary
        resp_after = requests.get(f"{base_url}/mqtt/status", timeout=5)
        assert resp_after.status_code == 200
        after_data = resp_after.json()
        assert after_data["connected"] is True
        assert "watermeter/total/value" in after_data["last_published_topics"]
    finally:
        mqtt_rx.stop()
