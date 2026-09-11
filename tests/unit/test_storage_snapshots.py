"""Unit tests for snapshot frame archival, time machine timeline, and pruning in storage backends."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from configuration import Config, Snapshots
from processor.digitizer import MeterResult, MeterValue
from storage.base import MeterReading
from storage.memory import MemoryStorageBackend
from storage.sql import SQLAlchemyStorageBackend
from utils.visual_diff import compress_image_to_bytes


@pytest.fixture
def temp_snapshots_dir(tmp_path):
    d = tmp_path / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def test_sql_storage_snapshots_record_and_get_frame(tmp_path, temp_snapshots_dir):
    db_path = tmp_path / "test_history.db"
    db_url = f"sqlite:///{db_path}"

    storage = SQLAlchemyStorageBackend(
        db_url=db_url,
        snapshots_dir=temp_snapshots_dir,
        snapshot_mode="full_frames",
    )

    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 80)

    reading_id = storage.record_reading(
        timestamp=datetime.now(UTC),
        meters={"total": MeterReading(value=100.5, raw_value="100.5", unit="m3")},
        frame_bytes=frame_bytes,
        frame_type="full",
        flow_detected=True,
    )

    assert reading_id is not None
    data, mime = storage.get_frame_bytes(reading_id)
    assert data is not None
    assert mime == "image/webp"

    # Timeline retrieval
    timeline = storage.get_timeline(limit=10)
    assert len(timeline) == 1
    assert timeline[0].id == reading_id
    assert timeline[0].frame_type == "full"
    assert timeline[0].flow_detected is True

    # Storage stats
    summary = storage.get_summary()
    assert summary.total_snapshots == 1
    assert summary.snapshot_disk_bytes > 0


def test_memory_storage_snapshots(tmp_path):
    storage = MemoryStorageBackend(snapshot_mode="smart_tiered")

    test_img = np.zeros((50, 50, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 75)

    reading_id = storage.record_reading(
        timestamp=datetime.now(UTC),
        meters={"total": MeterReading(value=50.0, raw_value="50.0", unit="m3")},
        frame_bytes=frame_bytes,
        frame_type="full",
    )

    assert reading_id is not None
    data, mime = storage.get_frame_bytes(reading_id)
    assert data == frame_bytes
    assert mime == "image/webp"

    timeline = storage.get_timeline(limit=10)
    assert len(timeline) == 1
    assert timeline[0].id == reading_id


def test_record_meter_result_with_snapshots(tmp_path, temp_snapshots_dir):
    db_path = tmp_path / "test_mr.db"
    db_url = f"sqlite:///{db_path}"

    storage = SQLAlchemyStorageBackend(
        db_url=db_url,
        snapshots_dir=temp_snapshots_dir,
        snapshot_mode="smart_tiered",
    )

    config = Config()
    config.snapshots = Snapshots(mode="full_frames", format="webp", quality=80)

    meter_res = MeterResult()
    meter_res.meters = [
        MeterValue(
            name="total", value="123.45", unit="m3", quality="good", confidence=99.0
        )
    ]
    meter_res.digital_results = {"0": "1", "1": "2", "2": "3"}

    test_img = np.zeros((80, 80, 3), dtype=np.uint8)

    rec_id = storage.record_meter_result(
        result=meter_res,
        image=test_img,
        config=config,
    )

    assert rec_id is not None
    data, _mime = storage.get_frame_bytes(rec_id)
    assert data is not None


def test_prune_snapshots(tmp_path, temp_snapshots_dir):
    db_path = tmp_path / "test_prune.db"
    db_url = f"sqlite:///{db_path}"

    storage = SQLAlchemyStorageBackend(
        db_url=db_url,
        snapshots_dir=temp_snapshots_dir,
        max_records=100,
    )

    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 80)

    # Record 5 readings with snapshots
    for i in range(5):
        storage.record_reading(
            timestamp=datetime.now(UTC) + timedelta(seconds=i),
            meters={"total": MeterReading(value=float(i), raw_value=str(i), unit="m3")},
            frame_bytes=frame_bytes,
            frame_type="full",
        )

    # Prune with very small max_disk_mb (e.g. 0.0001 MB = 100 bytes)
    deleted = storage.prune_snapshots(max_disk_mb=0.0001)
    assert deleted > 0


def test_sql_storage_snapshots_fallback_search(tmp_path, temp_snapshots_dir):
    db_path = tmp_path / "test_fallback.db"
    db_url = f"sqlite:///{db_path}"

    storage = SQLAlchemyStorageBackend(
        db_url=db_url,
        snapshots_dir=temp_snapshots_dir,
        snapshot_mode="full_frames",
    )

    test_img = np.zeros((60, 60, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 80)

    reading_id = storage.record_reading(
        timestamp=datetime.now(UTC),
        meters={"total": MeterReading(value=200.0, raw_value="200.0", unit="m3")},
        frame_bytes=frame_bytes,
        frame_type="full",
    )
    assert reading_id is not None

    # Verify standard lookup
    data, mime = storage.get_frame_bytes(reading_id)
    assert data is not None
    assert mime == "image/webp"

    # Now simulate moving or renaming the file to another snapshot pattern in temp_snapshots_dir
    # e.g., rename to custom_999_12345.webp
    files = list((tmp_path / "snapshots").glob("*.*"))
    assert len(files) > 0
    orig_file = files[0]
    renamed_file = tmp_path / "snapshots" / f"custom_{reading_id}_1700000000.webp"
    orig_file.rename(renamed_file)

    # Even though row.frame_path points to old file, fallback glob pattern should resolve it
    found_data, found_mime = storage.get_frame_bytes(reading_id)
    assert found_data is not None
    assert found_mime == "image/webp"


def test_sql_storage_timeline_frames_only_filter(tmp_path, temp_snapshots_dir):
    db_path = tmp_path / "test_filter.db"
    db_url = f"sqlite:///{db_path}"

    storage = SQLAlchemyStorageBackend(
        db_url=db_url,
        snapshots_dir=temp_snapshots_dir,
    )

    test_img = np.zeros((40, 40, 3), dtype=np.uint8)
    frame_bytes = compress_image_to_bytes(test_img, "webp", 80)

    # Record 1 reading without frame
    storage.record_reading(
        timestamp=datetime.now(UTC),
        meters={"total": MeterReading(value=1.0, raw_value="1.0", unit="m3")},
    )

    # Record 1 reading with frame
    id2 = storage.record_reading(
        timestamp=datetime.now(UTC) + timedelta(seconds=1),
        meters={"total": MeterReading(value=2.0, raw_value="2.0", unit="m3")},
        frame_bytes=frame_bytes,
        frame_type="full",
    )

    all_timeline = storage.get_timeline(limit=10, frames_only=False)
    assert len(all_timeline) == 2

    frames_timeline = storage.get_timeline(limit=10, frames_only=True)
    assert len(frames_timeline) == 1
    assert frames_timeline[0].id == id2
