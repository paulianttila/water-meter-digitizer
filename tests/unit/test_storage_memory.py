from datetime import datetime, timezone, timedelta
from configuration import Config
from processor.digitizer import MeterResult, MeterValue
from storage.base import MeterReading
from storage.memory import MemoryStorageBackend
from storage import get_storage_backend


def test_memory_storage_basic_record_and_get():
    storage = MemoryStorageBackend(max_memory_mb=10.0, max_records=100)
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    storage.record_reading(
        timestamp=now,
        meters={
            "total": MeterReading(value=300.5, raw_value="300.5", unit="m3"),
            "instant": MeterReading(value=0.2, raw_value="0.2", unit="m3/h"),
        },
        digital_results={"digit1": "3"},
        analog_results={"analog1": "5"},
    )

    readings = storage.get_readings()
    assert len(readings) == 1
    assert readings[0].meters["total"].value == 300.5
    assert readings[0].digital_results == {"digit1": "3"}

    summary = storage.get_summary()
    assert summary.backend == "memory"
    assert summary.total_records == 1
    assert "total" in summary.meters_tracked
    assert "instant" in summary.meters_tracked


def test_memory_storage_record_meter_result():
    storage = MemoryStorageBackend(max_memory_mb=10.0, max_records=100)
    now = datetime(2026, 9, 6, 14, 30, 0, tzinfo=timezone.utc)

    res = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="0300.850",
                unit="m3",
                quality="good",
                confidence=95.0,
            ),
            MeterValue(
                name="bad",
                value="NN.NNN",
                unit="m3",
                quality="uncertain",
                confidence=10.0,
            ),
        ],
        digital_results={"digit1": "3"},
        analog_results={"analog1": "8"},
    )

    storage.record_meter_result(res, timestamp=now)
    readings = storage.get_readings(meter_name="total")
    assert len(readings) == 1
    assert readings[0].meters["total"].value == 300.85
    assert readings[0].meters["bad"].value is None
    assert readings[0].meters["bad"].raw_value == "NN.NNN"


def test_memory_storage_limits_and_pruning():
    # Set small record limit = 5
    storage = MemoryStorageBackend(max_memory_mb=1.0, max_records=5)
    base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(10):
        ts = base_time + timedelta(hours=i)
        storage.record_reading(
            timestamp=ts,
            meters={"total": MeterReading(value=100.0 + i, raw_value=str(100.0 + i))},
        )

    readings = storage.get_readings()
    assert len(readings) == 5
    # Oldest 5 pruned, remaining are i=5..9
    assert readings[0].meters["total"].value == 105.0
    assert readings[-1].meters["total"].value == 109.0


def test_memory_storage_daily_consumption():
    storage = MemoryStorageBackend()

    # Day 1: 3 readings (consumption = 300.5 - 300.0 = 0.5)
    t1 = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 1, 20, 0, tzinfo=timezone.utc)
    storage.record_reading(t1, {"total": MeterReading(value=300.0, unit="m3")})
    storage.record_reading(t2, {"total": MeterReading(value=300.2, unit="m3")})
    storage.record_reading(t3, {"total": MeterReading(value=300.5, unit="m3")})

    # Day 2: 2 readings (consumption = 301.2 - 300.5 = 0.7)
    t4 = datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)
    t5 = datetime(2026, 9, 2, 19, 0, tzinfo=timezone.utc)
    storage.record_reading(t4, {"total": MeterReading(value=300.9, unit="m3")})
    storage.record_reading(t5, {"total": MeterReading(value=301.2, unit="m3")})

    daily = storage.get_consumption(meter_name="total", interval="daily")
    assert len(daily) == 2
    assert daily[0].bucket == "2026-09-01"
    assert round(daily[0].consumption, 2) == 0.50
    assert daily[0].reading_count == 3

    assert daily[1].bucket == "2026-09-02"
    assert round(daily[1].consumption, 2) == 0.70
    assert daily[1].reading_count == 2


def test_memory_storage_hourly_and_weekly_consumption():
    storage = MemoryStorageBackend()
    # 2 readings in same hour
    t1 = datetime(2026, 9, 1, 10, 5, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 10, 35, tzinfo=timezone.utc)
    storage.record_reading(t1, {"total": MeterReading(value=10.0, unit="m3")})
    storage.record_reading(t2, {"total": MeterReading(value=10.4, unit="m3")})

    hourly = storage.get_consumption(meter_name="total", interval="hourly")
    assert len(hourly) == 1
    assert hourly[0].bucket == "2026-09-01 10:00"
    assert round(hourly[0].consumption, 2) == 0.40

    weekly = storage.get_consumption(meter_name="total", interval="weekly")
    assert len(weekly) == 1
    assert "W" in weekly[0].bucket
    assert round(weekly[0].consumption, 2) == 0.40


def test_memory_storage_clear():
    storage = MemoryStorageBackend()
    storage.record_reading(
        datetime.now(timezone.utc),
        {"total": MeterReading(value=1.0)},
    )
    assert len(storage.get_readings()) == 1
    storage.clear()
    assert len(storage.get_readings()) == 0
    assert storage.get_summary().total_records == 0


def test_config_history_section_load_and_save():
    ini_data = """[DEFAULT]
LogLevel = DEBUG

[History]
Enabled = True
Backend = memory
MaxMemoryMB = 35.5
MaxRecords = 25000
RetentionDays = 60
"""
    cfg = Config().load_from_string(ini_data)
    assert cfg.history.enabled is True
    assert cfg.history.backend == "memory"
    assert cfg.history.max_memory_mb == 35.5
    assert cfg.history.max_records == 25000
    assert cfg.history.retention_days == 60

    storage = get_storage_backend(cfg)
    assert isinstance(storage, MemoryStorageBackend)
    assert storage.max_memory_mb == 35.5
    assert storage.max_records == 25000

    saved_ini = cfg.save_to_string()
    assert "[History]" in saved_ini
    assert "MaxMemoryMB=35.5" in saved_ini or "maxmemorymb=35.5" in saved_ini.lower()


def test_history_api_endpoints():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    # Seed reading
    app.state.storage.clear()
    now = datetime.now(timezone.utc)
    app.state.storage.record_reading(
        now,
        {"total": MeterReading(value=500.0, unit="m3")},
    )
    app.state.storage.record_reading(
        now + timedelta(hours=2),
        {"total": MeterReading(value=500.8, unit="m3")},
    )

    # 1. Stats
    resp_stats = client.get("/history/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_records"] == 2
    assert "total" in stats["meters_tracked"]

    # 2. Readings
    resp_readings = client.get("/history/readings?limit=10")
    assert resp_readings.status_code == 200
    readings = resp_readings.json()
    assert len(readings) == 2
    assert readings[0]["meters"]["total"]["value"] == 500.0

    # 3. Consumption
    resp_cons = client.get("/history/consumption?meter=total&interval=hourly&days=1")
    assert resp_cons.status_code == 200
    cons = resp_cons.json()
    assert len(cons) >= 1
    assert cons[-1]["consumption"] == 0.8
    assert "cumulative_consumption" in cons[-1]

    # 4. Cumulative Consumption mode
    resp_cum = client.get(
        "/history/consumption?meter=total&interval=hourly&days=1&cumulative=true"
    )
    assert resp_cum.status_code == 200
    cum_data = resp_cum.json()
    assert len(cum_data) >= 1
    assert cum_data[-1]["consumption"] == 0.8
    assert cum_data[-1]["cumulative_consumption"] == 0.8

    # 5. Clear endpoint
    resp_clear = client.post("/history/clear")
    assert resp_clear.status_code == 200
    assert app.state.storage.get_summary().total_records == 0

    # 6. Seed endpoint
    resp_seed = client.post("/history/seed?days=7&meter=total")
    assert resp_seed.status_code == 200
    seed_result = resp_seed.json()
    assert seed_result["seeded"] > 0
    assert app.state.storage.get_summary().total_records == seed_result["seeded"]
