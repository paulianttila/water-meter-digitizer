"""Unit tests for CodeMirror line-level hover tooltips generation."""

from gui.pages.config import build_line_tooltips
from gui.pages.config_field_registry import (
    build_line_tooltips as registry_build_line_tooltips,
)

INI = """
[DEFAULT]
loglevel = INFO

[MQTT]
host = 192.168.1.1
port = 1883
"""


def test_import_equivalence():
    assert build_line_tooltips is registry_build_line_tooltips


def test_section_header_tooltip():
    tips = build_line_tooltips(INI)
    # [DEFAULT] is on line 2 (line 1 is empty newline)
    assert 2 in tips
    assert "DEFAULT" in tips[2]
    assert "documented keys" in tips[2]

    # [MQTT] is on line 5
    assert 5 in tips
    assert "MQTT" in tips[5]
    assert "documented keys" in tips[5]


def test_known_key_gets_tooltip():
    tips = build_line_tooltips(INI)
    # loglevel is on line 3
    assert 3 in tips
    loglevel_tip = tips[3]
    assert "Log level" in loglevel_tip or "loglevel" in loglevel_tip.lower()
    assert "DEBUG" in loglevel_tip or "select" in loglevel_tip.lower()

    # host is on line 6
    assert 6 in tips
    assert "MQTT" in tips[6] or "broker" in tips[6].lower()
    assert "Type: str" in tips[6]

    # port is on line 7
    assert 7 in tips
    assert "1" in tips[7] and "65535" in tips[7]
    assert "Type: int" in tips[7]


def test_unknown_key_no_tooltip():
    tips = build_line_tooltips("[MQTT]\nsome_unknown = x\n")
    # Only the section header (line 1) should have a tooltip, not the unknown key (line 2)
    assert 1 in tips
    assert 2 not in tips
    assert all("some_unknown" not in v for v in tips.values())


def test_subsections_and_coordinates():
    ini_content = """[Alignment.ref0]
image = /config/ref0.jpg
x = 100
y = 200
w = 30
h = 40

[Digits.digit1]
x = 215
y = 97
w = 42
h = 75
"""
    tips = build_line_tooltips(ini_content)

    # Line 1: [Alignment.ref0]
    assert 1 in tips
    assert "Reference marker 'ref0'" in tips[1]

    # Line 2: image
    assert 2 in tips
    assert "reference" in tips[2].lower()

    # Line 3: x
    assert 3 in tips
    assert "Type: int" in tips[3]
    assert "X-coordinate" in tips[3]

    # Line 8: [Digits.digit1]
    assert 8 in tips
    assert "Digital digit ROI 'digit1'" in tips[8]

    # Line 9: x
    assert 9 in tips
    assert "Type: int" in tips[9]


def test_meter_section_and_values():
    ini_content = """[Meter.water]
Value = {digit1}{digit2}
ConsistencyEnabled = True
MaxRateValue = 0.5
Unit = m3
"""
    tips = build_line_tooltips(ini_content)

    # Line 1: Section
    assert 1 in tips
    assert "Meter configuration for 'water'" in tips[1]

    # Line 2: Value
    assert 2 in tips
    assert "Value template" in tips[2]

    # Line 3: ConsistencyEnabled
    assert 3 in tips
    assert "consistency" in tips[3].lower()
    assert "Type: boolean" in tips[3]

    # Line 4: MaxRateValue
    assert 4 in tips
    assert "Type: float" in tips[4]

    # Line 5: Unit
    assert 5 in tips
    assert "unit" in tips[5].lower()


def test_comments_and_blank_lines_have_no_tooltips():
    ini_content = """# Comment line 1
; Semicolon comment line 2

[DEFAULT]
# Inline comment inside section
LogLevel = INFO # trailing comment
"""
    tips = build_line_tooltips(ini_content)
    assert 1 not in tips
    assert 2 not in tips
    assert 3 not in tips  # blank
    assert 4 in tips  # [DEFAULT]
    assert 5 not in tips  # comment inside section
    assert 6 in tips  # LogLevel = INFO
    assert "Log level" in tips[6]


def test_full_config_ini():
    with open("config/config.ini", encoding="utf-8") as f:
        config_text = f.read()

    tips = build_line_tooltips(config_text)
    # The vast majority of lines in config.ini have keys or section headers
    assert len(tips) > 150
