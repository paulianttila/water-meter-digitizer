"""Unit tests for CodeMirror syntax error decorations and line highlighting."""

import configparser

from gui.pages.config import (
    build_syntax_error_decorations,
    extract_syntax_error_info,
)
from gui.pages.config_field_registry import (
    SyntaxErrorInfo,
)
from gui.pages.config_field_registry import (
    build_syntax_error_decorations as registry_build_decorations,
)
from gui.pages.config_field_registry import (
    extract_syntax_error_info as registry_extract_info,
)


def test_import_equivalence():
    assert build_syntax_error_decorations is registry_build_decorations
    assert extract_syntax_error_info is registry_extract_info


def test_extract_missing_section_header_error():
    bad_ini = "key_without_section = 123\n[DEFAULT]\nloglevel = INFO\n"
    parser = configparser.ConfigParser()
    try:
        parser.read_string(bad_ini)
    except Exception as ex:
        err_info = extract_syntax_error_info(bad_ini, ex)
        assert isinstance(err_info, SyntaxErrorInfo)
        assert err_info.lineno == 1
        assert "missing section header" in err_info.message.lower()
        assert err_info.position == len("key_without_section = 123")


def test_extract_parsing_error():
    bad_ini = "[DEFAULT]\nloglevel = INFO\nthis is not a valid ini line\nport = 1883\n"
    parser = configparser.ConfigParser()
    try:
        parser.read_string(bad_ini)
    except Exception as ex:
        err_info = extract_syntax_error_info(bad_ini, ex)
        assert isinstance(err_info, SyntaxErrorInfo)
        assert err_info.lineno == 3
        assert "line 3" in str(ex).lower() or err_info.lineno == 3
        # Position is character offset at end of line 3
        expected_pos = (
            len("[DEFAULT]\n")
            + len("loglevel = INFO\n")
            + len("this is not a valid ini line")
        )
        assert err_info.position == expected_pos


def test_extract_duplicate_section_error():
    bad_ini = "[MQTT]\nhost = 192.168.1.1\n\n[MQTT]\nhost = 192.168.1.2\n"
    parser = configparser.ConfigParser(strict=True)
    try:
        parser.read_string(bad_ini)
    except Exception as ex:
        err_info = extract_syntax_error_info(bad_ini, ex)
        assert isinstance(err_info, SyntaxErrorInfo)
        assert err_info.lineno == 4
        assert "duplicatesectionerror" in err_info.message.lower()


def test_extract_duplicate_option_error():
    bad_ini = "[MQTT]\nhost = 192.168.1.1\nhost = 192.168.1.2\n"
    parser = configparser.ConfigParser(strict=True)
    try:
        parser.read_string(bad_ini)
    except Exception as ex:
        err_info = extract_syntax_error_info(bad_ini, ex)
        assert isinstance(err_info, SyntaxErrorInfo)
        assert err_info.lineno == 3
        assert "duplicateoptionerror" in err_info.message.lower()


def test_extract_generic_error_regex_fallback():
    ini = "line1\nline2\nline3\n"
    ex = ValueError("Error occurred near line 2 while parsing")
    err_info = extract_syntax_error_info(ini, ex)
    assert err_info.lineno == 2
    expected_pos = len("line1\n") + len("line2")
    assert err_info.position == expected_pos


def test_extract_generic_error_no_lineno():
    ini = "line1\nline2\n"
    ex = RuntimeError("Unknown failure without line number")
    err_info = extract_syntax_error_info(ini, ex)
    assert err_info.lineno == 1
    assert err_info.position == len("line1")
    assert "Unknown failure" in err_info.message


def test_build_syntax_error_decorations():
    bad_ini = "[DEFAULT]\nloglevel = INFO\n= broken line without key\n"
    parser = configparser.ConfigParser()
    try:
        parser.read_string(bad_ini)
    except Exception as ex:
        decorations, tooltips = build_syntax_error_decorations(bad_ini, ex)

        # Check decorations
        assert len(decorations) == 2
        line_dec = next(d for d in decorations if d.get("kind") == "line")
        widget_dec = next(d for d in decorations if d.get("kind") == "widget")

        assert line_dec["line"] == 3
        assert line_dec["class"] == "cm-error-line"

        assert widget_dec["position"] > 0
        assert "cm-error-widget" in widget_dec["class"]
        assert "❌" in widget_dec["text"]

        # Check line tooltips
        assert 3 in tooltips
        assert "❌ Syntax Error:" in tooltips[3]


def test_build_syntax_error_decorations_empty_text():
    ex = ValueError("Empty file error")
    decorations, tooltips = build_syntax_error_decorations("", ex)
    assert len(decorations) == 2
    assert decorations[0]["line"] == 1
    assert decorations[1]["position"] == 0
    assert 1 in tooltips


def test_find_ini_line_exact_key_in_section():
    from gui.pages.config import find_ini_line

    ini = """[DEFAULT]
loglevel = INFO

[MQTT]
host = 192.168.1.1
port = 1883
"""
    # port is on line 6
    assert find_ini_line(ini, section="MQTT", key="port") == 6
    assert find_ini_line(ini, section="mqtt", key="Port") == 6
    # loglevel is on line 2
    assert find_ini_line(ini, section="DEFAULT", key="loglevel") == 2


def test_find_ini_line_section_only():
    from gui.pages.config import find_ini_line

    ini = """[DEFAULT]
loglevel = INFO

[MQTT]
host = 192.168.1.1
"""
    assert find_ini_line(ini, section="MQTT") == 4
    # If key doesn't exist in section, fall back to section header
    assert find_ini_line(ini, section="MQTT", key="nonexistent") == 4


def test_find_ini_line_key_only():
    from gui.pages.config import find_ini_line

    ini = """[DEFAULT]
loglevel = INFO

[Poller]
cron = 0 * * * *
"""
    assert find_ini_line(ini, key="cron") == 5


def test_extract_section_and_key_from_serializer_value_error():
    ini = """[DEFAULT]
loglevel = INFO

[MQTT]
host = 192.168.1.1
port = not_an_int
"""
    ex = ValueError("Invalid integer value 'not_an_int' for [MQTT] -> Port")
    err_info = extract_syntax_error_info(ini, ex)
    assert err_info.lineno == 6
    assert "Invalid integer value" in err_info.message


def test_extract_section_header_from_missing_config_error():
    ini = """[DEFAULT]
loglevel = INFO

[Digits]
model = class11
"""
    ex = ValueError("Section Digits is missing names.")
    err_info = extract_syntax_error_info(ini, ex)
    assert err_info.lineno == 4  # [Digits] line


def test_extract_interpolation_error_with_section_and_option():
    ini = """[DEFAULT]
loglevel = INFO

[MQTT]
host = 192.168.1.1
port = ${bad:syntax
"""
    ex = configparser.InterpolationSyntaxError("port", "MQTT", "bad syntax")
    err_info = extract_syntax_error_info(ini, ex)
    assert err_info.lineno == 6
