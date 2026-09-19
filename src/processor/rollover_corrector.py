"""Rollover correction, mechanical odometer drum transitions, and zero-crossing heuristics."""

import logging
import math
from typing import Any

from data_classes import INVALID_DIGIT

logger = logging.getLogger(__name__)

MODEL_ANALOG = "analog"
MODEL_DIGITAL = "digital"
MODEL_ANALOG100 = "analog100"
MODEL_DIGITAL100 = "digital100"

ANALOG_MODELS = {MODEL_ANALOG, MODEL_ANALOG100}
DIGITAL_MODELS = {MODEL_DIGITAL, MODEL_DIGITAL100}


class RolloverCorrector:
    """Corrects physical odometer drum transitions and successor dial rollovers."""

    @staticmethod
    def evaluate_wheel_counter(
        number: float,
        predecessor_value: float | None = None,
    ) -> int:
        """Resolve rolling odometer wheel digit using predecessor drum state."""
        if predecessor_value is None:
            return math.floor(number + 0.5) % 10

        digit = math.floor(number + 0.5) % 10

        if number % 1 >= 0.5 and predecessor_value % 1 < 0.5:
            return (digit - 1) % 10

        if number % 1 < 0.5 and predecessor_value % 1 >= 0.5:
            return 9

        return digit

    @classmethod
    def evaluate_digital_counter(
        cls,
        name: str,
        number: float | int | str,
        predecessor_digit: int | None = None,
        predecessor_value: float | None = None,
        model: str = "",
    ) -> int | str:
        """Evaluate digital readout counter slot according to CNN classification model."""
        if number == "-":
            return "-"

        model = model.lower()

        if model == MODEL_DIGITAL:
            if isinstance(number, (int, float)) and (number < 0 or number >= 10):
                return INVALID_DIGIT
            return int(number) if isinstance(number, (int, float)) else INVALID_DIGIT

        if model == MODEL_DIGITAL100:
            if (
                not isinstance(number, (int, float))
                or math.isnan(number)
                or number < 0
                or number >= 100
            ):
                return INVALID_DIGIT
            if predecessor_value is None:
                return math.floor(number) % 10

            return math.floor(number + 0.5) % 10

        raise ValueError(f"Unknown digital model: {model}")

    @classmethod
    def evaluate_analog_counter(
        cls,
        name: str,
        number: float,
        predecessor_digit: int | None = None,
        predecessor_value: float | None = None,
        model: str = "",
    ) -> int:
        """Evaluate analog dial counter using wheel transition logic."""
        return cls.evaluate_wheel_counter(
            number=number,
            predecessor_value=predecessor_value,
        )

    @classmethod
    def evaluate_counter(
        cls,
        name: str,
        number: float | int | str,
        predecessor_digit: int | None,
        model: str,
        predecessor_value: float | None = None,
    ) -> int | str:
        """Evaluate single digit/dial counter based on its model family."""
        if number == "-":
            return "-"

        model = model.lower()
        digit: int | str
        if model in ANALOG_MODELS:
            digit = cls.evaluate_analog_counter(
                name=name,
                number=float(number),
                predecessor_digit=predecessor_digit,
                predecessor_value=predecessor_value,
                model=model,
            )
        elif model in DIGITAL_MODELS:
            digit = cls.evaluate_digital_counter(
                name=name,
                number=number,
                predecessor_digit=predecessor_digit,
                predecessor_value=predecessor_value,
                model=model,
            )
        else:
            raise ValueError(f"Unknown model: {model}")

        logger.debug(
            "Evaluate %s: %s (predecessor: %s, predecessor_value: %s) -> %s",
            name,
            number,
            predecessor_digit,
            predecessor_value,
            digit,
        )
        return digit

    @classmethod
    def evaluate_counters(
        cls,
        values: list[Any],
        min_confidence_threshold: float = 60.0,
    ) -> dict[str, str]:
        """Evaluate a chained list of ReadoutResult objects in reverse order with predecessor tracking."""
        predecessor_value: float | str | None = None
        predecessor_model: str | None = None
        evaluated: dict[str, str] = {}

        for result in reversed(values):
            model = result.model.lower()

            # A change of model means a new independent wheel group.
            if model != predecessor_model:
                predecessor_value = None

            if result.value == "-":
                digit: int | str = "-"
            elif result.confidence < min_confidence_threshold or (
                isinstance(result.value, float) and math.isnan(result.value)
            ):
                digit = INVALID_DIGIT
            else:
                pred_val = (
                    predecessor_value
                    if isinstance(predecessor_value, (int, float))
                    else None
                )
                digit = cls.evaluate_counter(
                    name=result.name,
                    number=result.value,
                    predecessor_digit=None,
                    predecessor_value=pred_val,
                    model=model,
                )

            evaluated[result.name] = str(digit)
            predecessor_value = result.value
            predecessor_model = model

        return evaluated
