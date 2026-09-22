"""Unit tests for RolloverCorrector 0<->9 boundary transitions, wheel heuristics, and multi-drum rollover chains."""

import pytest

from data_classes import INVALID_DIGIT
from processor.digitizer import ReadoutResult
from processor.rollover_corrector import (
    MODEL_ANALOG,
    MODEL_DIGITAL,
    MODEL_DIGITAL100,
    RolloverCorrector,
)

# ============================================================================
# 1. evaluate_wheel_counter: Standalone (No Predecessor)
# ============================================================================


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (0.0, 0),
        (0.49, 0),
        (0.50, 1),
        (0.99, 1),
        (1.0, 1),
        (1.49, 1),
        (1.50, 2),
        (8.49, 8),
        (8.50, 9),
        (9.0, 9),
        (9.49, 9),
        (9.50, 0),  # wrap-around to 0
        (9.99, 0),
    ],
)
def test_wheel_without_predecessor_half_up(number: float, expected: int) -> None:
    assert RolloverCorrector.evaluate_wheel_counter(number) == expected
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=None)
        == expected
    )


# ============================================================================
# 2. evaluate_wheel_counter: Four Quadrant Transitions (0 <-> 9 Rollover Focus)
# ============================================================================


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # Q1: Both frac < 0.5 -> direct rounded digit
        (0.1, 0.2, 0),
        (0.2, 0.1, 0),
        (0.49, 0.49, 0),
        (9.1, 0.2, 9),
        (9.4, 0.3, 9),
        (5.2, 3.1, 5),
        (1.0, 0.0, 1),
    ],
)
def test_wheel_q1_both_fractions_below_half(
    number: float, predecessor: float, expected: int
) -> None:
    """Q1: Neither current nor predecessor is in rolling transition."""
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # Q2: Both frac >= 0.5 -> direct rounded digit
        (9.8, 9.9, 0),  # 9.8 rounds to 10 % 10 = 0
        (9.6, 9.7, 0),
        (0.8, 9.8, 1),
        (8.9, 9.7, 9),
        (5.7, 4.8, 6),
        (4.5, 0.5, 5),
    ],
)
def test_wheel_q2_both_fractions_above_half(
    number: float, predecessor: float, expected: int
) -> None:
    """Q2: Both current drum and predecessor have rolled past mid-point."""
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # Q3: Current frac >= 0.5, predecessor frac < 0.5 -> (digit - 1) % 10
        # Predecessor has just crossed 0 (e.g. 0.1), while current drum is seen as 9.9
        (9.9, 0.1, 9),  # rounded=0, decremented -> 9
        (9.8, 0.2, 9),
        (9.5, 0.0, 9),
        (0.9, 0.1, 0),  # rounded=1, decremented -> 0
        (0.5, 0.0, 0),
        (5.8, 0.2, 5),  # rounded=6, decremented -> 5
        (4.9, 0.0, 4),
        (4.5, 0.49, 4),
    ],
)
def test_wheel_q3_carry_down_predecessor_just_crossed_zero(
    number: float, predecessor: float, expected: int
) -> None:
    """Q3: Predecessor rolled past 0 (< 0.5), upper drum still showing trailing half (>= 0.5)."""
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        # Q4: Current frac < 0.5, predecessor frac >= 0.5 -> resolves to 9
        # Predecessor approaching rollover (e.g. 9.8), upper drum prematurely creeping (e.g. 0.1)
        (0.1, 9.8, 9),  # classic 0->9 pre-roll boundary
        (0.0, 9.9, 9),
        (0.2, 9.7, 9),
        (0.49, 9.5, 9),
        (0.1, 0.9, 9),
        (4.3, 0.7, 9),
        (5.1, 9.8, 9),
    ],
)
def test_wheel_q4_predecessor_approaching_rollover_holds_prior_decade(
    number: float, predecessor: float, expected: int
) -> None:
    """Q4: Predecessor drum >= 0.5 approaching rollover; hold 9 until complete."""
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


# ============================================================================
# 3. Boundary & Mid-Roll Thresholds (x.49, x.50, x.51)
# ============================================================================


@pytest.mark.parametrize(
    ("number", "predecessor", "expected"),
    [
        (9.49, 0.49, 9),  # both < 0.5 -> direct round(9.49) = 9
        (9.50, 0.49, 9),  # num >= 0.5, pred < 0.5 -> (round(9.5)-1)%10 = 9
        (9.50, 0.50, 0),  # both >= 0.5 -> direct round(9.5) = 0
        (0.49, 9.50, 9),  # num < 0.5, pred >= 0.5 -> 9
        (0.50, 9.50, 1),  # both >= 0.5 -> direct round(0.5) = 1
    ],
)
def test_wheel_exact_boundary_thresholds(
    number: float, predecessor: float, expected: int
) -> None:
    assert (
        RolloverCorrector.evaluate_wheel_counter(number, predecessor_value=predecessor)
        == expected
    )


# ============================================================================
# 4. evaluate_digital_counter: Models and Error Handling
# ============================================================================


def test_evaluate_digital_counter_standard_model():
    # Valid digits
    for i in range(10):
        assert (
            RolloverCorrector.evaluate_digital_counter("d1", i, model=MODEL_DIGITAL)
            == i
        )
        assert (
            RolloverCorrector.evaluate_digital_counter(
                "d1", float(i), model=MODEL_DIGITAL
            )
            == i
        )

    # Hyphen pass-through
    assert (
        RolloverCorrector.evaluate_digital_counter("d1", "-", model=MODEL_DIGITAL)
        == "-"
    )

    # Out of range / invalid
    assert (
        RolloverCorrector.evaluate_digital_counter("d1", -1, model=MODEL_DIGITAL)
        == INVALID_DIGIT
    )
    assert (
        RolloverCorrector.evaluate_digital_counter("d1", 10, model=MODEL_DIGITAL)
        == INVALID_DIGIT
    )
    assert (
        RolloverCorrector.evaluate_digital_counter("d1", "invalid", model=MODEL_DIGITAL)
        == INVALID_DIGIT
    )


def test_evaluate_digital_counter_model100():
    # Model 100 uses floor when no predecessor
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 4.8, model=MODEL_DIGITAL100, predecessor_value=None
        )
        == 4
    )
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 9.9, model=MODEL_DIGITAL100, predecessor_value=None
        )
        == 9
    )

    # Model 100 uses round-half-up when predecessor is provided
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 4.4, model=MODEL_DIGITAL100, predecessor_value=2.0
        )
        == 4
    )
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 4.6, model=MODEL_DIGITAL100, predecessor_value=2.0
        )
        == 5
    )
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 9.8, model=MODEL_DIGITAL100, predecessor_value=2.0
        )
        == 0
    )

    # Out-of-bounds or NaN
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", float("nan"), model=MODEL_DIGITAL100
        )
        == INVALID_DIGIT
    )
    assert (
        RolloverCorrector.evaluate_digital_counter("d100", -0.5, model=MODEL_DIGITAL100)
        == INVALID_DIGIT
    )
    assert (
        RolloverCorrector.evaluate_digital_counter(
            "d100", 100.0, model=MODEL_DIGITAL100
        )
        == INVALID_DIGIT
    )


def test_evaluate_digital_counter_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown digital model"):
        RolloverCorrector.evaluate_digital_counter("d1", 5, model="unknown_model")


# ============================================================================
# 5. evaluate_counter & evaluate_counters: Chained Sequences
# ============================================================================


def test_evaluate_counter_dispatch():
    # Analog dispatches to wheel evaluation
    assert (
        RolloverCorrector.evaluate_counter(
            name="a1",
            number=0.1,
            predecessor_digit=None,
            model=MODEL_ANALOG,
            predecessor_value=9.8,
        )
        == 9
    )

    # Digital dispatches to digital evaluation
    assert (
        RolloverCorrector.evaluate_counter(
            name="d1",
            number=5,
            predecessor_digit=None,
            model=MODEL_DIGITAL,
        )
        == 5
    )

    # Hyphen
    assert (
        RolloverCorrector.evaluate_counter(
            name="d1",
            number="-",
            predecessor_digit=None,
            model=MODEL_DIGITAL,
        )
        == "-"
    )

    # Unknown model
    with pytest.raises(ValueError, match="Unknown model"):
        RolloverCorrector.evaluate_counter(
            name="x",
            number=1,
            predecessor_digit=None,
            model="unsupported",
        )


def test_evaluate_counters_chained_rollover_sequence():
    """Verify multi-dial rollover where lower drum is at 9.8 and upper drum at 0.1."""
    readouts = [
        ReadoutResult(
            name="digit_tens", value=0.1, model=MODEL_ANALOG, confidence=95.0
        ),
        ReadoutResult(
            name="digit_units", value=9.8, model=MODEL_ANALOG, confidence=95.0
        ),
    ]

    evaluated = RolloverCorrector.evaluate_counters(readouts)
    # digit_units has no predecessor -> direct round(9.8) = 0
    assert evaluated["digit_units"] == "0"
    # digit_tens has predecessor 9.8 -> (0.1, pred=9.8) resolves to 9
    assert evaluated["digit_tens"] == "9"


def test_evaluate_counters_low_confidence_yields_invalid_digit():
    readouts = [
        ReadoutResult(name="d1", value=5, model=MODEL_DIGITAL, confidence=40.0),
        ReadoutResult(name="d2", value=7, model=MODEL_DIGITAL, confidence=95.0),
    ]

    evaluated = RolloverCorrector.evaluate_counters(
        readouts, min_confidence_threshold=60.0
    )
    assert evaluated["d1"] == INVALID_DIGIT
    assert evaluated["d2"] == "7"


def test_evaluate_counters_model_switch_resets_predecessor():
    """When switching between analog and digital models, predecessor tracking resets."""
    readouts = [
        ReadoutResult(name="d1", value=0.1, model=MODEL_DIGITAL100, confidence=95.0),
        ReadoutResult(name="a1", value=9.8, model=MODEL_ANALOG, confidence=95.0),
    ]

    evaluated = RolloverCorrector.evaluate_counters(readouts)
    # a1 evaluated first (in reverse): predecessor=None -> direct round(9.8) = 0
    assert evaluated["a1"] == "0"
    # d1 has different model (digital100 vs analog): predecessor resets to None
    # For digital100 with pred=None, math.floor(0.1)%10 = 0
    assert evaluated["d1"] == "0"
