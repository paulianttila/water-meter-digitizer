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


def test_consistency_validator_zero_max_rate_disables_rate_limit():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=0.0,
    )
    # With max_rate_value=0.0, rate-of-change check is disabled; large delta passes cleanly
    ConsistencyValidator.validate_reading(config, "200.0", "100.0")


def test_consistency_validator_zero_max_rate_still_enforces_negative_rate():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=0.0,
    )
    # Negative rate rejection is independent of max_rate_value
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(config, "99.0", "100.0")

    assert "Negative rate (-1.000)" in str(exc_info.value)


def test_serializer_warns_when_consistency_enabled_with_zero_max_rate(caplog):
    from configuration import Config

    ini_content = """
    [Meters]
    Names = total

    [Meter.total]
    ConsistencyEnabled = True
    MaxRateValue = 0.0
    """
    with caplog.at_level("WARNING"):
        Config().load_from_string(ini_content)

    assert (
        "Rate-of-change check is disabled; only negative-rate check will be enforced."
        in caplog.text
    )
    assert (
        "Meter 'total': ConsistencyEnabled is True but MaxRateValue is 0" in caplog.text
    )


def test_consistency_validator_zero_delta_allowed_with_min_rate():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
        min_rate_value=0.1,
        stale_threshold_hours=0.0,
    )
    # Zero consumption (delta = 0.0) is totally ok when stale_threshold_hours=0
    ConsistencyValidator.validate_reading(config, "100.0", "100.0")


def test_consistency_validator_rate_too_low():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
        min_rate_value=0.1,
    )
    # Delta = 0.05 > 0, but < min_rate_value 0.1 -> Rate too low
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(config, "100.05", "100.0")

    assert "Rate too low (0.050)" in str(exc_info.value)


def test_consistency_validator_stale_reading_exceeds_hours():
    from datetime import datetime

    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
        stale_threshold_hours=24.0,
    )
    # Delta = 0.0, unchanged for 26 hours >= 24.0 threshold -> Stale reading
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_reading(
            config,
            "100.0",
            "100.0",
            last_change_time="2026-09-20T10:00:00",
            current_time=datetime(2026, 9, 21, 12, 0, 0),
        )

    assert "Stale reading (no change for 26.0h)" in str(exc_info.value)


def test_consistency_validator_zero_delta_under_stale_threshold_passes():
    from datetime import datetime

    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
        stale_threshold_hours=24.0,
    )
    # Delta = 0.0, unchanged for only 12 hours < 24.0 threshold -> passes cleanly
    ConsistencyValidator.validate_reading(
        config,
        "100.0",
        "100.0",
        last_change_time="2026-09-21T00:00:00",
        current_time=datetime(2026, 9, 21, 12, 0, 0),
    )


def test_consistency_validator_min_rate_satisfied():
    config = MeterConfig(
        name="total",
        format="{digit1}",
        consistency_enabled=True,
        allow_negative_rates=False,
        max_rate_value=1.0,
        min_rate_value=0.1,
    )
    # Delta = 0.2 >= 0.1 -> passes
    ConsistencyValidator.validate_reading(config, "100.2", "100.0")


def test_consistency_validator_validate_stale_direct():
    from datetime import datetime

    # Disabled or None passes without error
    ConsistencyValidator.validate_stale(0.0, "2026-09-20T10:00:00")
    ConsistencyValidator.validate_stale(10.0, None)
    ConsistencyValidator.validate_stale(10.0, "invalid-date")

    # Within threshold passes
    ConsistencyValidator.validate_stale(
        24.0,
        "2026-09-21T00:00:00",
        current_time=datetime(2026, 9, 21, 10, 0, 0),
    )

    # Exceeding threshold raises ConsistencyError
    with pytest.raises(ConsistencyError) as exc_info:
        ConsistencyValidator.validate_stale(
            24.0,
            "2026-09-20T00:00:00",
            current_time=datetime(2026, 9, 21, 12, 0, 0),
        )
    assert "Stale reading (no change for 36.0h)" in str(exc_info.value)


def test_serializer_loads_min_rate_and_stale_threshold():
    from configuration import Config

    ini_content = """
    [Meters]
    Names = total

    [Meter.total]
    ConsistencyEnabled = True
    MaxRateValue = 0.5
    MinRateValue = 0.05
    StaleThresholdHours = 48.0
    """
    cfg = Config().load_from_string(ini_content)
    assert len(cfg.meter_configs) == 1
    assert cfg.meter_configs[0].min_rate_value == 0.05
    assert cfg.meter_configs[0].stale_threshold_hours == 48.0


def test_serializer_warns_when_min_rate_greater_than_max_rate(caplog):
    from configuration import Config

    ini_content = """
    [Meters]
    Names = total

    [Meter.total]
    ConsistencyEnabled = True
    MaxRateValue = 0.2
    MinRateValue = 0.5
    """
    with caplog.at_level("WARNING"):
        Config().load_from_string(ini_content)

    assert (
        "Meter 'total': MinRateValue (0.500) is greater than MaxRateValue (0.200)."
        in caplog.text
    )
