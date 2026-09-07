from collections import defaultdict
from datetime import datetime, timezone
import logging
import sys
import threading
from typing import Any, Literal

from .base import (
    ConsumptionRecord,
    MeterReading,
    ReadingRecord,
    StorageBackend,
    StorageSummary,
)

logger = logging.getLogger(__name__)


class MemoryStorageBackend(StorageBackend):
    """In-memory bounded storage for historical meter readings."""

    # Approximate memory overhead per record in bytes (dataclass + dicts + strings)
    ESTIMATED_BYTES_PER_RECORD = 600

    def __init__(
        self,
        max_memory_mb: float = 20.0,
        max_records: int = 50000,
    ) -> None:
        self.max_memory_mb = max(0.01, float(max_memory_mb))
        self.max_records = max(1, int(max_records))
        self.max_memory_bytes = int(self.max_memory_mb * 1024 * 1024)
        self._records: list[ReadingRecord] = []
        self._lock = threading.RLock()
        self._known_meters: set[str] = set()

    def record_reading(
        self,
        timestamp: datetime,
        meters: dict[str, MeterReading],
        digital_results: dict[str, str] | None = None,
        analog_results: dict[str, str] | None = None,
        error: str = "",
    ) -> None:
        """Record a single timestamped reading."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        record = ReadingRecord(
            timestamp=timestamp,
            meters=meters,
            digital_results=digital_results or {},
            analog_results=analog_results or {},
            error=error,
        )

        with self._lock:
            self._records.append(record)
            for name in meters:
                self._known_meters.add(name)
            self._enforce_limits()

    def record_meter_result(
        self,
        result: Any,
        timestamp: datetime | None = None,
    ) -> None:
        """Helper to record directly from a MeterResult object."""
        if result is None:
            return

        ts = timestamp or datetime.now(timezone.utc)
        meters_dict: dict[str, MeterReading] = {}

        if hasattr(result, "meters") and result.meters:
            for m in result.meters:
                try:
                    num_val = (
                        float(m.value) if m.value not in ("", "N", "NN.NNN") else None
                    )
                except (ValueError, TypeError):
                    num_val = None

                meters_dict[m.name] = MeterReading(
                    value=num_val,
                    raw_value=str(m.value),
                    unit=getattr(m, "unit", ""),
                    quality=getattr(m, "quality", "good"),
                    confidence=float(getattr(m, "confidence", 100.0)),
                )

        dig = getattr(result, "digital_results", {}) or {}
        ana = getattr(result, "analog_results", {}) or {}
        err = getattr(result, "error", "") or ""

        self.record_reading(
            timestamp=ts,
            meters=meters_dict,
            digital_results=dig,
            analog_results=ana,
            error=err,
        )

    def _estimate_memory_usage(self) -> int:
        """Calculate approximate memory usage of stored records."""
        base_size = sys.getsizeof(self._records)
        record_size = len(self._records) * self.ESTIMATED_BYTES_PER_RECORD
        return base_size + record_size

    def _enforce_limits(self) -> None:
        """Prune oldest records if record count or memory limit is exceeded."""
        # Count limit
        if len(self._records) > self.max_records:
            excess = len(self._records) - self.max_records
            del self._records[:excess]

        # Memory limit
        usage = self._estimate_memory_usage()
        while usage > self.max_memory_bytes and len(self._records) > 1:
            prune_count = max(1, len(self._records) // 10)
            del self._records[:prune_count]
            usage = self._estimate_memory_usage()

    def get_readings(
        self,
        meter_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[ReadingRecord]:
        """Query raw readings within an optional time range."""
        with self._lock:
            records = self._records[:]

        if start is not None:
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            records = [r for r in records if r.timestamp >= start]

        if end is not None:
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            records = [r for r in records if r.timestamp <= end]

        if meter_name:
            records = [r for r in records if meter_name in r.meters]

        if limit is not None and limit > 0:
            records = records[-limit:]

        return records

    @staticmethod
    def _format_bucket_key(
        dt: datetime, interval: Literal["hourly", "daily", "weekly"]
    ) -> str:
        """Format timestamp into bucket string."""
        if interval == "hourly":
            return dt.strftime("%Y-%m-%d %H:00")
        elif interval == "weekly":
            # ISO year and week number
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        else:  # daily
            return dt.strftime("%Y-%m-%d")

    def get_consumption(
        self,
        meter_name: str = "total",
        interval: Literal["hourly", "daily", "weekly"] = "daily",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ConsumptionRecord]:
        """Aggregate readings into consumption deltas per time bucket."""
        readings = self.get_readings(meter_name=meter_name, start=start, end=end)
        if not readings:
            return []

        # Sort chronologically
        readings.sort(key=lambda r: r.timestamp)

        # Group readings by bucket
        buckets: dict[str, list[tuple[datetime, MeterReading]]] = defaultdict(list)
        unit = ""

        for r in readings:
            if meter_name not in r.meters:
                continue
            mr = r.meters[meter_name]
            if mr.unit and not unit:
                unit = mr.unit
            key = self._format_bucket_key(r.timestamp, interval)
            buckets[key].append((r.timestamp, mr))

        result: list[ConsumptionRecord] = []
        last_known_value: float | None = None

        for bucket_key in sorted(buckets.keys()):
            items = buckets[bucket_key]
            times = [t for t, _ in items]
            valid_vals = [m.value for _, m in items if m.value is not None]

            start_time = min(times)
            end_time = max(times)
            reading_count = len(items)

            if not valid_vals:
                result.append(
                    ConsumptionRecord(
                        bucket=bucket_key,
                        start_time=start_time,
                        end_time=end_time,
                        meter_name=meter_name,
                        unit=unit,
                        consumption=0.0,
                        reading_count=reading_count,
                    )
                )
                continue

            start_val = valid_vals[0]
            end_val = valid_vals[-1]
            min_val = min(valid_vals)
            max_val = max(valid_vals)

            # Calculate consumption delta
            consumption = 0.0
            prev = last_known_value

            for _, mr in items:
                if mr.value is not None:
                    if prev is not None:
                        delta = mr.value - prev
                        # Only accumulate positive realistic deltas
                        if delta >= 0:
                            consumption += delta
                    prev = mr.value

            last_known_value = end_val

            # If only 1 reading in bucket and no previous, delta is 0.0
            # If multiple readings in bucket, consumption covers internal increments
            if len(valid_vals) > 1 and consumption == 0.0:
                consumption = max(0.0, max_val - min_val)

            result.append(
                ConsumptionRecord(
                    bucket=bucket_key,
                    start_time=start_time,
                    end_time=end_time,
                    meter_name=meter_name,
                    unit=unit,
                    consumption=round(consumption, 4),
                    start_value=start_val,
                    end_value=end_val,
                    min_value=min_val,
                    max_value=max_val,
                    reading_count=reading_count,
                )
            )

        return result

    def get_summary(self) -> StorageSummary:
        """Get summary statistics about storage health."""
        with self._lock:
            count = len(self._records)
            oldest = self._records[0].timestamp if count > 0 else None
            newest = self._records[-1].timestamp if count > 0 else None
            meters = sorted(list(self._known_meters))
            usage_bytes = self._estimate_memory_usage()

        return StorageSummary(
            backend="memory",
            total_records=count,
            memory_usage_bytes=usage_bytes,
            max_memory_bytes=self.max_memory_bytes,
            oldest_timestamp=oldest,
            newest_timestamp=newest,
            meters_tracked=meters,
        )

    def clear(self) -> None:
        """Clear all stored readings."""
        with self._lock:
            self._records.clear()
            self._known_meters.clear()
