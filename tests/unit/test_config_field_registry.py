"""Unit tests for config_field_registry auto-generation and schema resolution."""

from pydantic.fields import FieldInfo

from gui.config_field_registry import (
    _field_info_to_schema,
    build_field_registry,
    get_field_schema,
)


def test_build_field_registry_populates_entries():
    registry = build_field_registry()
    assert len(registry) > 40

    # Test top-level fields
    assert ("default", "loglevel") in registry
    assert registry[("default", "loglevel")]["type"] == "select"
    assert "DEBUG" in registry[("default", "loglevel")]["options"]

    # Test section model fields
    assert ("imagesource", "timeout") in registry
    assert registry[("imagesource", "timeout")]["type"] == "int"

    assert ("imageprocessing", "contrast") in registry
    assert registry[("imageprocessing", "contrast")]["type"] == "float"

    assert ("history", "autovacuum") in registry
    assert registry[("history", "autovacuum")]["type"] == "boolean"


def test_field_info_to_schema():
    # Boolean
    f_bool = FieldInfo.from_annotation(bool)
    assert _field_info_to_schema(f_bool)["type"] == "boolean"

    # Int
    f_int = FieldInfo.from_annotation(int)
    assert _field_info_to_schema(f_int)["type"] == "int"

    # Float
    f_float = FieldInfo.from_annotation(float)
    assert _field_info_to_schema(f_float)["type"] == "float"

    # String with description
    f_str = FieldInfo(annotation=str, description="Test description")
    res = _field_info_to_schema(f_str)
    assert res["type"] == "text"
    assert res["description"] == "Test description"


def test_get_field_schema_lookups():
    # Direct match
    assert get_field_schema("DEFAULT", "LogLevel", "INFO")["type"] == "select"
    assert get_field_schema("ImageSource", "Timeout", "30")["type"] == "int"
    assert get_field_schema("ImageProcessing", "Contrast", "1.0")["type"] == "float"

    # Meter parameters
    assert (
        get_field_schema("Meter.total", "ConsistencyEnabled", "true")["type"]
        == "boolean"
    )
    assert get_field_schema("Meter.total", "MaxRateValue", "0.5")["type"] == "float"
    assert (
        get_field_schema("Meter.total", "PreValueFromFileMaxAge", "100")["type"]
        == "int"
    )

    # Coordinate fields
    assert get_field_schema("Alignment.ref0", "X", "100")["type"] == "int"
    assert get_field_schema("Alignment.ref0", "Y", "200")["type"] == "int"

    # Custom boolean
    assert get_field_schema("Custom", "MyFlagEnabled", "false")["type"] == "boolean"

    # Custom int & float
    assert get_field_schema("Custom", "MyNumber", "42")["type"] == "int"
    assert get_field_schema("Custom", "MyDecimal", "3.14")["type"] == "float"

    # Text fallback
    assert get_field_schema("Custom", "MyText", "hello world")["type"] == "text"
