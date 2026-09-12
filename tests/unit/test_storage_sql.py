import threading
from datetime import datetime, timedelta
from pathlib import Path

from processor.digitizer import MeterResult, MeterValue
from storage.base import MeterReading
from storage.sql import SQLAlchemyStorageBackend


def test_sqlite_file_storage_basic(tmp_path: Path):
    db_path = tmp_path / "data" / "history.db"
    storage = SQLAlchemyStorageBackend(
        db_url=f"sqlite:///{db_path}",
        max_records=100,
        retention_days=30,
    )
    assert db_path.exists()

    local_tz = datetime.now().astimezone().tzinfo
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=local_tz)
    storage.record_reading(
        timestamp=now,
        meters={
            "main": MeterReading(value=123.456, raw_value="123.456", unit="m3"),
            "flow": MeterReading(value=1.5, raw_value="1.5", unit="l/min"),
        },
        digital_results={"d1": "1"},
        analog_results={"a1": "2"},
        error="",
    )

    readings = storage.get_readings()
    assert len(readings) == 1
    assert readings[0].meters["main"].value == 123.456
    assert readings[0].meters["flow"].value == 1.5
    assert readings[0].digital_results == {"d1": "1"}

    summary = storage.get_summary()
    assert summary.backend == "sqlite"
    assert summary.total_records == 1
    assert "main" in summary.meters_tracked
    assert "flow" in summary.meters_tracked
    assert summary.memory_usage_bytes > 0


def test_sqlite_time_retention_pruning():
    storage = SQLAlchemyStorageBackend(
        db_url="sqlite:///:memory:",
        retention_days=7,
        max_records=1000,
        prune_interval=1,
    )
    now = datetime.now().astimezone()

    # Record 1: 10 days ago (should be pruned)
    storage.record_reading(
        timestamp=now - timedelta(days=10),
        meters={"main": MeterReading(value=100.0)},
    )
    # Record 2: 5 days ago (should remain)
    storage.record_reading(
        timestamp=now - timedelta(days=5),
        meters={"main": MeterReading(value=101.0)},
    )
    # Record 3: Trigger pruning
    storage.record_reading(
        timestamp=now,
        meters={"main": MeterReading(value=102.0)},
    )

    readings = storage.get_readings()
    assert len(readings) == 2
    assert readings[0].meters["main"].value == 101.0
    assert readings[1].meters["main"].value == 102.0


def test_sqlite_max_records_fifo_pruning():
    storage = SQLAlchemyStorageBackend(
        db_url="sqlite:///:memory:",
        max_records=5,
        prune_interval=1,
    )
    now = datetime.now().astimezone()

    for i in range(10):
        storage.record_reading(
            timestamp=now + timedelta(minutes=i),
            meters={"main": MeterReading(value=float(i))},
        )

    readings = storage.get_readings()
    assert len(readings) == 5
    # The oldest (0..4) should be pruned, leaving (5..9)
    values = [r.meters["main"].value for r in readings]
    assert values == [5.0, 6.0, 7.0, 8.0, 9.0]


def test_sqlite_filtering_options():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")
    local_tz = datetime.now().astimezone().tzinfo
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=local_tz)
    t2 = datetime(2026, 9, 1, 11, 0, 0, tzinfo=local_tz)
    t3 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=local_tz)

    storage.record_reading(timestamp=t1, meters={"m1": MeterReading(value=1.0)})
    storage.record_reading(
        timestamp=t2, meters={"m1": MeterReading(value=2.0)}, error="OCR Failed"
    )
    storage.record_reading(timestamp=t3, meters={"m2": MeterReading(value=3.0)})

    # Filter by meter name
    m1_readings = storage.get_readings(meter_name="m1")
    assert len(m1_readings) == 2

    # Filter by time range
    time_filtered = storage.get_readings(
        start=t1 + timedelta(minutes=30), end=t3 - timedelta(minutes=30)
    )
    assert len(time_filtered) == 1
    assert time_filtered[0].meters["m1"].value == 2.0

    # Limit
    limited = storage.get_readings(limit=1)
    assert len(limited) == 1
    assert "m2" in limited[0].meters


def test_sqlite_consumption_intervals():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")
    local_tz = datetime.now().astimezone().tzinfo

    # Record readings across hours
    storage.record_reading(
        timestamp=datetime(2026, 9, 1, 10, 0, 0, tzinfo=local_tz),
        meters={"main": MeterReading(value=100.0)},
    )
    storage.record_reading(
        timestamp=datetime(2026, 9, 1, 10, 30, 0, tzinfo=local_tz),
        meters={"main": MeterReading(value=100.5)},
    )
    storage.record_reading(
        timestamp=datetime(2026, 9, 1, 11, 15, 0, tzinfo=local_tz),
        meters={"main": MeterReading(value=101.2)},
    )
    storage.record_reading(
        timestamp=datetime(2026, 9, 1, 11, 45, 0, tzinfo=local_tz),
        meters={"main": MeterReading(value=102.0)},
    )

    hourly = storage.get_consumption("main", interval="hourly")
    assert len(hourly) == 2
    assert hourly[0].bucket == "2026-09-01 10:00"
    assert round(hourly[0].consumption, 2) == 0.50
    assert hourly[1].bucket == "2026-09-01 11:00"
    assert round(hourly[1].consumption, 2) == 1.50

    daily = storage.get_consumption("main", interval="daily")
    assert len(daily) == 1
    assert daily[0].bucket == "2026-09-01"
    assert round(daily[0].consumption, 2) == 2.00


def test_sqlite_concurrent_writes_and_reads():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:", max_records=200)
    local_tz = datetime.now().astimezone().tzinfo
    base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=local_tz)

    def worker(worker_id: int):
        for i in range(20):
            ts = base_time + timedelta(seconds=worker_id * 100 + i)
            storage.record_reading(
                timestamp=ts,
                meters={"total": MeterReading(value=float(worker_id * 100 + i))},
            )
            # Concurrent read
            _ = storage.get_readings(limit=5)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summary = storage.get_summary()
    assert summary.total_records == 100


def test_sqlite_record_meter_result():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")
    res = MeterResult(
        meters=[
            MeterValue(
                name="main",
                value="543.21",
                unit="m3",
                quality="good",
                confidence=98.5,
            )
        ],
        digital_results={"digit_0": "5"},
        analog_results={},
        error="",
    )
    storage.record_meter_result(res)

    readings = storage.get_readings(meter_name="main")
    assert len(readings) == 1
    assert readings[0].meters["main"].value == 543.21
    assert readings[0].meters["main"].confidence == 98.5


def test_sqlite_timeline_queries_and_filters():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")
    now = datetime.now().astimezone()

    storage.record_reading(
        timestamp=now - timedelta(hours=2),
        meters={"total": MeterReading(value=10.0)},
        error="",
    )
    storage.record_reading(
        timestamp=now - timedelta(hours=1),
        meters={"total": MeterReading(value=11.0)},
        error="Anomaly error",
        frame_bytes=b"RIFFtestwebp",
        frame_type="full",
    )
    storage.record_reading(
        timestamp=now,
        meters={"total": MeterReading(value=12.0)},
        confidence_scores={"d1": 99.0},
    )

    # 1. Anomalies only
    anomalies = storage.get_timeline(anomalies_only=True)
    assert len(anomalies) == 1
    assert anomalies[0].error == "Anomaly error"

    # 2. Frames only
    frames = storage.get_timeline(frames_only=True)
    assert len(frames) == 1
    assert frames[0].frame_type == "full"

    # 3. Start & End filter
    time_bounded = storage.get_timeline(
        start=now - timedelta(minutes=30), end=now + timedelta(minutes=30)
    )
    assert len(time_bounded) == 1
    assert time_bounded[0].meters["total"].value == 12.0


def test_sqlite_memory_frame_and_mime_types(tmp_path: Path):
    storage = SQLAlchemyStorageBackend(
        db_url="sqlite:///:memory:",
        snapshots_dir=str(tmp_path / "snaps"),
    )
    now = datetime.now().astimezone()

    # WebP buffer
    rid1 = storage.record_reading(
        timestamp=now,
        meters={"total": MeterReading(value=1.0)},
        frame_bytes=b"RIFFsome_webp_data",
        frame_type="full",
    )
    assert rid1 is not None
    _data, mime = storage.get_frame_bytes(rid1)
    assert mime == "image/webp"

    # JPEG buffer
    rid2 = storage.record_reading(
        timestamp=now + timedelta(minutes=1),
        meters={"total": MeterReading(value=2.0)},
        frame_bytes=b"\xff\xd8\xffsome_jpeg_data",
        frame_type="full",
    )
    assert rid2 is not None
    _data, mime = storage.get_frame_bytes(rid2)
    assert mime == "image/jpeg"
