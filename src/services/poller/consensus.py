"""Temporal consensus and median filter for meter readout results."""

import logging
import statistics
from collections import Counter, deque

from processor.digitizer import MeterResult

logger = logging.getLogger(__name__)


class ConsensusFilter:
    """Temporal consensus and median filter for meter readout results.

    Buffers recent MeterResult instances to reject single-frame impulse
    anomalies (water drops, reflection glitches, transient occlusions)
    before updating MQTT and telemetry.
    """

    def __init__(self, window_size: int = 1) -> None:
        self.window_size = max(1, window_size)
        self._buffer: deque[MeterResult] = deque(maxlen=self.window_size)

    @property
    def is_enabled(self) -> bool:
        """Return True if temporal consensus filtering is active."""
        return self.window_size > 1

    @property
    def current_size(self) -> int:
        """Return number of results currently buffered."""
        return len(self._buffer)

    def clear(self) -> None:
        """Clear the internal reading buffer."""
        self._buffer.clear()

    def filter(self, latest: MeterResult) -> tuple[MeterResult, bool]:
        """Process the latest MeterResult through the temporal consensus filter.

        Args:
            latest: The freshly acquired MeterResult from inference.

        Returns:
            A tuple of (consensus_result, is_outlier), where:
            - consensus_result: The consensus MeterResult to publish.
            - is_outlier: True if the latest reading deviated from consensus.
        """
        if not self.is_enabled:
            return latest, False

        # If buffer is empty, initialize and accept first reading immediately
        if not self._buffer:
            self._buffer.append(latest)
            return latest, False

        # Handle isolated invalid frame suppression
        if not latest.valid:
            valid_buffered = [r for r in self._buffer if r.valid]
            if valid_buffered:
                # Surrounding buffer has valid reads; treat this frame as a transient failure
                self._buffer.append(latest)
                logger.warning(
                    "Poller consensus filter suppressed isolated invalid frame: %s",
                    latest.error or latest.warning or "invalid reading",
                )
                return valid_buffered[-1], True

        # Append latest result to ring buffer
        self._buffer.append(latest)

        # If buffer not yet full, accept latest during initial warmup
        if len(self._buffer) < self.window_size:
            return latest, False

        # Find consensus result across the window
        return self._compute_consensus(latest)

    def _compute_consensus(self, latest: MeterResult) -> tuple[MeterResult, bool]:
        """Compute median/majority result across the window for the primary meter."""
        valid_results = [r for r in self._buffer if r.valid]
        if len(valid_results) < 3:
            return latest, False

        # Determine target meter name (use 'total' if available, else first meter)
        meter_name = "total"
        sample_meter_names = [m.name for m in valid_results[0].meters]
        if meter_name not in sample_meter_names and sample_meter_names:
            meter_name = sample_meter_names[0]

        # Extract values for this meter across valid results
        meter_values_numeric: list[tuple[int, float]] = []
        meter_values_str: list[tuple[int, str]] = []

        for idx, res in enumerate(valid_results):
            for m in res.meters:
                if m.name == meter_name:
                    meter_values_str.append((idx, m.value))
                    try:
                        numeric_val = float(m.value)
                        meter_values_numeric.append((idx, numeric_val))
                    except (ValueError, TypeError):
                        pass
                    break

        # If numeric values are available across all valid results
        if len(meter_values_numeric) == len(valid_results):
            raw_floats = [v for _, v in meter_values_numeric]
            med_val = statistics.median(raw_floats)

            # Find result closest to median
            best_idx = min(
                meter_values_numeric,
                key=lambda item: abs(item[1] - med_val),
            )[0]
            consensus_result = valid_results[best_idx]

            # Check if latest deviates from median
            latest_val = None
            for m in latest.meters:
                if m.name == meter_name:
                    try:
                        latest_val = float(m.value)
                    except (ValueError, TypeError):
                        latest_val = None
                    break

            if latest_val is not None and abs(latest_val - med_val) > 1e-6:
                logger.info(
                    "Poller consensus filter: meter '%s' raw=%s differs from consensus=%s",
                    meter_name,
                    latest_val,
                    med_val,
                )
                return consensus_result, True
            return latest, False

        # Fallback to string majority voting
        if meter_values_str:
            counts = Counter(v for _, v in meter_values_str)
            most_common_val, count = counts.most_common(1)[0]
            # Find result with most common value
            best_idx = next(
                idx for idx, val in meter_values_str if val == most_common_val
            )
            consensus_result = valid_results[best_idx]

            latest_str = next(
                (m.value for m in latest.meters if m.name == meter_name), ""
            )
            if latest_str != most_common_val and count > 1:
                return consensus_result, True

        return latest, False
