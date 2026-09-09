from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any, Literal

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    delete,
    event,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import (
    ConsumptionRecord,
    MeterReading,
    ReadingRecord,
    StorageBackend,
    StorageSummary,
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class ReadingModel(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    meters_json: Mapped[str] = mapped_column(Text, nullable=False)
    digital_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analog_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str] = mapped_column(String(500), default="")


class SQLAlchemyStorageBackend(StorageBackend):
    """SQLAlchemy-based historical storage supporting SQLite (memory/disk),

    PostgreSQL, MySQL, and other standard relational databases with bounded
    retention policies and space management.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///:memory:",
        max_memory_mb: float = 20.0,
        retention_days: int = 30,
        max_records: int = 50000,
        auto_vacuum: bool = True,
        prune_interval: int = 50,
    ) -> None:
        self.db_url = db_url or "sqlite:///:memory:"
        self.max_memory_mb = max_memory_mb
        self.retention_days = max(0, retention_days)
        self.max_records = max(0, max_records)
        self.auto_vacuum = auto_vacuum
        self.prune_interval = max(1, prune_interval)
        if self.max_records > 0:
            self.prune_interval = max(1, min(self.prune_interval, self.max_records))
        self._write_count = 0
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
        except (OSError, PermissionError) as e:
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

    def record_reading(
        self,
        timestamp: datetime,
        meters: dict[str, MeterReading],
        digital_results: dict[str, str] | None = None,
        analog_results: dict[str, str] | None = None,
        error: str = "",
    ) -> None:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        meters_dict = {k: v.model_dump() for k, v in meters.items()}
        meters_json = json.dumps(meters_dict)
        digital_json = json.dumps(digital_results) if digital_results else None
        analog_json = json.dumps(analog_results) if analog_results else None

        with self._lock:
            with self.Session() as session:
                entry = ReadingModel(
                    timestamp=timestamp,
                    meters_json=meters_json,
                    digital_json=digital_json,
                    analog_json=analog_json,
                    error=error or "",
                )
                session.add(entry)
                session.commit()

                self._write_count += 1
                if self._write_count % self.prune_interval == 0:
                    self._prune_and_vacuum(session)

    def record_meter_result(
        self,
        result: Any,
        timestamp: datetime | None = None,
    ) -> None:
        ts = timestamp or datetime.now(timezone.utc)
        meters: dict[str, MeterReading] = {}
        for m in result.meters:
            num_val: float | None = None
            try:
                num_val = float(m.value)
            except (ValueError, TypeError):
                num_val = None
            meters[m.name] = MeterReading(
                value=num_val,
                raw_value=str(m.value) if m.value is not None else "",
                unit=m.unit or "",
                quality=getattr(m, "quality", "good"),
                confidence=getattr(m, "confidence", 100.0),
            )

        self.record_reading(
            timestamp=ts,
            meters=meters,
            digital_results=result.digital_results,
            analog_results=result.analog_results,
            error=getattr(result, "error", ""),
        )

    def _prune_and_vacuum(self, session: Any) -> None:
        """Enforce time-based retention and max records limits, then vacuum."""
        now = datetime.now(timezone.utc)

        # 1. Time-based retention pruning
        if self.retention_days > 0:
            cutoff = now - timedelta(days=self.retention_days)
            session.execute(delete(ReadingModel).where(ReadingModel.timestamp < cutoff))
            session.commit()

        # 2. Max row count limit (oldest-first FIFO)
        if self.max_records > 0:
            total_count = session.scalar(select(func.count(ReadingModel.id))) or 0
            if total_count > self.max_records:
                excess = total_count - self.max_records
                oldest_ids = session.scalars(
                    select(ReadingModel.id)
                    .order_by(ReadingModel.timestamp.asc())
                    .limit(excess)
                ).all()
                if oldest_ids:
                    session.execute(
                        delete(ReadingModel).where(ReadingModel.id.in_(oldest_ids))
                    )
                    session.commit()

        # 3. SQLite incremental vacuum to return freed pages to OS
        if self.is_sqlite and not self.is_memory and self.auto_vacuum:
            try:
                session.execute(text("PRAGMA incremental_vacuum"))
                session.commit()
            except Exception as e:
                logger.debug("Incremental vacuum ignored error: %s", e)

    def prune(self) -> None:
        """Manually trigger pruning and vacuuming."""
        with self._lock:
            with self.Session() as session:
                self._prune_and_vacuum(session)

    def get_readings(
        self,
        meter_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[ReadingRecord]:
        with self._lock:
            with self.Session() as session:
                query = select(ReadingModel)
                if start is not None:
                    s_utc = (
                        start.replace(tzinfo=timezone.utc)
                        if start.tzinfo is None
                        else start.astimezone(timezone.utc)
                    )
                    query = query.where(ReadingModel.timestamp >= s_utc)
                if end is not None:
                    e_utc = (
                        end.replace(tzinfo=timezone.utc)
                        if end.tzinfo is None
                        else end.astimezone(timezone.utc)
                    )
                    query = query.where(ReadingModel.timestamp <= e_utc)

                if limit is not None and limit > 0:
                    query = query.order_by(ReadingModel.timestamp.desc()).limit(limit)
                    rows = list(reversed(session.scalars(query).all()))
                else:
                    query = query.order_by(ReadingModel.timestamp.asc())
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

            if meter_name and meter_name not in parsed_meters:
                continue

            rec = ReadingRecord(
                timestamp=(
                    r.timestamp.replace(tzinfo=timezone.utc)
                    if r.timestamp.tzinfo is None
                    else r.timestamp
                ),
                meters=parsed_meters,
                digital_results=json.loads(r.digital_json) if r.digital_json else {},
                analog_results=json.loads(r.analog_json) if r.analog_json else {},
                error=r.error or "",
            )
            results.append(rec)

        return results

    def get_consumption(
        self,
        meter_name: str = "total",
        interval: Literal["hourly", "daily", "weekly"] = "daily",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ConsumptionRecord]:
        readings = self.get_readings(meter_name=meter_name, start=start, end=end)
        if not readings:
            return []

        def get_bucket_key(ts: datetime) -> str:
            if interval == "hourly":
                return ts.strftime("%Y-%m-%d %H:00")
            if interval == "weekly":
                return f"{ts.year}-W{ts.isocalendar()[1]:02d}"
            return ts.strftime("%Y-%m-%d")

        bucket_groups: dict[str, list[tuple[datetime, float, str]]] = defaultdict(list)
        for r in readings:
            if meter_name in r.meters:
                m = r.meters[meter_name]
                if m.value is not None:
                    b_key = get_bucket_key(r.timestamp)
                    bucket_groups[b_key].append((r.timestamp, m.value, m.unit))

        sorted_buckets = sorted(bucket_groups.keys())
        consumption_records: list[ConsumptionRecord] = []

        prev_end_value: float | None = None

        for b_key in sorted_buckets:
            items = bucket_groups[b_key]
            if not items:
                continue

            items_sorted = sorted(items, key=lambda x: x[0])
            start_t = items_sorted[0][0]
            end_t = items_sorted[-1][0]
            unit = items_sorted[0][2]
            values = [x[1] for x in items_sorted]

            start_v = values[0]
            end_v = values[-1]
            min_v = min(values)
            max_v = max(values)
            cnt = len(values)

            # Delta within bucket
            bucket_delta = 0.0
            for i in range(1, len(values)):
                diff = values[i] - values[i - 1]
                if diff > 0:
                    bucket_delta += diff

            # If there was a previous bucket reading, include cross-bucket jump
            if prev_end_value is not None:
                cross_diff = start_v - prev_end_value
                if 0 < cross_diff < 1000.0:
                    bucket_delta += cross_diff

            prev_end_value = end_v

            consumption_records.append(
                ConsumptionRecord(
                    bucket=b_key,
                    start_time=start_t,
                    end_time=end_t,
                    meter_name=meter_name,
                    unit=unit,
                    consumption=round(bucket_delta, 3),
                    start_value=start_v,
                    end_value=end_v,
                    min_value=min_v,
                    max_value=max_v,
                    reading_count=cnt,
                )
            )

        return consumption_records

    def get_summary(self) -> StorageSummary:
        with self._lock:
            with self.Session() as session:
                total_records = session.scalar(select(func.count(ReadingModel.id))) or 0
                min_ts = session.scalar(select(func.min(ReadingModel.timestamp)))
                max_ts = session.scalar(select(func.max(ReadingModel.timestamp)))

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
            with self._lock:
                with self.Session() as session:
                    try:
                        page_count = session.scalar(text("PRAGMA page_count")) or 0
                        page_size = session.scalar(text("PRAGMA page_size")) or 4096
                        mem_bytes = page_count * page_size
                    except Exception as e:
                        logger.debug("Failed reading SQLite page metrics: %s", e)
                        mem_bytes = total_records * 300
        else:
            mem_bytes = total_records * 300

        backend_name = (
            "memory"
            if self.is_memory
            else ("sqlite" if self.is_sqlite else "sqlalchemy")
        )

        return StorageSummary(
            backend=backend_name,
            total_records=total_records,
            memory_usage_bytes=mem_bytes,
            max_memory_bytes=self.max_records * 300,
            oldest_timestamp=(
                min_ts.replace(tzinfo=timezone.utc)
                if min_ts and min_ts.tzinfo is None
                else min_ts
            ),
            newest_timestamp=(
                max_ts.replace(tzinfo=timezone.utc)
                if max_ts and max_ts.tzinfo is None
                else max_ts
            ),
            meters_tracked=sorted(list(meters_tracked)),
        )

    def clear(self) -> None:
        with self._lock:
            with self.Session() as session:
                session.execute(delete(ReadingModel))
                session.commit()
                if self.is_sqlite and not self.is_memory:
                    try:
                        session.execute(text("VACUUM"))
                        session.commit()
                    except Exception as e:
                        logger.debug("Vacuum on clear ignored error: %s", e)
