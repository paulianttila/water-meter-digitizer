from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class MeterReading:
    value: float | None = None
    raw_value: str = ""
    unit: str = ""
    quality: str = "good"
    confidence: float = 100.0


@dataclass
class ReadingRecord:
    timestamp: datetime
    meters: dict[str, MeterReading] = field(default_factory=dict)
    digital_results: dict[str, str] = field(default_factory=dict)
    analog_results: dict[str, str] = field(default_factory=dict)
    error: str = ""


@dataclass
class ConsumptionRecord:
    bucket: str  # e.g. "2026-09-06" or "2026-09-06 14:00" or "2026-W36"
    start_time: datetime
    end_time: datetime
    meter_name: str
    unit: str
    consumption: float
    start_value: float | None = None
    end_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    reading_count: int = 0


@dataclass
class StorageSummary:
    backend: str
    total_records: int
    memory_usage_bytes: int
    max_memory_bytes: int
    oldest_timestamp: datetime | None = None
    newest_timestamp: datetime | None = None
    meters_tracked: list[str] = field(default_factory=list)


class StorageBackend(ABC):
    """Abstract interface for historical meter reading storage backends."""

    @abstractmethod
    def record_reading(
        self,
        timestamp: datetime,
        meters: dict[str, MeterReading],
        digital_results: dict[str, str] | None = None,
        analog_results: dict[str, str] | None = None,
        error: str = "",
    ) -> None:
        """Record a single timestamped reading."""
        pass

    @abstractmethod
    def get_readings(
        self,
        meter_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[ReadingRecord]:
        """Query raw readings within an optional time range."""
        pass

    @abstractmethod
    def get_consumption(
        self,
        meter_name: str = "total",
        interval: Literal["hourly", "daily", "weekly"] = "daily",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ConsumptionRecord]:
        """Aggregate readings into consumption deltas per time bucket."""
        pass

    @abstractmethod
    def get_summary(self) -> StorageSummary:
        """Get summary statistics and health information about the storage."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored readings."""
        pass
