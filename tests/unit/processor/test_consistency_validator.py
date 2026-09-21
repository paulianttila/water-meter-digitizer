"""Unit tests for ConsistencyValidator and Continuity constraints."""

import pytest

from data_classes import MeterConfig
from processor.consistency_validator import ConsistencyError, ConsistencyValidator


def test_consistency_validator_valid_rate():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=0.5,
    )
    # 123.5 -> 123.8 (delta = 0.3 <= 0.5)
    ConsistencyValidator.validate_reading(config, "123.8", "123.5")


def test_consistency_validator_rate_too_high():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=0.2,
    )
    # 100.0 -> 101.5 (delta = 1.5 > 0.2)
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(config, "101.5", "100.0")

    assert "Rate too high (1.500)" in str(exc_info.value)


def test_consistency_validator_negative_rate_rejected():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
    )
    # 100.0 -> 99.5 (delta = -0.5 < 0)
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(config, "99.5", "100.0")

    assert "Negative rate (-0.500)" in str(exc_info.value)


def test_consistency_validator_negative_rate_allowed():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=True,
        max_rate_value=2.0,
    )
    # 100.0 -> 99.0 (delta = -1.0, abs <= 2.0)
    ConsistencyValidator.validate_reading(config, "99.0", "100.0")


def test_consistency_validator_invalid_values():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
    )
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(config, "123.?", "123.0")
    assert "Invalid value" in str(exc_info.value)


def test_consistency_validator_empty_values_skipped():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
    )
    # Empty string should return cleanly without error
    ConsistencyValidator.validate_reading(config, "123.4", "")
    ConsistencyValidator.validate_reading(config, "", "123.4")
    ConsistencyValidator.validate_reading(config, "", "")
