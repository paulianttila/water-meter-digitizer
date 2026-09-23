"""Quality determination logic and threshold evaluation for digitizer readings."""

from __future__ import annotations

from typing import Literal

from processor.models import (
    QUALITY_HIGH_AVG_CONFIDENCE,
    QUALITY_HIGH_MIN_CONFIDENCE,
    QUALITY_WARNING_AVG_CONFIDENCE,
    QUALITY_WARNING_MIN_CONFIDENCE,
)
from processor.rollover_corrector import INVALID_DIGIT


def determine_quality(
    value: str,
    valid: bool,
    warning: str,
    min_conf: float,
    avg_conf: float,
    quality_high_min_confidence: float = QUALITY_HIGH_MIN_CONFIDENCE,
    quality_high_avg_confidence: float = QUALITY_HIGH_AVG_CONFIDENCE,
    quality_warning_min_confidence: float = QUALITY_WARNING_MIN_CONFIDENCE,
    quality_warning_avg_confidence: float = QUALITY_WARNING_AVG_CONFIDENCE,
) -> Literal["good", "warning", "uncertain"]:
    """Classify readout quality based on unreadable digits, warnings, validity, and confidence thresholds."""
    if INVALID_DIGIT in value:
        return "uncertain"
    elif warning:
        return "warning"
    elif not valid:
        return "uncertain"
    elif (
        min_conf >= quality_high_min_confidence
        and avg_conf >= quality_high_avg_confidence
    ):
        return "good"
    elif (
        min_conf >= quality_warning_min_confidence
        and avg_conf >= quality_warning_avg_confidence
    ):
        return "warning"
    else:
        return "uncertain"
