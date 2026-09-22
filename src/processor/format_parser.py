"""Format template parsing, slot tokenization, and string assembly for meter readouts."""

import logging
import math
import re
from typing import Any

from utils.math import fill_value_with_ending_zeros

logger = logging.getLogger(__name__)


class FormatParser:
    """Utilities for parsing meter format strings and assembling structured values."""

    @staticmethod
    def extract_slots(format_str: str) -> list[str]:
        """Extract placeholder slot names (e.g. {digit1}, {analog1}) from format string."""
        return re.findall(r"\{([^}]+)\}", format_str)

    @staticmethod
    def format_template(format_str: str, values: dict[str, Any]) -> str:
        """Substitute values into template format string with graceful fallback."""
        try:
            return format_str.format(**values)
        except (KeyError, ValueError) as e:
            logger.warning(
                "Failed to format template '%s' with values %s: %s",
                format_str,
                values,
                e,
            )
            return format_str

    @staticmethod
    def adapt_previous_value_to_match_length(number: str, previous_value: str) -> str:
        """Align length of previous value string to match current readout length."""
        if len(number) > len(previous_value):
            logger.debug(
                "Fill previous value %s to match new value %s len",
                previous_value,
                number,
            )
            return fill_value_with_ending_zeros(len(number), previous_value)
        elif len(number) < len(previous_value):
            logger.warning(
                "Truncating previous value '%s' (len %d) to match new value '%s' (len %d)",
                previous_value,
                len(previous_value),
                number,
                len(number),
            )
            return previous_value[: len(number)]
        return previous_value

    @staticmethod
    def append_extended_digit(
        current_value: str, last_digit_value: float | str | None
    ) -> str:
        """Append decimal tenths fraction to least significant digit for extended resolution."""
        if (
            last_digit_value is None
            or isinstance(last_digit_value, str)
            or math.isnan(last_digit_value)
        ):
            return current_value
        decimal_digit = math.floor(last_digit_value * 10) % 10
        return f"{current_value}{decimal_digit}"
