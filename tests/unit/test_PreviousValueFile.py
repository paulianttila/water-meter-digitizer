import os
import tempfile

import pytest
from src.PreviousValueFile import (
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
    temp_name = next(tempfile._get_candidate_names())
    save_previous_value_to_file(temp_name, "total", "98765.4321")
    value = load_previous_value_from_file(temp_name, "total", 0)
    os.remove(temp_name)
    assert value == "98765.4321"


def test_save_prevvalue_multiple(tmp_path):
    temp_name = next(tempfile._get_candidate_names())
    save_previous_value_to_file(temp_name, "testing", "123456.789")
    save_previous_value_to_file(temp_name, "total", "98765.4321")
    value_testing = load_previous_value_from_file(temp_name, "testing", 0)
    value_total = load_previous_value_from_file(temp_name, "total", 0)
    os.remove(temp_name)
    assert value_testing == "123456.789"
    assert value_total == "98765.4321"
