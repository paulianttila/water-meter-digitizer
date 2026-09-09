from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class LeakState(str, Enum):
    OK = "OK"
    FLOW_ACTIVE = "FLOW_ACTIVE"
    LEAK_DETECTED = "LEAK_DETECTED"


class LeakEvent(BaseModel):
    event_id: str
    meter_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float = 0.0
    leaked_volume: float = 0.0
    peak_flow_rate: float = 0.0
    resolved: bool = False
    resolution_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        res = self.model_dump()
        res["start_time"] = self.start_time.isoformat()
        res["end_time"] = self.end_time.isoformat() if self.end_time else None
        return res


class ZeroFlowStatus(BaseModel):
    enabled: bool
    meter_name: str
    state: LeakState
    last_zero_flow_time: datetime | None = None
    last_reading_time: datetime | None = None
    current_flow_duration_seconds: float = 0.0
    current_flow_volume: float = 0.0
    current_flow_rate: float = 0.0
    consecutive_zero_readings: int = 0
    active_event: LeakEvent | None = None
    recent_events: list[LeakEvent] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "meter_name": self.meter_name,
            "state": (
                self.state.value if isinstance(self.state, LeakState) else self.state
            ),
            "last_zero_flow_time": (
                self.last_zero_flow_time.isoformat()
                if self.last_zero_flow_time
                else None
            ),
            "last_reading_time": (
                self.last_reading_time.isoformat() if self.last_reading_time else None
            ),
            "current_flow_duration_seconds": round(
                self.current_flow_duration_seconds, 1
            ),
            "current_flow_duration_minutes": round(
                self.current_flow_duration_seconds / 60.0, 1
            ),
            "current_flow_volume": round(self.current_flow_volume, 6),
            "current_flow_rate": round(self.current_flow_rate, 6),
            "consecutive_zero_readings": self.consecutive_zero_readings,
            "active_event": (
                self.active_event.to_dict() if self.active_event else None
            ),
            "recent_events": [e.to_dict() for e in self.recent_events],
        }
