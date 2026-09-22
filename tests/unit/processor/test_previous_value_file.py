"""Unit tests for atomic previous value persistence in prevalue.ini."""

import pytest

from previous_value import (
    get_all_previous_values,
    load_previous_value_from_file,
    save_previous_value_to_file,
)


def test_prevvalue():
    value = load_previous_value_from_file(
        "tests/unit/resource/prevalue-ok.ini", "total", 0
    )
    assert value == "12345.6789"


def test_prevvalue_aged():
    with pytest.raises(ValueError):
        load_previous_value_from_file(
            "tests/unit/resource/prevalue-ok.ini", "total", 60
        )


def test_not_existing_config_file():
    with pytest.raises(ValueError):
        load_previous_value_from_file("tests/unit/resource/not-exists.ini", "total", 0)


def test_save_prevvalue(tmp_path):
    temp_file = str(tmp_path / "prevalue.ini")
    save_previous_value_to_file(temp_file, "total", "98765.4321")
    value = load_previous_value_from_file(temp_file, "total", 0)
    assert value == "98765.4321"


def test_save_prevvalue_multiple(tmp_path):
    temp_file = str(tmp_path / "prevalue.ini")
    save_previous_value_to_file(temp_file, "testing", "123456.789")
    save_previous_value_to_file(temp_file, "total", "98765.4321")
    value_testing = load_previous_value_from_file(temp_file, "testing", 0)
    value_total = load_previous_value_from_file(temp_file, "total", 0)
    assert value_testing == "123456.789"
    assert value_total == "98765.4321"

    # Test get_all_previous_values
    all_values = get_all_previous_values(temp_file)
    assert "testing" in all_values
    assert all_values["testing"]["value"] == "123456.789"
    assert "total" in all_values
    assert all_values["total"]["value"] == "98765.4321"


def test_get_all_previous_values_not_found(tmp_path):
    missing_file = str(tmp_path / "missing.ini")
    assert get_all_previous_values(missing_file) == {}


def test_get_all_previous_values_corrupted(tmp_path):
    corrupted_file = tmp_path / "corrupted.ini"
    corrupted_file.write_text("NOT A VALID INI FILE === [[[]]]")
    assert get_all_previous_values(str(corrupted_file)) == {}


def test_timestamp_formats_iso_and_legacy(tmp_path):
    from datetime import datetime

    # 1. ISO format timestamp
    iso_file = tmp_path / "iso_prevalue.ini"
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    iso_file.write_text(f"[total]\nTime = {now_iso}\nValue = 111.222\n")
    assert (
        load_previous_value_from_file(str(iso_file), "total", max_age_minutes=5)
        == "111.222"
    )

    # 2. Legacy dot format timestamp
    legacy_file = tmp_path / "legacy_prevalue.ini"
    now_dot = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    legacy_file.write_text(f"[total]\nTime = {now_dot}\nValue = 333.444\n")
    assert (
        load_previous_value_from_file(str(legacy_file), "total", max_age_minutes=5)
        == "333.444"
    )

    # 3. Invalid timestamp format error
    invalid_file = tmp_path / "invalid_prevalue.ini"
    invalid_file.write_text("[total]\nTime = INVALID_TIME\nValue = 555.666\n")
    with pytest.raises(ValueError, match="Error occured during previous value loading"):
        load_previous_value_from_file(str(invalid_file), "total", max_age_minutes=5)


def test_atomic_save_writes_iso_timestamp(tmp_path):
    temp_file = tmp_path / "atomic_test.ini"
    save_previous_value_to_file(str(temp_file), "main", "42.0")
    assert temp_file.exists()
    assert not (tmp_path / "atomic_test.ini.tmp").exists()

    assert load_previous_value_from_file(str(temp_file), "main") == "42.0"
    content = temp_file.read_text()
    assert "value = 42.0" in content
    assert "T" in content  # ISO-8601 has 'T' between date and time


def test_save_previous_value_rejects_invalid_digit(tmp_path):
    temp_file = tmp_path / "reject_invalid.ini"
    with pytest.raises(
        ValueError, match="Cannot save previous value containing invalid digit"
    ):
        save_previous_value_to_file(str(temp_file), "total", "12?4.5")
    assert not temp_file.exists()


def test_load_previous_value_rejects_invalid_digit(tmp_path):
    invalid_file = tmp_path / "has_invalid_digit.ini"
    invalid_file.write_text("[total]\nTime = 2026-09-22T12:00:00\nValue = 12?4.5\n")
    with pytest.raises(ValueError, match="contains invalid digit"):
        load_previous_value_from_file(str(invalid_file), "total")
