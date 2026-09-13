import time
from datetime import datetime, timedelta

import pytest
import requests
from testing_utils import MQTTTestReceiver

from configuration import ZeroFlowMonitor
from leak import ValueType
from leak.tracker import LeakState, ZeroFlowTracker


def test_e2e_mock_camera_leak_detection_flow_and_reset():
    base_url = "http://localhost:3000"

    try:
        resp_health = requests.get(f"{base_url}/health", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.skip("Test application server is not running on http://localhost:3000")

    assert resp_health.status_code == 200

    # 1. Query initial leak status
    resp_leak = requests.get(f"{base_url}/leak/status", timeout=5)
    assert resp_leak.status_code == 200
    leak_data = resp_leak.json()
    assert "enabled" in leak_data
    assert "state" in leak_data

    # 2. Start MQTT receiver
    mqtt_rx = MQTTTestReceiver(host="127.0.0.1", port=1883)
    try:
        mqtt_rx.start(topics=["watermeter/leak/#", "watermeter/#"])
    except Exception as e:
        pytest.skip(f"MQTT broker not reachable for integration test: {e}")

    try:
        # 3. Trigger manual reset endpoint
        resp_reset = requests.post(f"{base_url}/leak/reset", timeout=5)
        assert resp_reset.status_code == 200
        reset_data = resp_reset.json()
        assert reset_data["state"] == "OK"

        # 4. Trigger successive meter readouts feeding zero-flow monitor
        for _ in range(3):
            resp_read = requests.get(f"{base_url}/meter?format=json", timeout=5)
            assert resp_read.status_code == 200
            time.sleep(0.1)

        # 5. Verify /leak/status endpoint reflects evaluated state
        resp_eval = requests.get(f"{base_url}/leak/status", timeout=5)
        assert resp_eval.status_code == 200
        eval_data = resp_eval.json()
        assert "current_flow_duration_seconds" in eval_data
        assert "recent_events" in eval_data
        assert "state" in eval_data
    finally:
        mqtt_rx.stop()


def test_e2e_zero_flow_tracker_continuous_flow_simulation():
    """Simulate continuous water flow vs stoppage using simulated meter readings."""
    cfg = ZeroFlowMonitor(
        enabled=True,
        meter_name="total",
        continuous_flow_hours=0.001,  # Short duration for test (3.6s)
        min_leak_volume=0.010,
        flow_threshold=0.001,
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(cfg)

    # 1. Baseline reading
    now = datetime.now()
    st1 = tracker.evaluate_reading(timestamp=now, meter_value=100.000)
    assert st1.state == LeakState.OK

    # 2. Advancing consumption (flow active)
    st2 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=1), meter_value=100.050
    )
    assert st2.current_flow_rate > 0

    # 3. Flow ceases (constant value for resolve debounce count)
    tracker.evaluate_reading(timestamp=now + timedelta(seconds=2), meter_value=100.050)
    st3 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=3), meter_value=100.050
    )
    assert st3.state == LeakState.OK


def test_e2e_zero_flow_tracker_flow_rate_simulation():
    """Simulate direct flow rate readings vs zero flow using simulated meter readings."""
    cfg = ZeroFlowMonitor(
        enabled=True,
        meter_name="flow",
        value_type=ValueType.FLOW_RATE,
        continuous_flow_hours=0.001,  # 3.6s
        min_leak_volume=0.0001,
        flow_threshold=0.001,
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(cfg)

    now = datetime.now()
    # 1. Zero flow baseline
    st1 = tracker.evaluate_reading(timestamp=now, meter_value=0.000)
    assert st1.state == LeakState.OK
    assert st1.value_type == ValueType.FLOW_RATE

    # 2. Flow rate active (e.g. 0.500 m3/h)
    st2 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=2), meter_value=0.500
    )
    assert st2.current_flow_rate == 0.500
    assert st2.current_flow_volume > 0

    # 3. Exceed duration -> leak state
    st3 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=5), meter_value=0.500
    )
    assert st3.state == LeakState.LEAK_DETECTED
    assert st3.active_event is not None

    # 4. Zero flow -> resolves after debounce count
    st4 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=6), meter_value=0.000
    )
    assert st4.state == LeakState.LEAK_DETECTED
    st5 = tracker.evaluate_reading(
        timestamp=now + timedelta(seconds=7), meter_value=0.000
    )
    assert st5.state == LeakState.OK
    assert len(tracker.get_status().recent_events) == 1
