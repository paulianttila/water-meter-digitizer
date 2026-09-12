"""Unit tests for historical meter reading, consumption, frame diff, and snapshot endpoints."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app
from storage.base import ConsumptionRecord, MeterReading, ReadingRecord, StorageSummary
from utils.visual_diff import compress_image_to_bytes


@pytest.fixture(autouse=True)
def restore_app_state():
    orig_storage = getattr(app.state, "storage", None)
    yield
    app.state.storage = orig_storage


def test_history_consumption_endpoints():
    client = TestClient(app)

    # 1. Without storage
    app.state.storage = None
    resp_none = client.get("/history/consumption")
    assert resp_none.status_code == 200
    assert resp_none.json() == []

    # 2. With mock storage
    mock_storage = MagicMock()
    app.state.storage = mock_storage

    now = datetime.now().astimezone()
    mock_records = [
        ConsumptionRecord(
            bucket="2026-09-10",
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=1),
            meter_name="total",
            unit="m3",
            consumption=0.5,
            start_value=100.0,
            end_value=100.5,
            min_value=100.0,
            max_value=100.5,
            reading_count=5,
        ),
        ConsumptionRecord(
            bucket="2026-09-11",
            start_time=now - timedelta(days=1),
            end_time=now,
            meter_name="total",
            unit="m3",
            consumption=0.8,
            start_value=100.5,
            end_value=101.3,
            min_value=100.5,
            max_value=101.3,
            reading_count=4,
        ),
    ]
    mock_storage.get_consumption.return_value = mock_records

    # Daily interval, non-cumulative
    resp = client.get("/history/consumption?meter=total&interval=daily&days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["consumption"] == 0.5
    assert data[1]["consumption"] == 0.8
    assert data[1]["cumulative_consumption"] == 1.3

    # Cumulative mode
    resp_cum = client.get(
        "/history/consumption?meter=total&interval=invalid_interval&cumulative=true&days=0"
    )
    assert resp_cum.status_code == 200
    data_cum = resp_cum.json()
    assert data_cum[0]["consumption"] == 0.5
    assert data_cum[1]["consumption"] == 1.3


def test_history_readings_endpoint():
    client = TestClient(app)

    # Without storage
    app.state.storage = None
    assert client.get("/history/readings").json() == []

    # With storage
    mock_storage = MagicMock()
    app.state.storage = mock_storage

    now = datetime.now().astimezone()
    mock_storage.get_readings.return_value = [
        ReadingRecord(
            id=1,
            timestamp=now,
            meters={"total": MeterReading(value=100.0, unit="m3")},
            digital_results={"0": "1"},
            analog_results={},
            error="",
            frame_type="full",
            flow_detected=True,
            confidence_scores={"0": 98.0},
        )
    ]

    resp = client.get("/history/readings?meter=total&limit=50")
    assert resp.status_code == 200
    readings = resp.json()
    assert len(readings) == 1
    assert readings[0]["id"] == 1
    assert readings[0]["has_frame"] is True
    assert readings[0]["meters"]["total"]["value"] == 100.0


def test_history_timeline_endpoint():
    client = TestClient(app)

    # Without storage
    app.state.storage = None
    assert client.get("/history/timeline").json() == []

    # With storage
    mock_storage = MagicMock()
    app.state.storage = mock_storage

    now = datetime.now().astimezone()
    mock_storage.get_timeline.return_value = [
        ReadingRecord(
            id=10,
            timestamp=now,
            meters={"total": MeterReading(value=200.0, unit="m3")},
            digital_results={},
            analog_results={},
            error="low_confidence",
            frame_type="composite",
            flow_detected=False,
            confidence_scores={},
        )
    ]

    resp = client.get(
        "/history/timeline?limit=10&offset=0&anomalies_only=true&frames_only=true"
    )
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) == 1
    assert timeline[0]["id"] == 10
    mock_storage.get_timeline.assert_called_once_with(
        limit=10,
        offset=0,
        anomalies_only=True,
        frames_only=True,
    )


def test_history_frame_download():
    client = TestClient(app)

    # 1. Storage is None -> 404
    app.state.storage = None
    resp_no_store = client.get("/history/frame/1")
    assert resp_no_store.status_code == 404

    # 2. Frame not found in storage -> 404
    mock_storage = MagicMock()
    app.state.storage = mock_storage
    mock_storage.get_frame_bytes.return_value = (None, None)

    resp_no_frame = client.get("/history/frame/999")
    assert resp_no_frame.status_code == 404

    # 3. Frame found -> 200 with bytes
    test_img = np.zeros((30, 30, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 80)
    mock_storage.get_frame_bytes.return_value = (frame_bytes, "image/webp")

    resp_ok = client.get("/history/frame/1")
    assert resp_ok.status_code == 200
    assert resp_ok.headers["content-type"] == "image/webp"
    assert resp_ok.content == frame_bytes


def test_history_frame_diff_and_diff_image():
    client = TestClient(app)

    test_img1 = np.zeros((40, 40, 3), dtype=np.uint8)
    test_img2 = np.ones((40, 40, 3), dtype=np.uint8) * 128

    bytes1 = compress_image_to_bytes(test_img1, "jpeg", 80)
    bytes2 = compress_image_to_bytes(test_img2, "jpeg", 80)

    # 1. Diff endpoints when storage is None -> 404
    app.state.storage = None
    assert client.get("/history/frame/1/diff").status_code == 404
    assert client.get("/history/frame/1/diff_image").status_code == 404

    # 2. Frame not found -> 404
    mock_storage = MagicMock()
    app.state.storage = mock_storage
    mock_storage.get_frame_bytes.return_value = (None, None)
    assert client.get("/history/frame/1/diff").status_code == 404
    assert client.get("/history/frame/1/diff_image").status_code == 404

    # 3. Success with compare_id
    def get_frame_side_effect(reading_id):
        if reading_id == 1:
            return (bytes1, "image/jpeg")
        if reading_id == 2:
            return (bytes2, "image/jpeg")
        return (None, None)

    mock_storage.get_frame_bytes.side_effect = get_frame_side_effect

    resp_diff = client.get("/history/frame/1/diff?compare_id=2")
    assert resp_diff.status_code == 200
    diff_data = resp_diff.json()
    assert diff_data["reading_id"] == 1
    assert diff_data["compare_id"] == 2
    assert "ssim_similarity" in diff_data
    assert "is_anomaly" in diff_data

    # Heatmap image
    resp_diff_img = client.get("/history/frame/1/diff_image?compare_id=2")
    assert resp_diff_img.status_code == 200
    assert resp_diff_img.headers["content-type"] == "image/jpeg"
    assert len(resp_diff_img.content) > 0


def test_history_stats_prune_seed_clear():
    client = TestClient(app)

    # 1. Stats
    app.state.storage = None
    assert client.get("/history/stats").json() == {}

    mock_storage = MagicMock()
    app.state.storage = mock_storage

    now = datetime.now().astimezone()
    mock_storage.get_summary.return_value = StorageSummary(
        backend="sqlite",
        total_records=50,
        memory_usage_bytes=1024,
        max_memory_bytes=10485760,
        oldest_timestamp=now - timedelta(days=7),
        newest_timestamp=now,
        meters_tracked=["total", "flow"],
        total_snapshots=12,
        snapshot_disk_bytes=204800,
        snapshot_mode="full_frames",
    )

    resp_stats = client.get("/history/stats")
    assert resp_stats.status_code == 200
    s_data = resp_stats.json()
    assert s_data["total_records"] == 50
    assert s_data["total_snapshots"] == 12
    assert s_data["backend"] == "sqlite"

    # 2. Prune
    mock_storage.prune_snapshots.return_value = 5
    resp_prune = client.post(
        "/history/snapshots/prune?retention_days=30&max_disk_mb=50"
    )
    assert resp_prune.status_code == 200
    assert resp_prune.json()["deleted_count"] == 5

    # 3. Seed
    with patch("api.routes_history.seed_demo_history", return_value=14):
        resp_seed = client.post("/history/seed?days=14&meter=total&base_val=300.0")
        assert resp_seed.status_code == 200
        assert resp_seed.json()["seeded"] == 14

    # 4. Clear
    resp_clear = client.post("/history/clear")
    assert resp_clear.status_code == 200
    assert "cleared" in resp_clear.json()["message"].lower()
    mock_storage.clear.assert_called_once()
