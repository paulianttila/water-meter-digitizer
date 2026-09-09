import threading
from datetime import UTC, datetime, timedelta
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

    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
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
    now = datetime.now(UTC)

    # Record 1: 10 days ago (should be pruned)
    storage.record_reading(
        timestamp=now - timedelta(days=10),
        meters={"main": MeterReading(value=100.0)},
    )
    # Record 2: 5 days ago (should remain)
    storage.record_reading(
        timestamp=now - timedelta(days=5),
        meters={"main": MeterReading(value=105.0)},
    )
    # Record 3: 1 day ago (should remain)
    storage.record_reading(
        timestamp=now - timedelta(days=1),
        meters={"main": MeterReading(value=110.0)},
    )

    storage.prune()
    readings = storage.get_readings()
    assert len(readings) == 2
    assert readings[0].meters["main"].value == 105.0
    assert readings[1].meters["main"].value == 110.0


def test_sqlite_max_records_fifo_pruning():
    storage = SQLAlchemyStorageBackend(
        db_url="sqlite:///:memory:",
        max_records=5,
        retention_days=0,
        prune_interval=1,
    )
    base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)

    for i in range(12):
        storage.record_reading(
            timestamp=base_time + timedelta(hours=i),
            meters={"main": MeterReading(value=float(i))},
        )

    readings = storage.get_readings()
    assert len(readings) == 5
    # The oldest 7 were pruned, remaining values: 7, 8, 9, 10, 11
    assert readings[0].meters["main"].value == 7.0
    assert readings[-1].meters["main"].value == 11.0


def test_sqlite_filtering_options():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")
    base = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)

    for i in range(10):
        storage.record_reading(
            timestamp=base + timedelta(hours=i),
            meters={
                "meterA": MeterReading(value=float(i)),
                "meterB": MeterReading(value=float(i * 2)),
            },
        )

    # Filter by start & end
    filtered = storage.get_readings(
        start=base + timedelta(hours=2),
        end=base + timedelta(hours=5),
    )
    assert len(filtered) == 4
    assert filtered[0].timestamp == base + timedelta(hours=2)
    assert filtered[-1].timestamp == base + timedelta(hours=5)

    # Filter with limit
    limited = storage.get_readings(limit=3)
    assert len(limited) == 3
    # Returns the 3 newest in chronological order
    assert limited[-1].timestamp == base + timedelta(hours=9)
    assert limited[0].timestamp == base + timedelta(hours=7)


def test_sqlite_consumption_intervals():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:")

    # Hourly test
    t1 = datetime(2026, 9, 1, 10, 5, tzinfo=UTC)
    t2 = datetime(2026, 9, 1, 10, 45, tzinfo=UTC)
    t3 = datetime(2026, 9, 1, 11, 10, tzinfo=UTC)
    t4 = datetime(2026, 9, 1, 11, 50, tzinfo=UTC)

    storage.record_reading(t1, {"main": MeterReading(value=100.0)})
    storage.record_reading(t2, {"main": MeterReading(value=100.5)})
    storage.record_reading(t3, {"main": MeterReading(value=101.2)})
    storage.record_reading(t4, {"main": MeterReading(value=102.0)})

    hourly = storage.get_consumption("main", interval="hourly")
    assert len(hourly) == 2
    assert hourly[0].bucket == "2026-09-01 10:00"
    assert round(hourly[0].consumption, 2) == 0.50
    assert hourly[1].bucket == "2026-09-01 11:00"
    # Includes cross-bucket jump 100.5 -> 101.2 (0.7) + 101.2 -> 102.0 (0.8) = 1.50
    assert round(hourly[1].consumption, 2) == 1.50

    daily = storage.get_consumption("main", interval="daily")
    assert len(daily) == 1
    assert daily[0].bucket == "2026-09-01"
    assert round(daily[0].consumption, 2) == 2.00


def test_sqlite_concurrent_writes_and_reads():
    storage = SQLAlchemyStorageBackend(db_url="sqlite:///:memory:", max_records=200)
    base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)

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
