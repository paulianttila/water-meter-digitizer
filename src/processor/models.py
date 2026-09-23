"""Data models and constants for digitizer processing pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from data_classes import MeterConfig

DEFAULT_MIN_CONFIDENCE_THRESHOLD = 60.0
MIN_CONFIDENCE_THRESHOLD = DEFAULT_MIN_CONFIDENCE_THRESHOLD
MODEL_AUTO = "auto"

QUALITY_HIGH_MIN_CONFIDENCE = 80.0
QUALITY_HIGH_AVG_CONFIDENCE = 85.0
QUALITY_WARNING_MIN_CONFIDENCE = 60.0
QUALITY_WARNING_AVG_CONFIDENCE = 65.0


class ReadoutResult(BaseModel):
    name: str
    value: float | str
    model: str
    confidence: float = 100.0


class MeterValue(BaseModel):
    name: str
    value: str
    unit: str = ""
    quality: Literal["good", "warning", "uncertain"] = "good"
    confidence: float = 100.0
    min_confidence: float = 100.0
    filled_digits: int = 0
    warning: str = ""
    valid: bool = True


class MeterResult(BaseModel):
    meters: list[MeterValue] = Field(default_factory=list)
    digital_results: dict[str, str] = Field(default_factory=dict)
    analog_results: dict[str, str] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    error: str = ""
    warning: str = ""
    valid: bool = True


class Meter(BaseModel):
    config: MeterConfig
    name: str = ""
    value: str = ""  # value after postprocessing
    unprocessed_value: str = ""  # value without postprocessing
    previous_value: str = ""
    previous_value_last_change: str = ""
    warning: str = ""
    valid: bool = True
    filled_digits: int = 0
