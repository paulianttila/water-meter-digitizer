"""Consistency and continuity validation for meter readouts."""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from data_classes import MeterConfig
from exceptions import ConsistencyValidationError

logger = logging.getLogger(__name__)


class ConsistencyError(ConsistencyValidationError):
    """Raised when a meter reading violates monotonicity, max rate, or sanity constraints."""


class ConsistencyValidator:
    """Validates meter reading continuity against past values and configuration rules."""

    @staticmethod
    def validate_reading(
        meter_config: MeterConfig,
        current_value: str,
        previous_value: str,
        last_change_time: str | datetime | None = None,
        current_time: datetime | None = None,
    ) -> None:
        """Verify that current value satisfies continuity, direction, and rate-of-change constraints."""
        if not current_value or not previous_value:
            return

        try:
            current = Decimal(current_value)
            previous = Decimal(previous_value)
        except InvalidOperation as err:
            raise ConsistencyError(
                f"Invalid value: {current_value} or {previous_value}"
            ) from err

        delta = current - previous

        if delta == 0:
            ConsistencyValidator.validate_stale(
                meter_config.stale_threshold_hours,
                last_change_time,
                current_time,
            )
            return

        if not meter_config.allow_negative_rates and delta < 0:
            raise ConsistencyError(f"Negative rate ({delta:.3f})")
        if meter_config.max_rate_value > 0 and abs(delta) > meter_config.max_rate_value:
            raise ConsistencyError(f"Rate too high ({delta:.3f})")
        if meter_config.min_rate_value > 0 and abs(delta) < meter_config.min_rate_value:
            raise ConsistencyError(f"Rate too low ({delta:.3f})")

    @staticmethod
    def validate_stale(
        stale_threshold_hours: float,
        last_change_time: str | datetime | None,
        current_time: datetime | None = None,
    ) -> None:
        """Verify reading is not stale when value has remained unchanged."""
        if stale_threshold_hours <= 0 or last_change_time is None:
            return

        if isinstance(last_change_time, str):
            try:
                last_change_dt = datetime.fromisoformat(last_change_time)
            except ValueError:
                last_change_dt = None
        else:
            last_change_dt = last_change_time

        if last_change_dt is not None:
            now = current_time or datetime.now()
            hours_unchanged = (now - last_change_dt).total_seconds() / 3600.0
            if hours_unchanged >= stale_threshold_hours:
                raise ConsistencyError(
                    f"Stale reading (no change for {hours_unchanged:.1f}h)"
                )
