"""Predecessor / adjacent-wheel evaluation.

These tests lock the current DigitizerProcessor behaviour, including the
branch that returns 9 whenever this wheel's fraction is below 0.5 and the
less-significant wheel's fraction is at or above 0.5.

List order for _evaluate_counters is most-significant first (same as meter
format). Evaluation walks the list in reverse so the last item has no
predecessor.
"""

import math

import pytest

from src.processor.digitizer import (
    DigitizerProcessor,
    INVALID_DIGIT,
    Meter,
    MeterConfig,
    MODEL_ANALOG,
    MODEL_ANALOG100,
    MODEL_DIGITAL,
    MODEL_DIGITAL100,
    ReadoutResult,
)


def _processor() -> DigitizerProcessor:
    return DigitizerProcessor()


def _analog_results(*values: float, model: str = MODEL_ANALOG) -> list[ReadoutResult]:
    return [
        ReadoutResult(name=f"analog{i}", value=value, model=model)
        for i, value in enumerate(values, start=1)
    ]


def _digital_results(*values: float, model: str = MODEL_DIGITAL) -> list[ReadoutResult]:
    return [
        ReadoutResult(name=f"digit{i}", value=value, model=model)
        for i, value in enumerate(values, start=1)
    ]


# ---------------------------------------------------------------------------
# _evaluate_wheel_counter — fractional quadrants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (0.00, 0),
        (0.49, 0),
        (0.50, 1),
        (4.49, 4),
        (4.50, 5),
        (9.49, 9),
        (9.50, 0),
        (9.99, 0),
    ],
)
def test_wheel_without_predecessor_rounds_half_up(number: float, expected: int) -> None:
    assert _processor()._evaluate_wheel_counter(number) == expected
    assert (
        _processor()._evaluate_wheel_counter(number, predecessor_value=None) == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # this frac >= 0.5, predecessor frac < 0.5 → (rounded_digit - 1) % 10
        (4.6, 0.3, 4),
        (4.5, 0.0, 4),
        (4.5, 0.49, 4),
        (0.5, 0.0, 0),
        (0.51, 2.2, 0),
        (5.5, 2.49, 5),
        (9.7, 1.2, 9),
        (9.5, 0.0, 9),
        (9.99, 0.1, 9),
        (8.6, 9.4, 8),
        # wrap: rounded digit is 0, then minus one → 9
        (9.6, 0.1, 9),
        (0.5, 9.0, 0),
    ],
)
def test_wheel_carry_down_when_this_past_half_and_predecessor_before_half(
    number: float, predecessor: float, expected: int
) -> None:
    assert (
        _processor()._evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # this frac < 0.5, predecessor frac >= 0.5 → always 9 (current behaviour)
        (4.3, 0.7, 9),
        (4.3, 0.5, 9),
        (4.49, 0.5, 9),
        (0.0, 9.9, 9),
        (0.49, 0.5, 9),
        (1.0, 5.5, 9),
        (5.2, 9.8, 9),
        (8.1, 0.9, 9),
        (9.49, 9.51, 9),
        (9.0, 0.5, 9),
        (2.2, 7.7, 9),
    ],
)
def test_wheel_returns_nine_when_this_before_half_and_predecessor_past_half(
    number: float, predecessor: float, expected: int
) -> None:
    assert (
        _processor()._evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # both fractions >= 0.5 → independently rounded digit
        (4.6, 0.7, 5),
        (4.5, 0.5, 5),
        (0.5, 0.5, 1),
        (9.6, 9.7, 0),
        (8.8, 1.9, 9),
        (5.5, 2.5, 6),
        # both fractions < 0.5 → independently rounded digit
        (4.3, 0.2, 4),
        (4.49, 0.49, 4),
        (0.0, 0.0, 0),
        (9.4, 1.1, 9),
        (5.2, 9.2, 5),
        (0.49, 9.49, 0),
    ],
)
def test_wheel_same_side_of_half_keeps_rounded_digit(
    number: float, predecessor: float, expected: int
) -> None:
    assert (
        _processor()._evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


def test_wheel_predecessor_digit_argument_is_ignored() -> None:
    result = _processor()._evaluate_counter(
        name="analog1",
        number=4.3,
        predecessor_digit=0,
        predecessor_value=0.7,
        model=MODEL_ANALOG,
    )
    assert result == 9


# ---------------------------------------------------------------------------
# _evaluate_counters — analog pairs (MSD first in the list)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("msd", "lsd", "expected_msd", "expected_lsd"),
    [
        (4.6, 0.3, "4", "0"),
        (4.5, 0.0, "4", "0"),
        (9.6, 0.1, "9", "0"),
        (0.5, 0.0, "0", "0"),
        (4.3, 0.7, "9", "1"),
        (0.0, 9.9, "9", "0"),
        (9.49, 9.51, "9", "0"),
        (4.6, 0.7, "5", "1"),
        (4.5, 0.5, "5", "1"),
        (4.3, 0.2, "4", "0"),
        (9.4, 1.1, "9", "1"),
        (0.49, 0.49, "0", "0"),
        (9.99, 9.99, "0", "0"),
    ],
)
def test_evaluate_counters_analog_pair(
    msd: float, lsd: float, expected_msd: str, expected_lsd: str
) -> None:
    result = _processor()._evaluate_counters(_analog_results(msd, lsd))
    assert result == {"analog1": expected_msd, "analog2": expected_lsd}


@pytest.mark.parametrize("model", [MODEL_ANALOG, MODEL_ANALOG100])
def test_evaluate_counters_analog_and_analog100_share_wheel_rules(model: str) -> None:
    result = _processor()._evaluate_counters(_analog_results(4.6, 0.3, model=model))
    assert result == {"analog1": "4", "analog2": "0"}

    result_nine = _processor()._evaluate_counters(
        _analog_results(4.3, 0.7, model=model)
    )
    assert result_nine == {"analog1": "9", "analog2": "1"}


def test_evaluate_counters_three_analog_wheels_carry_down_chain() -> None:
    # LSD 0.2 < 0.5 so analog2 (4.6) carry-down 5→4; analog1 sees pred 4.6
    # (both >= 0.5) so stays rounded 4.
    result = _processor()._evaluate_counters(_analog_results(3.6, 4.6, 0.2))
    assert result == {"analog1": "4", "analog2": "4", "analog3": "0"}


def test_evaluate_counters_three_analog_wheels_return_nine_on_middle() -> None:
    # analog3 9.8 rounds to 0 and frac >= 0.5 → analog2 returns 9;
    # analog1 3.2 with pred 4.2 (frac < 0.5) stays 3.
    result = _processor()._evaluate_counters(_analog_results(3.2, 4.2, 9.8))
    assert result == {"analog1": "3", "analog2": "9", "analog3": "0"}


def test_evaluate_counters_four_analog_wheels_mixed_rules() -> None:
    result = _processor()._evaluate_counters(_analog_results(1.6, 2.3, 3.6, 0.2))
    # analog4: 0
    # analog3: 3.6 vs 0.2 → carry-down 4→3
    # analog2: 2.3 vs 3.6 → return 9
    # analog1: 1.6 vs 2.3 → carry-down 2→1
    assert result == {
        "analog1": "1",
        "analog2": "9",
        "analog3": "3",
        "analog4": "0",
    }


def test_evaluate_counters_model_change_resets_predecessor() -> None:
    values = [
        ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG100),
    ]
    result = _processor()._evaluate_counters(values)
    # analog2 evaluated first with no predecessor (round 0.3 → 0).
    # analog1 is a different model so predecessor is cleared; 4.6 rounds to 5.
    assert result == {"analog1": "5", "analog2": "0"}


def test_evaluate_counters_same_model_does_not_reset_predecessor() -> None:
    values = [
        ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG),
    ]
    result = _processor()._evaluate_counters(values)
    assert result == {"analog1": "4", "analog2": "0"}


# ---------------------------------------------------------------------------
# Digital classic — predecessor value is unused
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("msd", "lsd", "expected_msd", "expected_lsd"),
    [
        (1, 2, "1", "2"),
        (5, 9.9, "5", "9"),
        (0, 0.7, "0", "0"),
        (9, 0.0, "9", "0"),
    ],
)
def test_evaluate_counters_digital_ignores_predecessor_value(
    msd: float, lsd: float, expected_msd: str, expected_lsd: str
) -> None:
    result = _processor()._evaluate_counters(
        _digital_results(msd, lsd, model=MODEL_DIGITAL)
    )
    assert result == {"digit1": expected_msd, "digit2": expected_lsd}


def test_evaluate_counters_digital_invalid_with_predecessor() -> None:
    result = _processor()._evaluate_counters(
        _digital_results(10, 5.0, model=MODEL_DIGITAL)
    )
    assert result == {"digit1": INVALID_DIGIT, "digit2": "5"}

    result_neg = _processor()._evaluate_counters(
        _digital_results(-1, 9.0, model=MODEL_DIGITAL)
    )
    assert result_neg == {"digit1": INVALID_DIGIT, "digit2": "9"}


def test_evaluate_counters_digital_and_analog_are_independent_groups() -> None:
    values = [
        ReadoutResult(name="digit1", value=4, model=MODEL_DIGITAL),
        ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG),
    ]
    result = _processor()._evaluate_counters(values)
    assert result == {"digit1": "4", "analog1": "4", "analog2": "0"}


def test_evaluate_counters_analog_then_digital_does_not_feed_predecessor() -> None:
    values = [
        ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        ReadoutResult(name="digit1", value=1.6, model=MODEL_DIGITAL100),
    ]
    result = _processor()._evaluate_counters(values)
    # digit1 evaluated first (no pred) → floor(1.6) = 1
    # analog1 different model → 4.6 rounds to 5
    assert result == {"analog1": "5", "digit1": "1"}


# ---------------------------------------------------------------------------
# Digital100 — predecessor presence switches floor vs round-half-up
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (0.0, 0),
        (0.9, 0),
        (1.0, 1),
        (1.4, 1),
        (1.5, 1),
        (1.9, 1),
        (9.0, 9),
        (9.9, 9),
        (10.0, 0),
        (99.9, 9),
    ],
)
def test_digital100_without_predecessor_uses_floor(
    number: float, expected: int
) -> None:
    result = _processor()._evaluate_digital_counter(
        name="digit1",
        number=number,
        predecessor_value=None,
        model=MODEL_DIGITAL100,
    )
    assert result == expected


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        (1.4, 0.0, 1),
        (1.5, 0.0, 2),
        (1.6, 9.9, 2),
        (9.4, 1.0, 9),
        (9.5, 1.0, 0),
        (9.6, 0.1, 0),
        (0.49, 5.0, 0),
        (0.5, 5.0, 1),
        (99.4, 0.0, 9),
        (99.5, 0.0, 0),
        # predecessor value itself is ignored; any non-None enables rounding
        (1.6, 0.0, 2),
        (1.6, 99.9, 2),
        (1.4, 99.9, 1),
    ],
)
def test_digital100_with_predecessor_uses_round_half_up(
    number: float, predecessor: float, expected: int
) -> None:
    result = _processor()._evaluate_digital_counter(
        name="digit1",
        number=number,
        predecessor_value=predecessor,
        model=MODEL_DIGITAL100,
    )
    assert result == expected


@pytest.mark.parametrize(
    "number",
    [float("nan"), -0.1, -1.0, 100.0, 100.1, 150.0],
)
def test_digital100_invalid_values(number: float) -> None:
    result = _processor()._evaluate_digital_counter(
        name="digit1",
        number=number,
        predecessor_value=5.0,
        model=MODEL_DIGITAL100,
    )
    assert result == INVALID_DIGIT


def test_evaluate_counters_digital100_lsd_floors_msd_rounds() -> None:
    result = _processor()._evaluate_counters(
        _digital_results(5.6, 4.4, 3.9, model=MODEL_DIGITAL100)
    )
    # digit3 (LSD): no pred → floor(3.9)=3
    # digit2: pred present → round 4.4→4
    # digit1: pred present → round 5.6→6
    assert result == {"digit1": "6", "digit2": "4", "digit3": "3"}


def test_evaluate_counters_digital100_single_digit_floors() -> None:
    result = _processor()._evaluate_counters(
        _digital_results(5.6, model=MODEL_DIGITAL100)
    )
    assert result == {"digit1": "5"}


def test_evaluate_counters_digital100_nan_in_chain() -> None:
    result = _processor()._evaluate_counters(
        [
            ReadoutResult(name="digit1", value=1.6, model=MODEL_DIGITAL100),
            ReadoutResult(name="digit2", value=math.nan, model=MODEL_DIGITAL100),
        ]
    )
    assert result == {"digit1": "2", "digit2": INVALID_DIGIT}


# ---------------------------------------------------------------------------
# evaluate_cnn_results does not apply predecessor correction
# ---------------------------------------------------------------------------


def test_evaluate_cnn_results_ignores_predecessor_for_analog() -> None:
    processor = _processor()
    processor.cnn_analog_results = _analog_results(4.6, 0.3)
    processor.cnn_digital_results = []
    processor.evaluate_cnn_results()
    # Independent rounding: 4.6→5, 0.3→0. Contrast with _evaluate_counters → 4, 0.
    assert processor.available_values == {"analog1": 5, "analog2": 0}
    assert processor._evaluate_counters(processor.cnn_analog_results) == {
        "analog1": "4",
        "analog2": "0",
    }


def test_evaluate_cnn_results_digital100_always_floors() -> None:
    processor = _processor()
    processor.cnn_digital_results = _digital_results(5.6, 4.4, model=MODEL_DIGITAL100)
    processor.cnn_analog_results = []
    processor.evaluate_cnn_results()
    assert processor.available_values == {"digit1": 5, "digit2": 4}
    assert processor._evaluate_counters(processor.cnn_digital_results) == {
        "digit1": "6",
        "digit2": "4",
    }


# ---------------------------------------------------------------------------
# Post-processing uses _evaluate_counters (predecessor applied)
# ---------------------------------------------------------------------------


def _analog_meter() -> Meter:
    return Meter(
        config=MeterConfig(
            name="meter1",
            format="{analog1}{analog2}",
            unit="m3",
            consistency_enabled=False,
            use_extended_resolution=False,
            use_previous_value=False,
            pre_value_from_file_max_age=0,
            allow_negative_rates=False,
            max_rate_value=0.0,
        ),
        name="meter1",
        value="",
        unprocessed_value="",
    )


def test_postprocess_applies_analog_carry_down() -> None:
    meter = _analog_meter()
    cnn = {
        "analog1": ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG),
    }
    _processor()._postprocess_meter_value(meter, {}, cnn)
    assert meter.value == "40"


def test_postprocess_applies_analog_return_nine_rule() -> None:
    meter = _analog_meter()
    cnn = {
        "analog1": ReadoutResult(name="analog1", value=4.3, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=0.7, model=MODEL_ANALOG),
    }
    _processor()._postprocess_meter_value(meter, {}, cnn)
    assert meter.value == "91"


def test_postprocess_mixed_digital_and_analog_predecessor() -> None:
    meter = Meter(
        config=MeterConfig(
            name="meter1",
            format="{digit1}{digit2}.{analog1}{analog2}",
            unit="m3",
            consistency_enabled=False,
            use_extended_resolution=False,
            use_previous_value=False,
            pre_value_from_file_max_age=0,
            allow_negative_rates=False,
            max_rate_value=0.0,
        ),
        name="meter1",
        value="",
        unprocessed_value="",
    )
    cnn = {
        "digit1": ReadoutResult(name="digit1", value=1.6, model=MODEL_DIGITAL100),
        "digit2": ReadoutResult(name="digit2", value=2.4, model=MODEL_DIGITAL100),
        "analog1": ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG),
    }
    _processor()._postprocess_meter_value(meter, {}, cnn)
    # digit2 floor 2; digit1 rounds because pred exists → 2; analog 4.6/0.3 → 40
    assert meter.value == "22.40"


def test_postprocess_extended_resolution_uses_raw_last_wheel() -> None:
    meter = _analog_meter()
    meter.config.format = "{analog1}{analog2}"
    meter.config.use_extended_resolution = True
    cnn = {
        "analog1": ReadoutResult(name="analog1", value=4.6, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=0.3, model=MODEL_ANALOG),
    }
    _processor()._postprocess_meter_value(meter, {}, cnn)
    # value "40" plus floor(0.3 * 10) % 10 = 3
    assert meter.value == "403"
