"""Consistency and continuity validation for meter readouts."""

import logging
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
    ) -> None:
        """Verify that current value satisfies continuity, direction, and rate-of-change constraints."""
        try:
            current = Decimal(current_value)
            previous = Decimal(previous_value)
        except InvalidOperation as err:
            raise ConsistencyError(
                f"Invalid value: {current_value} or {previous_value}"
            ) from err

        delta = current - previous
        if not meter_config.allow_negative_rates and delta < 0:
            raise ConsistencyError(f"Negative rate ({delta:.3f})")
        if abs(delta) > meter_config.max_rate_value:
            raise ConsistencyError(f"Rate too high ({delta:.3f})")
