"""SQLAlchemy historical storage implementation supporting SQLite, PostgreSQL, and other relational backends."""

import json
import logging
import os
import re
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import (
    create_engine,
    delete,
    event,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from utils.visual_diff import compress_image_to_bytes, create_roi_composite_strip

from .aggregations import aggregate_consumption
from .base import (
    ConsumptionRecord,
    MeterReading,
    ReadingRecord,
    StorageBackend,
    StorageSummary,
)
from .models import Base, ReadingModel
from .pruner import prune_database
from .snapshots import (
    detect_mime,
    ensure_snapshots_dir,
    find_frame_bytes,
    prune_disk_snapshots,
    read_file_safe,
)

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_FRAMES_CAP = 50
DEFAULT_SNAPSHOT_MAX_DISK_MB = 500.0
ESTIMATED_BYTES_PER_RECORD = 300


def _to_local(ts: datetime) -> datetime:
    """Normalize a datetime to local timezone with fallback."""
    if ts.tzinfo is not None:
        return ts.astimezone()
    return ts.replace(tzinfo=datetime.now().astimezone().tzinfo)


class SQLAlchemyStorageBackend(StorageBackend):
    """SQLAlchemy-based historical storage supporting SQLite (memory/disk),

    PostgreSQL, MySQL, and other standard relational databases with bounded
    retention policies, snapshot archival, and space management.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///:memory:",
        max_memory_mb: float = 20.0,
        retention_days: int = 30,
        max_records: int = 50000,
        auto_vacuum: bool = True,
        prune_interval: int = 50,
        snapshots_dir: str | None = None,
        snapshot_mode: str = "smart_tiered",
    ) -> None:
        self.db_url = db_url or "sqlite:///:memory:"
        self.max_memory_mb = max_memory_mb
        self.retention_days = max(0, retention_days)
        self.max_records = max(0, max_records)
        self.auto_vacuum = auto_vacuum
        self.prune_interval = max(1, prune_interval)
        self.snapshot_mode = snapshot_mode
        self.snapshots_dir = snapshots_dir or "/data/snapshots"
        if self.max_records > 0:
            self.prune_interval = max(1, min(self.prune_interval, self.max_records))
        self._write_count = 0
        self._last_saved_snapshot_ts: datetime | None = None
        self._last_meter_values: dict[str, float] = {}
        self._memory_frames: OrderedDict[int, tuple[bytes, str]] = OrderedDict()
        self._lock = threading.Lock()

        self.is_memory = (
            self.db_url.lower() == "memory"
            or "sqlite:///:memory:" in self.db_url.lower()
            or "mode=memory" in self.db_url.lower()
        )
        self.is_sqlite = self.db_url.lower().startswith("sqlite")
        self.sqlite_file_path: str | None = None

        if self.is_memory:
            self.db_url = "sqlite:///:memory:"
            self.engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        elif self.is_sqlite:
            self.sqlite_file_path = self._extract_sqlite_path(self.db_url)
            fallback_to_memory = False
            if self.sqlite_file_path:
                try:
                    Path(self.sqlite_file_path).parent.mkdir(
                        parents=True, exist_ok=True
                    )
                except (OSError, PermissionError) as e:
                    logger.warning(
                        "Cannot create directory %s for SQLite (%s). "
                        "Falling back to in-memory DB.",
                        Path(self.sqlite_file_path).parent,
                        e,
                    )
                    fallback_to_memory = True

            if fallback_to_memory:
                self.is_memory = True
                self.db_url = "sqlite:///:memory:"
                self.sqlite_file_path = None
                self.engine = create_engine(
                    self.db_url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )
            else:
                self.engine = create_engine(
                    self.db_url,
                    connect_args={"check_same_thread": False},
                )

                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    if self.auto_vacuum:
                        cursor.execute("PRAGMA auto_vacuum=INCREMENTAL")
                    cursor.close()

        else:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)

        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            logger.warning(
                "Failed to initialize database tables on %s (%s). "
                "Falling back to in-memory DB.",
                self.db_url,
                e,
            )
            self.is_memory = True
            self.db_url = "sqlite:///:memory:"
            self.sqlite_file_path = None
            self.engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            Base.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    @staticmethod
    def _extract_sqlite_path(url: str) -> str | None:
        """Extract filesystem path from sqlite:///... URL."""
        if not url.startswith("sqlite"):
            return None
        clean_url = url.split("?")[0]
        match = re.match(r"^sqlite:///(.*)$", clean_url)
        if match:
            path = match.group(1)
            return os.path.abspath(path)
        return None

    def _ensure_snapshots_dir(self) -> Path | None:
        if self.is_memory or not self.snapshots_dir:
            return None
        p = ensure_snapshots_dir(self.snapshots_dir)
        if p is not None:
            return p
        # Fallback to local snapshots or data/snapshots directory
        for fallback in [
            Path("snapshots"),
            Path("data/snapshots"),
            Path("./snapshots"),
        ]:
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                self.snapshots_dir = str(fallback)
                logger.info("Using fallback snapshots directory: %s", fallback)
                return fallback
            except Exception as fb_err:
                logger.debug("Fallback %s failed: %s", fallback, fb_err)
        return None

    def record_reading(
        self,
        timestamp: datetime,
        meters: dict[str, MeterReading],
        digital_results: dict[str, str] | None = None,
        analog_results: dict[str, str] | None = None,
        error: str = "",
        frame_bytes: bytes | None = None,
        frame_type: str | None = None,
        flow_detected: bool = False,
        confidence_scores: dict[str, float] | None = None,
    ) -> int | None:
        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()
        else:
            timestamp = timestamp.astimezone()

        meters_dict = {k: v.model_dump() for k, v in meters.items()}
        meters_json = json.dumps(meters_dict)
        digital_json = json.dumps(digital_results) if digital_results else None
        analog_json = json.dumps(analog_results) if analog_results else None
        conf_json = json.dumps(confidence_scores) if confidence_scores else None

        frame_path: str | None = None
        frame_blob: bytes | None = None

        with self._lock, self.Session() as session:
            entry = ReadingModel(
                timestamp=timestamp,
                meters_json=meters_json,
                digital_json=digital_json,
                analog_json=analog_json,
                error=error or "",
                frame_type=frame_type,
                flow_detected=flow_detected,
                confidence_scores_json=conf_json,
            )
            session.add(entry)
            session.flush()
            inserted_id = entry.id

            if frame_bytes and frame_type:
                snap_dir = self._ensure_snapshots_dir()
                if snap_dir:
                    ext = "webp" if frame_bytes.startswith(b"RIFF") else "jpg"
                    prefix = "strip" if frame_type == "roi_strip" else "frame"
                    fname = f"{prefix}_{inserted_id}_{int(timestamp.timestamp())}.{ext}"
                    fpath = snap_dir / fname
                    try:
                        fpath.write_bytes(frame_bytes)
                        frame_path = str(fpath)
                        entry.frame_path = frame_path
                    except Exception as e:
                        logger.warning("Failed writing frame file %s: %s", fpath, e)
                        frame_blob = frame_bytes
                        entry.frame_blob = frame_blob
                else:
                    # In-memory storage / blob fallback
                    frame_blob = frame_bytes
                    entry.frame_blob = frame_blob
                    self._memory_frames[inserted_id] = (frame_bytes, frame_type)
                    # Limit memory frame ring buffer to ~50 frames
                    while len(self._memory_frames) > DEFAULT_MEMORY_FRAMES_CAP:
                        self._memory_frames.popitem(last=False)

            session.commit()

            self._write_count += 1
            if self._write_count % self.prune_interval == 0:
                self._prune_and_vacuum(session)

            return inserted_id

    def record_meter_result(
        self,
        result: Any,
        timestamp: datetime | None = None,
        image: Any | None = None,
        config: Any | None = None,
    ) -> int | None:
        ts = timestamp if timestamp is not None else datetime.now().astimezone()
        meters: dict[str, MeterReading] = {}
        flow_detected = False
        confidence_scores: dict[str, float] = {}

        for m in result.meters:
            num_val: float | None = None
            try:
                num_val = float(m.value)
            except (ValueError, TypeError):
                num_val = None

            raw_v = str(m.value) if m.value is not None else ""
            meters[m.name] = MeterReading(
                value=num_val,
                raw_value=raw_v,
                unit=m.unit or "",
                quality=getattr(m, "quality", "good"),
                confidence=getattr(m, "confidence", 100.0),
            )
            confidence_scores[m.name] = getattr(m, "confidence", 100.0)

            # Check flow
            if num_val is not None:
                prev = self._last_meter_values.get(m.name)
                if prev is not None and abs(num_val - prev) > 1e-5:
                    flow_detected = True
                self._last_meter_values[m.name] = num_val

        # Digital/analog individual confidences if present
        if hasattr(result, "digital_results") and isinstance(
            result.digital_results, dict
        ):
            for k, _v in result.digital_results.items():
                confidence_scores[f"digital_{k}"] = result.confidence_scores.get(
                    k, 100.0
                )

        # Snapshot evaluation
        frame_bytes: bytes | None = None
        frame_type: str | None = None

        snap_cfg = getattr(config, "snapshots", None) if config else None
        mode = getattr(snap_cfg, "mode", "smart_tiered") if snap_cfg else "smart_tiered"
        fmt = getattr(snap_cfg, "format", "webp") if snap_cfg else "webp"
        quality = getattr(snap_cfg, "quality", 75) if snap_cfg else 75
        heartbeat_min = (
            getattr(snap_cfg, "idle_heartbeat_minutes", 15) if snap_cfg else 15
        )
        always_anomaly = (
            getattr(snap_cfg, "always_save_on_anomaly", True) if snap_cfg else True
        )

        has_anomaly = bool(getattr(result, "error", "")) or any(
            m.quality != "good" for m in meters.values()
        )

        heartbeat_due = False
        if self._last_saved_snapshot_ts is None:
            heartbeat_due = True
        else:
            diff_min = (ts - self._last_saved_snapshot_ts).total_seconds() / 60.0
            if diff_min >= heartbeat_min:
                heartbeat_due = True

        if image is not None and mode != "disabled":
            should_save = False
            chosen_type = "full"

            if mode == "full_frames":
                should_save = True
                chosen_type = "full"
            elif mode == "roi_strips_only":
                should_save = True
                chosen_type = "roi_strip"
            elif mode == "change_only":
                if flow_detected or (always_anomaly and has_anomaly) or heartbeat_due:
                    should_save = True
                    chosen_type = "full"
            elif mode == "smart_tiered":
                if flow_detected or (always_anomaly and has_anomaly) or heartbeat_due:
                    should_save = True
                    chosen_type = "full"
                else:
                    should_save = True
                    chosen_type = "roi_strip"

            if should_save:
                if chosen_type == "roi_strip" and config is not None:
                    dig_rois = getattr(config.digital_readout, "cut_images", [])
                    ana_rois = getattr(config.analog_readout, "cut_images", [])
                    strip = create_roi_composite_strip(image, dig_rois, ana_rois)
                    frame_bytes = compress_image_to_bytes(
                        strip, format_type=fmt, quality=quality
                    )
                    frame_type = "roi_strip"
                else:
                    frame_bytes = compress_image_to_bytes(
                        image, format_type=fmt, quality=quality
                    )
                    frame_type = "full"

                self._last_saved_snapshot_ts = ts

        return self.record_reading(
            timestamp=ts,
            meters=meters,
            digital_results=getattr(result, "digital_results", None),
            analog_results=getattr(result, "analog_results", None),
            error=getattr(result, "error", ""),
            frame_bytes=frame_bytes,
            frame_type=frame_type,
            flow_detected=flow_detected,
            confidence_scores=confidence_scores,
        )

    def _prune_and_vacuum(self, session: Any) -> None:
        """Enforce time-based retention, max records limits, and snapshot storage caps."""
        prune_database(
            session=session,
            retention_days=self.retention_days,
            max_records=self.max_records,
            is_sqlite=self.is_sqlite,
            is_memory=self.is_memory,
            auto_vacuum=self.auto_vacuum,
            snapshots_dir=self.snapshots_dir,
            max_disk_mb=DEFAULT_SNAPSHOT_MAX_DISK_MB,
            memory_frames=self._memory_frames,
        )

    def prune_snapshots(
        self,
        retention_days: int | None = None,
        max_disk_mb: float | None = None,
    ) -> int:
        """Prune snapshot files exceeding max disk limit or age threshold."""
        return prune_disk_snapshots(
            self.snapshots_dir, max_disk_mb or DEFAULT_SNAPSHOT_MAX_DISK_MB
        )

    def prune(self) -> None:
        """Manually trigger pruning and vacuuming."""
        with self._lock, self.Session() as session:
            self._prune_and_vacuum(session)

    def get_readings(
        self,
        meter_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[ReadingRecord]:
        with self._lock, self.Session() as session:
            query = select(ReadingModel)
            if start is not None:
                query = query.where(ReadingModel.timestamp >= _to_local(start))
            if end is not None:
                query = query.where(ReadingModel.timestamp <= _to_local(end))

            if limit is not None and limit > 0:
                query = query.order_by(ReadingModel.timestamp.desc()).limit(limit)
                rows = list(reversed(session.scalars(query).all()))
            else:
                query = query.order_by(ReadingModel.timestamp.asc())
                rows = list(session.scalars(query).all())

        results: list[ReadingRecord] = []
        for r in rows:
            raw_meters = json.loads(r.meters_json)
            parsed_meters = {
                k: MeterReading(
                    value=v.get("value"),
                    raw_value=v.get("raw_value", ""),
                    unit=v.get("unit", ""),
                    quality=v.get("quality", "good"),
                    confidence=v.get("confidence", 100.0),
                )
                for k, v in raw_meters.items()
            }

            if meter_name and meter_name not in parsed_meters:
                continue

            conf_dict = {}
            if r.confidence_scores_json:
                try:
                    conf_dict = json.loads(r.confidence_scores_json)
                except Exception:
                    conf_dict = {}

            rec = ReadingRecord(
                id=r.id,
                timestamp=_to_local(r.timestamp),
                meters=parsed_meters,
                digital_results=json.loads(r.digital_json) if r.digital_json else {},
                analog_results=json.loads(r.analog_json) if r.analog_json else {},
                error=r.error or "",
                frame_type=r.frame_type,
                frame_path=r.frame_path,
                flow_detected=bool(r.flow_detected),
                confidence_scores=conf_dict,
            )
            results.append(rec)

        return results

    def get_timeline(
        self,
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        frames_only: bool = False,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ReadingRecord]:
        with self._lock, self.Session() as session:
            query = select(ReadingModel)
            if start is not None:
                query = query.where(ReadingModel.timestamp >= _to_local(start))
            if end is not None:
                query = query.where(ReadingModel.timestamp <= _to_local(end))

            if anomalies_only:
                query = query.where(ReadingModel.error != "")

            if frames_only:
                query = query.where(
                    or_(
                        ReadingModel.frame_type.is_not(None),
                        ReadingModel.frame_path.is_not(None),
                        ReadingModel.frame_blob.is_not(None),
                    )
                )

            query = (
                query.order_by(ReadingModel.timestamp.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.scalars(query).all()

        results: list[ReadingRecord] = []
        for r in rows:
            raw_meters = json.loads(r.meters_json)
            parsed_meters = {
                k: MeterReading(
                    value=v.get("value"),
                    raw_value=v.get("raw_value", ""),
                    unit=v.get("unit", ""),
                    quality=v.get("quality", "good"),
                    confidence=v.get("confidence", 100.0),
                )
                for k, v in raw_meters.items()
            }

            conf_dict = {}
            if r.confidence_scores_json:
                try:
                    conf_dict = json.loads(r.confidence_scores_json)
                except Exception:
                    conf_dict = {}

            results.append(
                ReadingRecord(
                    id=r.id,
                    timestamp=_to_local(r.timestamp),
                    meters=parsed_meters,
                    digital_results=(
                        json.loads(r.digital_json) if r.digital_json else {}
                    ),
                    analog_results=json.loads(r.analog_json) if r.analog_json else {},
                    error=r.error or "",
                    frame_type=r.frame_type,
                    frame_path=r.frame_path,
                    flow_detected=bool(r.flow_detected),
                    confidence_scores=conf_dict,
                )
            )
        return results

    def get_frame_bytes(self, reading_id: int) -> tuple[bytes | None, str | None]:
        logger.debug("get_frame_bytes: lookup initiated for reading_id=%s", reading_id)
        # 1. Check in-memory ring buffer
        if reading_id in self._memory_frames:
            data, _ftype = self._memory_frames[reading_id]
            mime = "image/webp" if data.startswith(b"RIFF") else "image/jpeg"
            logger.debug(
                "get_frame_bytes: found frame in memory ring buffer for reading_id=%s (%d bytes, %s)",
                reading_id,
                len(data),
                mime,
            )
            return data, mime

        # 2. Check database row
        row_frame_path = None
        row_frame_blob = None
        with self._lock, self.Session() as session:
            row = session.get(ReadingModel, reading_id)
            if row:
                row_frame_path = row.frame_path
                row_frame_blob = row.frame_blob
                logger.debug(
                    "get_frame_bytes: DB row #%s found: frame_path='%s', frame_type='%s', has_blob=%s",
                    reading_id,
                    row.frame_path,
                    row.frame_type,
                    row.frame_blob is not None,
                )

        return find_frame_bytes(
            reading_id=reading_id,
            row_frame_path=row_frame_path,
            row_frame_blob=row_frame_blob,
            memory_frames=self._memory_frames,
            snapshots_dir=self.snapshots_dir,
        )

    def get_consumption(
        self,
        meter_name: str = "total",
        interval: Literal["hourly", "daily", "weekly", "monthly"] = "daily",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ConsumptionRecord]:
        readings = self.get_readings(meter_name=meter_name, start=start, end=end)
        return aggregate_consumption(
            readings=readings, meter_name=meter_name, interval=interval
        )

    def get_summary(self) -> StorageSummary:
        with self._lock, self.Session() as session:
            total_records = session.scalar(select(func.count(ReadingModel.id))) or 0
            min_ts = session.scalar(select(func.min(ReadingModel.timestamp)))
            max_ts = session.scalar(select(func.max(ReadingModel.timestamp)))
            total_snaps = (
                session.scalar(
                    select(func.count(ReadingModel.id)).where(
                        or_(
                            ReadingModel.frame_type.is_not(None),
                            ReadingModel.frame_path.is_not(None),
                            ReadingModel.frame_blob.is_not(None),
                        )
                    )
                )
                or 0
            )

            # Sample recent meters
            sample_rows = session.scalars(
                select(ReadingModel.meters_json)
                .order_by(ReadingModel.timestamp.desc())
                .limit(10)
            ).all()

        meters_tracked: set[str] = set()
        for s in sample_rows:
            try:
                meters_tracked.update(json.loads(s).keys())
            except Exception as e:
                logger.debug("Failed parsing meters_json sample: %s", e)

        mem_bytes = 0
        if self.is_sqlite and self.sqlite_file_path:
            if os.path.exists(self.sqlite_file_path):
                mem_bytes = os.path.getsize(self.sqlite_file_path)
        elif self.is_memory:
            with self._lock, self.Session() as session:
                try:
                    page_count = session.scalar(text("PRAGMA page_count")) or 0
                    page_size = session.scalar(text("PRAGMA page_size")) or 4096
                    mem_bytes = page_count * page_size
                except Exception as e:
                    logger.debug("Failed reading SQLite page metrics: %s", e)
                    mem_bytes = total_records * 300
        else:
            mem_bytes = total_records * 300

        # Measure snapshot disk usage
        snap_disk_bytes = 0
        if (
            not self.is_memory
            and self.snapshots_dir
            and os.path.exists(self.snapshots_dir)
        ):
            try:
                snap_disk_bytes = sum(
                    f.stat().st_size
                    for f in Path(self.snapshots_dir).glob("*.*")
                    if f.is_file()
                )
            except Exception:
                snap_disk_bytes = 0
        else:
            snap_disk_bytes = sum(len(b) for b, _ in self._memory_frames.values())

        backend_name = (
            "memory"
            if self.is_memory
            else ("sqlite" if self.is_sqlite else "sqlalchemy")
        )

        return StorageSummary(
            backend=backend_name,
            total_records=total_records,
            memory_usage_bytes=mem_bytes,
            max_memory_bytes=self.max_records * ESTIMATED_BYTES_PER_RECORD,
            oldest_timestamp=_to_local(min_ts) if min_ts else None,
            newest_timestamp=_to_local(max_ts) if max_ts else None,
            meters_tracked=sorted(list(meters_tracked)),
            total_snapshots=total_snaps + len(self._memory_frames),
            snapshot_disk_bytes=snap_disk_bytes,
            snapshot_mode=self.snapshot_mode,
        )

    def clear(self) -> None:
        with self._lock, self.Session() as session:
            session.execute(delete(ReadingModel))
            session.commit()
            if self.is_sqlite and not self.is_memory:
                try:
                    session.execute(text("VACUUM"))
                    session.commit()
                except Exception as e:
                    logger.debug("Vacuum on clear ignored error: %s", e)

        self._memory_frames.clear()
        snap_dir = self._ensure_snapshots_dir()
        if snap_dir and snap_dir.exists():
            for f in snap_dir.glob("*.*"):
                try:
                    f.unlink(missing_ok=True)
                except Exception as e:
                    logger.debug("Failed deleting snapshot file %s: %s", f, e)


__all__ = [
    "Base",
    "ReadingModel",
    "SQLAlchemyStorageBackend",
    "detect_mime",
    "ensure_snapshots_dir",
    "find_frame_bytes",
    "prune_disk_snapshots",
    "read_file_safe",
]
