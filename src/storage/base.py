from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MeterReading(BaseModel):
    value: float | None = None
    raw_value: str = ""
    unit: str = ""
    quality: str = "good"
    confidence: float = 100.0


class ReadingRecord(BaseModel):
    id: int | None = None
    timestamp: datetime
    meters: dict[str, MeterReading] = Field(default_factory=dict)
    digital_results: dict[str, str] = Field(default_factory=dict)
    analog_results: dict[str, str] = Field(default_factory=dict)
    error: str = ""
    frame_type: str | None = None  # "full", "roi_strip", or None
    frame_path: str | None = None
    flow_detected: bool = False
    confidence_scores: dict[str, float] = Field(default_factory=dict)


class ConsumptionRecord(BaseModel):
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


class StorageSummary(BaseModel):
    backend: str
    total_records: int
    memory_usage_bytes: int
    max_memory_bytes: int
    oldest_timestamp: datetime | None = None
    newest_timestamp: datetime | None = None
    meters_tracked: list[str] = Field(default_factory=list)
    total_snapshots: int = 0
    snapshot_disk_bytes: int = 0
    snapshot_mode: str = "disabled"


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
        frame_bytes: bytes | None = None,
        frame_type: str | None = None,
        flow_detected: bool = False,
        confidence_scores: dict[str, float] | None = None,
    ) -> int | None:
        """Record a single timestamped reading and return its ID."""
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
    def get_timeline(
        self,
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        frames_only: bool = False,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ReadingRecord]:
        """Query timeline frames with optional filtering for anomalies/snapshots."""
        pass

    @abstractmethod
    def get_frame_bytes(self, reading_id: int) -> tuple[bytes | None, str | None]:
        """Retrieve stored frame bytes and MIME type/format for a specific reading ID."""
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
    def prune_snapshots(
        self,
        retention_days: int | None = None,
        max_disk_mb: float | None = None,
    ) -> int:
        """Prune older snapshots based on tier retention or max disk usage."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored readings and snapshots."""
        pass
