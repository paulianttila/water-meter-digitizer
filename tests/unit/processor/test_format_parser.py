"""Unit tests for FormatParser template extraction, formatting, and previous value adaptation."""

import logging

import pytest

from src.processor.format_parser import FormatParser


def test_extract_slots():
    """Verify placeholder slot extraction from template strings."""
    template = "{digit1}{digit2}.{analog1}{analog2}"
    slots = FormatParser.extract_slots(template)
    assert slots == ["digit1", "digit2", "analog1", "analog2"]


def test_extract_slots_empty():
    """Verify empty list returned when template contains no placeholders."""
    assert FormatParser.extract_slots("123.456") == []


def test_format_template_success():
    """Verify template values correctly substituted."""
    template = "{digit1}{digit2}.{analog1}"
    res = FormatParser.format_template(
        template, {"digit1": "1", "digit2": "2", "analog1": "3"}
    )
    assert res == "12.3"


def test_format_template_fallback_on_missing_key(caplog: pytest.LogCaptureFixture):
    """Verify fallback to raw format string on missing template placeholder."""
    template = "{digit1}{missing}"
    with caplog.at_level(logging.WARNING):
        res = FormatParser.format_template(template, {"digit1": "1"})
    assert res == template
    assert "Failed to format template" in caplog.text


def test_adapt_previous_value_equal_length():
    """Verify previous value unchanged when length matches current reading."""
    res = FormatParser.adapt_previous_value_to_match_length("12345", "98765")
    assert res == "98765"


def test_adapt_previous_value_pads_shorter_previous():
    """Verify previous value padded with ending zeros when shorter than current reading."""
    res = FormatParser.adapt_previous_value_to_match_length("12345.6", "123")
    assert res == "1230000"
    assert len(res) == len("12345.6")


def test_adapt_previous_value_truncates_longer_previous_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
):
    """Verify previous value truncated and warning logged when previous value is longer than current."""
    with caplog.at_level(logging.WARNING):
        res = FormatParser.adapt_previous_value_to_match_length("1234", "12345.67")
    assert res == "1234"
    assert (
        "Truncating previous value '12345.67' (len 8) to match new value '1234' (len 4)"
        in caplog.text
    )


def test_append_extended_digit():
    """Verify extended resolution fractional digit appending."""
    assert FormatParser.append_extended_digit("123", 4.56) == "1235"
    assert FormatParser.append_extended_digit("123", 4.01) == "1230"
    assert FormatParser.append_extended_digit("123", None) == "123"
    assert FormatParser.append_extended_digit("123", float("nan")) == "123"
    assert FormatParser.append_extended_digit("123", "invalid") == "123"
