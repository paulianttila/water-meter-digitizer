"""Unit tests for ConsensusFilter temporal consensus and median filter."""

from processor.digitizer import MeterResult, MeterValue
from services.poller.consensus import ConsensusFilter


def _make_result(value: str, valid: bool = True, error: str = "") -> MeterResult:
    return MeterResult(
        meters=[MeterValue(name="main", value=value, valid=valid)],
        digital_results={},
        analog_results={},
        error=error,
        valid=valid,
    )


def test_consensus_filter_disabled():
    filter_ = ConsensusFilter(window_size=1)
    assert not filter_.is_enabled
    assert filter_.current_size == 0

    res = _make_result("50.0")
    consensus_res, is_outlier = filter_.filter(res)
    assert consensus_res == res
    assert not is_outlier
    assert filter_.current_size == 0


def test_consensus_filter_warmup():
    filter_ = ConsensusFilter(window_size=3)
    assert filter_.is_enabled

    r1 = _make_result("50.0")
    out1, is_outlier1 = filter_.filter(r1)
    assert out1 == r1
    assert not is_outlier1
    assert filter_.current_size == 1

    r2 = _make_result("50.1")
    out2, is_outlier2 = filter_.filter(r2)
    assert out2 == r2
    assert not is_outlier2
    assert filter_.current_size == 2


def test_consensus_filter_outlier_suppression_numeric():
    filter_ = ConsensusFilter(window_size=3)

    r1 = _make_result("50.0")
    r2 = _make_result("50.0")
    filter_.filter(r1)
    filter_.filter(r2)

    # Spike anomaly: 999.0 instead of 50.0
    r_spike = _make_result("999.0")
    out_spike, is_outlier = filter_.filter(r_spike)
    assert is_outlier is True
    # Consensus returns the median reading (50.0)
    assert out_spike.meters[0].value == "50.0"

    # Legitimate advance after spike: 50.1
    # Buffer is now [50.0, 999.0, 50.1] -> median is 50.1
    r_next = _make_result("50.1")
    out_next, is_outlier_next = filter_.filter(r_next)
    assert out_next.meters[0].value == "50.1"
    assert is_outlier_next is False


def test_consensus_filter_isolated_invalid_suppression():
    filter_ = ConsensusFilter(window_size=3)

    r1 = _make_result("50.0")
    r2 = _make_result("50.0")
    filter_.filter(r1)
    filter_.filter(r2)

    # 3rd read suffers optical glitch (e.g. droplet causing OCR failure)
    r_bad = _make_result("0.0", valid=False, error="OCR recognition failed")
    out_bad, is_outlier = filter_.filter(r_bad)

    # Suppressed; returns previous valid consensus
    assert is_outlier is True
    assert out_bad.valid is True
    assert out_bad.meters[0].value == "50.0"

    # 4th read is valid
    r4 = _make_result("50.1")
    out4, is_outlier4 = filter_.filter(r4)
    assert out4.valid is True
    assert out4.meters[0].value in ("50.0", "50.1")
    assert is_outlier4 is False


def test_consensus_filter_string_majority():
    filter_ = ConsensusFilter(window_size=3)

    r1 = _make_result("ABC")
    r2 = _make_result("ABC")
    filter_.filter(r1)
    filter_.filter(r2)

    r3 = _make_result("XYZ")
    out3, is_outlier3 = filter_.filter(r3)
    assert is_outlier3 is True
    assert out3.meters[0].value == "ABC"


def test_consensus_filter_clear():
    filter_ = ConsensusFilter(window_size=3)
    filter_.filter(_make_result("50.0"))
    assert filter_.current_size == 1

    filter_.clear()
    assert filter_.current_size == 0
