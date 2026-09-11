import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any

from .models import LeakEvent, LeakState, ZeroFlowStatus

logger = logging.getLogger(__name__)


class ZeroFlowTracker:
    """Thread-safe Zero-Flow Tracker and Continuous Flow Leak Detector."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self._lock = threading.Lock()

        self._last_reading_time: datetime | None = None
        self._last_reading_value: float | None = None
        self._last_zero_flow_time: datetime | None = None
        self._continuous_flow_start_time: datetime | None = None
        self._continuous_flow_volume: float = 0.0
        self._peak_flow_rate: float = 0.0
        self._consecutive_zero_count: int = 0
        self._current_flow_rate: float = 0.0

        self._state: LeakState = LeakState.OK
        self._active_event: LeakEvent | None = None
        self._event_history: deque[LeakEvent] = deque(
            maxlen=getattr(config, "max_history_events", 50)
        )

    def evaluate_reading(
        self,
        timestamp: datetime,
        meter_value: float | None,
        confidence: float = 100.0,
        quality: str = "good",
        min_confidence_threshold: float = 50.0,
        max_gap_seconds: float = 7200.0,
    ) -> ZeroFlowStatus:
        """Evaluate a new meter reading for continuous flow and zero-flow events."""
        with self._lock:
            if not getattr(self.config, "enabled", False):
                return self._build_status(enabled=False)

            # Quality & Confidence filter
            if (
                meter_value is None
                or quality != "good"
                or confidence < min_confidence_threshold
            ):
                logger.debug(
                    "Skipping zero-flow evaluation: invalid reading value=%s, "
                    "quality=%s, confidence=%.1f",
                    meter_value,
                    quality,
                    confidence,
                )
                return self._build_status(enabled=True)

            if timestamp.tzinfo is None:
                timestamp = timestamp.astimezone()
            else:
                timestamp = timestamp.astimezone()

            # First reading initialization
            if self._last_reading_value is None or self._last_reading_time is None:
                self._last_reading_value = meter_value
                self._last_reading_time = timestamp
                self._last_zero_flow_time = timestamp
                logger.info(
                    "Initialized ZeroFlowTracker with baseline value=%.6f at %s",
                    meter_value,
                    timestamp.isoformat(),
                )
                return self._build_status(enabled=True)

            # Compute elapsed time
            dt_seconds = (timestamp - self._last_reading_time).total_seconds()
            if dt_seconds <= 0:
                logger.debug("Ignoring non-increasing timestamp in ZeroFlowTracker")
                return self._build_status(enabled=True)

            # Outage / gap watchdog: if gap is too large, reset continuous window
            if dt_seconds > max_gap_seconds:
                logger.warning(
                    "ZeroFlowTracker detected sample gap of %.1fs > %.1fs; "
                    "resetting continuous flow sequence",
                    dt_seconds,
                    max_gap_seconds,
                )
                if self._active_event is not None:
                    self._resolve_active_event(timestamp, "outage_reset")
                self._last_zero_flow_time = timestamp
                self._continuous_flow_start_time = None
                self._continuous_flow_volume = 0.0
                self._peak_flow_rate = 0.0
                self._consecutive_zero_count = 0
                self._state = LeakState.OK

            # Consumption delta
            dv = meter_value - self._last_reading_value

            # Monotonicity check / negative delta handling
            if dv < 0:
                logger.warning(
                    "Negative meter delta detected in ZeroFlowTracker: dv=%.6f; "
                    "ignoring sample for volume accumulation",
                    dv,
                )
                self._last_reading_time = timestamp
                self._last_reading_value = meter_value
                self._current_flow_rate = 0.0
                return self._build_status(enabled=True)

            # Flow rate per hour
            flow_rate_per_hour = (dv / dt_seconds) * 3600.0
            self._current_flow_rate = flow_rate_per_hour

            flow_threshold = getattr(self.config, "flow_threshold", 0.001)
            debounce_limit = max(1, getattr(self.config, "resolve_debounce_count", 2))

            if dv <= flow_threshold:
                # Zero / negligible flow observed
                self._consecutive_zero_count += 1
                if self._consecutive_zero_count >= debounce_limit:
                    self._last_zero_flow_time = timestamp
                    self._continuous_flow_start_time = None
                    self._continuous_flow_volume = 0.0
                    self._peak_flow_rate = 0.0

                    if self._active_event is not None:
                        logger.info(
                            "Zero flow confirmed after %d readings; "
                            "auto-resolving active leak alert",
                            self._consecutive_zero_count,
                        )
                        self._resolve_active_event(timestamp, "auto_zero_flow")

                    self._state = LeakState.OK
            else:
                # Active positive flow observed
                self._consecutive_zero_count = 0

                if self._continuous_flow_start_time is None:
                    self._continuous_flow_start_time = (
                        self._last_zero_flow_time or timestamp
                    )

                self._continuous_flow_volume += dv
                if flow_rate_per_hour > self._peak_flow_rate:
                    self._peak_flow_rate = flow_rate_per_hour

                zero_ref = self._last_zero_flow_time or timestamp
                flow_duration = (timestamp - zero_ref).total_seconds()
                hours_elapsed = flow_duration / 3600.0

                continuous_hours_thresh = getattr(
                    self.config, "continuous_flow_hours", 2.0
                )
                min_volume_thresh = getattr(self.config, "min_leak_volume", 0.010)

                # Dual condition trigger
                if (
                    hours_elapsed >= continuous_hours_thresh
                    and self._continuous_flow_volume >= min_volume_thresh
                ):
                    self._state = LeakState.LEAK_DETECTED
                    if self._active_event is None:
                        event_id = f"leak_{int(timestamp.timestamp())}"
                        self._active_event = LeakEvent(
                            event_id=event_id,
                            meter_name=getattr(self.config, "meter_name", "total"),
                            start_time=self._continuous_flow_start_time,
                            duration_seconds=flow_duration,
                            leaked_volume=self._continuous_flow_volume,
                            peak_flow_rate=self._peak_flow_rate,
                        )
                        logger.warning(
                            "LEAK DETECTED on meter '%s': duration=%.1fh >= %.1fh, "
                            "volume=%.4f >= %.4f",
                            getattr(self.config, "meter_name", "total"),
                            hours_elapsed,
                            continuous_hours_thresh,
                            self._continuous_flow_volume,
                            min_volume_thresh,
                        )
                    else:
                        self._active_event.duration_seconds = flow_duration
                        self._active_event.leaked_volume = self._continuous_flow_volume
                        self._active_event.peak_flow_rate = self._peak_flow_rate
                else:
                    if self._state != LeakState.LEAK_DETECTED:
                        self._state = LeakState.FLOW_ACTIVE

            self._last_reading_time = timestamp
            self._last_reading_value = meter_value
            return self._build_status(enabled=True)

    def _resolve_active_event(
        self, timestamp: datetime, reason: str = "auto_zero_flow"
    ) -> None:
        if self._active_event is not None:
            self._active_event.end_time = timestamp
            self._active_event.duration_seconds = (
                timestamp - self._active_event.start_time
            ).total_seconds()
            self._active_event.resolved = True
            self._active_event.resolution_reason = reason
            self._event_history.appendleft(self._active_event)
            self._active_event = None

    def reset(self) -> ZeroFlowStatus:
        """Manually reset and acknowledge any active leak alert."""
        with self._lock:
            now = datetime.now().astimezone()
            if self._active_event is not None:
                self._resolve_active_event(now, "manual_reset")
            self._last_zero_flow_time = now
            self._continuous_flow_start_time = None
            self._continuous_flow_volume = 0.0
            self._peak_flow_rate = 0.0
            self._consecutive_zero_count = 0
            self._state = LeakState.OK
            logger.info("ZeroFlowTracker manually reset to OK")
            return self._build_status(enabled=getattr(self.config, "enabled", False))

    def clear_history(self) -> None:
        """Clear all historical leak events."""
        with self._lock:
            self._event_history.clear()

    def get_status(self) -> ZeroFlowStatus:
        """Get snapshot of current tracker state and active/historical events."""
        with self._lock:
            return self._build_status(enabled=getattr(self.config, "enabled", False))

    def _build_status(self, enabled: bool) -> ZeroFlowStatus:
        duration = 0.0
        if self._last_zero_flow_time and self._last_reading_time:
            duration = max(
                0.0,
                (self._last_reading_time - self._last_zero_flow_time).total_seconds(),
            )

        return ZeroFlowStatus(
            enabled=enabled,
            meter_name=getattr(self.config, "meter_name", "total"),
            state=self._state if enabled else LeakState.OK,
            last_zero_flow_time=self._last_zero_flow_time,
            last_reading_time=self._last_reading_time,
            current_flow_duration_seconds=duration,
            current_flow_volume=self._continuous_flow_volume,
            current_flow_rate=self._current_flow_rate,
            consecutive_zero_readings=self._consecutive_zero_count,
            active_event=self._active_event,
            recent_events=list(self._event_history),
        )
