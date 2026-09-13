"""End-to-End integration test: Background poller simulation, timeseries history, and snapshot timeline tracking."""

import time

import pytest
import requests


def test_e2e_mock_camera_poller_and_timeseries_accumulation():
    base_url = "http://localhost:3000"

    try:
        resp_health = requests.get(f"{base_url}/health", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.skip("Test application server is not running on http://localhost:3000")

    assert resp_health.status_code == 200

    # 1. Reset mock camera ticker and clear historical data
    requests.post(f"{base_url}/api/mock_camera/reset?start_value=120.0", timeout=5)
    requests.post(f"{base_url}/history/clear", timeout=5)

    # 2. Simulate 4 successive poller readouts
    for _ in range(4):
        resp_r = requests.get(
            f"{base_url}/meter?format=json&saveimages=true",
            timeout=10,
        )
        assert resp_r.status_code == 200
        data = resp_r.json()
        assert len(data["meters"]) > 0
        time.sleep(0.1)

    # 3. Verify history storage stats reflect the new records
    resp_stats = requests.get(f"{base_url}/history/stats", timeout=5)
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_records"] >= 4

    # 4. Verify chronologically indexed historical readings
    resp_readings = requests.get(f"{base_url}/history/readings?limit=10", timeout=5)
    assert resp_readings.status_code == 200
    readings = resp_readings.json()
    assert len(readings) >= 4
    assert "timestamp" in readings[0]
    assert "meters" in readings[0]

    # 5. Verify consumption aggregation intervals
    resp_hourly = requests.get(
        f"{base_url}/history/consumption?interval=hourly", timeout=5
    )
    assert resp_hourly.status_code == 200
    hourly_data = resp_hourly.json()
    assert isinstance(hourly_data, list)
    if hourly_data:
        assert "bucket" in hourly_data[0]
        assert "consumption" in hourly_data[0]

    # 6. Verify timeline snapshots endpoint
    resp_timeline = requests.get(f"{base_url}/history/timeline?limit=10", timeout=5)
    assert resp_timeline.status_code == 200
    timeline = resp_timeline.json()
    assert len(timeline) >= 4
