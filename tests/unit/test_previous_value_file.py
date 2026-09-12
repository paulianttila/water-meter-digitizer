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
