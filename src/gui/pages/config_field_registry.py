"""Configuration Field Registry for auto-generating UI field schemas from Pydantic models."""

from __future__ import annotations

import enum
import re
import types
from typing import Any, Literal, get_args, get_origin

from pydantic.fields import FieldInfo

from config.models import (
    MQTT,
    Alignment,
    AutoContrast,
    CNNParams,
    Crop,
    GlareSuppression,
    History,
    ImageProcessing,
    ImageSource,
    Poller,
    Resize,
    Snapshots,
    ZeroFlowMonitor,
)
from configuration import Config
from data_classes import MeterConfig

# Explicit overrides for dropdown options, custom descriptions, or specific numeric bounds
FIELD_OVERRIDES: dict[tuple[str, str], dict[str, Any]] = {
    # [DEFAULT]
    ("default", "loglevel"): {
        "type": "select",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "description": "Log level for the application",
    },
    ("default", "minconfidencethreshold"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 1.0,
        "description": "Minimum CNN prediction confidence %",
    },
    # [ImageSource]
    ("imagesource", "timeout"): {
        "type": "int",
        "min": 1,
        "max": 300,
        "step": 1,
        "description": "Image fetch timeout in seconds",
    },
    ("imagesource", "minsize"): {
        "type": "int",
        "min": 0,
        "step": 1000,
        "description": "Minimum image file size in bytes",
    },
    # [Alignment]
    ("alignment", "rotationangle"): {
        "type": "select",
        "options": ["0", "90", "180", "270"],
        "description": "Initial coarse rotation angle (deg)",
    },
    ("alignment", "rotateangle"): {
        "type": "select",
        "options": ["0", "90", "180", "270"],
        "description": "Initial coarse rotation angle (deg)",
    },
    ("alignment", "postrotationangle"): {
        "type": "float",
        "min": -180.0,
        "max": 180.0,
        "step": 0.1,
        "description": "Fine-tuning rotation angle after alignment",
    },
    ("alignment", "postrotateangle"): {
        "type": "float",
        "min": -180.0,
        "max": 180.0,
        "step": 0.1,
        "description": "Fine-tuning rotation angle after alignment",
    },
    # [Digits], [Analog]
    ("digits", "model"): {
        "type": "select",
        "options": ["digital100", "digital", "analog100", "analog", "auto"],
        "description": "CNN inference model for digits",
    },
    ("analog", "model"): {
        "type": "select",
        "options": ["analog100", "analog", "digital100", "digital", "auto"],
        "description": "CNN inference model for analog needles",
    },
    # [ImageProcessing]
    ("imageprocessing", "contrast"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "brightness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "color"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "sharpness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "gamma"): {
        "type": "float",
        "min": 0.1,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "grayscale"): {"type": "boolean"},
    ("imageprocessing", "sharpnessmode"): {
        "type": "select",
        "options": ["standard", "unsharp_mask", "auto"],
        "description": "Sharpening filter mode",
    },
    ("imageprocessing", "unsharpradius"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
    },
    ("imageprocessing", "unsharpamount"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
    },
    ("imageprocessing", "unsharpthreshold"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
    },
    ("imageprocessing", "glaresuppressionmode"): {
        "type": "select",
        "options": ["clahe", "inpaint", "illumination_normalize", "combined"],
        "description": "Hotspot glare mitigation mode",
    },
    ("imageprocessing", "glareinpaintthreshold"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
    },
    ("imageprocessing", "glareinpaintradius"): {
        "type": "int",
        "min": 1,
        "max": 50,
        "step": 1,
    },
    ("imageprocessing", "glareclahecliplimit"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.5,
    },
    ("imageprocessing", "glareclahegridsize"): {
        "type": "int",
        "min": 2,
        "max": 64,
        "step": 1,
    },
    # [History]
    ("history", "backend"): {
        "type": "select",
        "options": ["sqlite", "memory"],
        "description": "Storage backend engine",
    },
    ("history", "maxmemorymb"): {
        "type": "float",
        "min": 1.0,
        "step": 5.0,
    },
    ("history", "maxrecords"): {
        "type": "int",
        "min": 100,
        "step": 1000,
    },
    ("history", "retentiondays"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    ("history", "pruneinterval"): {
        "type": "int",
        "min": 1,
        "step": 10,
    },
    # [Snapshots]
    ("snapshots", "mode"): {
        "type": "select",
        "options": [
            "smart_tiered",
            "change_only",
            "roi_strips_only",
            "full_frames",
            "disabled",
        ],
        "description": "Storage tiering policy",
    },
    ("snapshots", "format"): {
        "type": "select",
        "options": ["webp", "jpeg"],
        "description": "Image encoding format",
    },
    ("snapshots", "quality"): {
        "type": "int",
        "min": 1,
        "max": 100,
        "step": 5,
        "description": "Encoding quality (1-100)",
    },
    ("snapshots", "maxdiskmb"): {
        "type": "float",
        "min": 10.0,
        "step": 50.0,
        "description": "Max disk storage quota in MB",
    },
    ("snapshots", "recentfullframedays"): {
        "type": "int",
        "min": 0,
        "step": 1,
    },
    ("snapshots", "roistripretentiondays"): {
        "type": "int",
        "min": 0,
        "step": 1,
    },
    ("snapshots", "idleheartbeatminutes"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    # [Poller]
    ("poller", "intervalseconds"): {
        "type": "int",
        "min": 1,
        "step": 10,
        "description": "Polling interval in seconds",
    },
    ("poller", "retryintervalseconds"): {
        "type": "int",
        "min": 1,
        "step": 5,
    },
    ("poller", "consensusreads"): {
        "type": "int",
        "min": 1,
        "max": 10,
        "step": 1,
        "description": "Number of consecutive reads for temporal consensus/median filter (1=disabled)",
    },
    # [MQTT]
    ("mqtt", "port"): {
        "type": "int",
        "min": 1,
        "max": 65535,
        "step": 1,
        "description": "MQTT broker TCP port",
    },
    ("mqtt", "keepalive"): {
        "type": "int",
        "min": 5,
        "max": 3600,
        "step": 5,
    },
    # [ZeroFlowMonitor]
    ("zeroflowmonitor", "valuetype"): {
        "type": "select",
        "options": ["cumulative", "flow_rate"],
        "description": "Zero-flow calculation mode",
    },
    ("zeroflowmonitor", "continuousflowhours"): {
        "type": "float",
        "min": 0.1,
        "step": 0.5,
        "description": "Continuous flow hours before leak alert",
    },
    ("zeroflowmonitor", "minleakvolume"): {
        "type": "float",
        "min": 0.001,
        "step": 0.005,
        "description": "Minimum consumption delta to trigger leak",
    },
    ("zeroflowmonitor", "flowthreshold"): {
        "type": "float",
        "min": 0.0001,
        "step": 0.001,
    },
    ("zeroflowmonitor", "resolvedebouncecount"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    ("zeroflowmonitor", "maxhistoryevents"): {
        "type": "int",
        "min": 5,
        "step": 10,
    },
}


def _field_info_to_schema(field_info: FieldInfo) -> dict[str, Any]:
    """Convert a Pydantic FieldInfo to an interactive UI field schema."""
    annotation = field_info.annotation
    schema: dict[str, Any] = {}

    if field_info.description:
        schema["description"] = field_info.description

    # Handle Union types (e.g. int | None, Optional[bool])
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is getattr(types, "Union", None):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            annotation = args[0]
            origin = get_origin(annotation)

    # Check for Literal[...]
    if origin is Literal:
        options = [str(x) for x in get_args(annotation)]
        schema.update({"type": "select", "options": options})
        return schema

    # Check for Enum / StrEnum
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        options = [str(e.value) for e in annotation]
        schema.update({"type": "select", "options": options})
        return schema

    # Base python primitive types
    if annotation is bool:
        schema["type"] = "boolean"
    elif annotation is int:
        schema["type"] = "int"
        schema["step"] = 1
    elif annotation is float:
        schema["type"] = "float"
        schema["step"] = 0.1
    else:
        schema["type"] = "text"

    return schema


def _iter_config_sections() -> list[tuple[str, Any]]:
    """Enumerate all configuration section names and their corresponding Pydantic models."""
    return [
        ("default", Config),
        ("imagesource", ImageSource),
        ("digits", CNNParams),
        ("analog", CNNParams),
        ("alignment", Alignment),
        ("crop", Crop),
        ("resize", Resize),
        ("imageprocessing", ImageProcessing),
        ("history", History),
        ("snapshots", Snapshots),
        ("poller", Poller),
        ("mqtt", MQTT),
        ("zeroflowmonitor", ZeroFlowMonitor),
        ("meter", MeterConfig),
    ]


def build_field_registry() -> dict[tuple[str, str], dict[str, Any]]:
    """Auto-generate field schemas from Config and nested Pydantic models."""
    registry: dict[tuple[str, str], dict[str, Any]] = {}

    # Top-level and section-level model introspection
    for section_name, section_model in _iter_config_sections():
        sec_clean = section_name.lower().replace("_", "")
        for field_name, field_info in section_model.model_fields.items():
            # Skip nested models handled as separate sections
            if field_name in (
                "image_source",
                "digital_readout",
                "analog_readout",
                "alignment",
                "crop",
                "resize",
                "image_processing",
                "history",
                "snapshots",
                "poller",
                "mqtt",
                "zero_flow_monitor",
                "meter_configs",
                "autocontrast",
                "autocontrast_cut_images",
                "glare_suppression",
                "cut_images",
                "ref_images",
            ):
                continue

            schema = _field_info_to_schema(field_info)
            f_clean = field_name.lower().replace("_", "")
            registry[(sec_clean, f_clean)] = schema
            registry[(sec_clean, field_name.lower())] = schema

    # Introspect nested sub-models inside ImageProcessing (autocontrast, glare, etc.)
    for sub_model, prefix in [
        (AutoContrast, "autocontrast"),
        (GlareSuppression, "glare"),
    ]:
        for field_name, field_info in sub_model.model_fields.items():
            schema = _field_info_to_schema(field_info)
            comb_clean = f"{prefix}{field_name}".lower().replace("_", "")
            registry[("imageprocessing", comb_clean)] = schema

    # Apply explicit overrides for dropdowns, ranges, and descriptions
    for (sec, key), override in FIELD_OVERRIDES.items():
        s_clean = sec.lower().replace("_", "")
        k_clean = key.lower().replace("_", "")
        base_schema = registry.get((s_clean, k_clean), {})
        merged = {**base_schema, **override}
        registry[(s_clean, k_clean)] = merged
        registry[(s_clean, key.lower())] = merged

    return registry


# Initialized global registry
FIELD_SCHEMAS: dict[tuple[str, str], dict[str, Any]] = build_field_registry()


def get_field_schema(section: str, key: str, value: str = "") -> dict[str, Any]:
    """Resolve field schema (type, options, bounds) for section parameter."""
    sec_k = section.lower()
    k_lower = key.lower()
    sec_clean = sec_k.replace("_", "").replace(".", "")
    k_clean = k_lower.replace("_", "")

    # Direct tuple match
    if (sec_clean, k_clean) in FIELD_SCHEMAS:
        return FIELD_SCHEMAS[(sec_clean, k_clean)]
    if (sec_k, k_lower) in FIELD_SCHEMAS:
        return FIELD_SCHEMAS[(sec_k, k_lower)]

    # Meter.<name> sections
    if sec_k.startswith("meter.") or sec_clean.startswith("meter"):
        if ("meter", k_clean) in FIELD_SCHEMAS:
            return FIELD_SCHEMAS[("meter", k_clean)]
        if k_clean in (
            "consistencyenabled",
            "allownegativerates",
            "usepreviousvalue",
            "useextendedresolution",
            "detectnegativesign",
        ):
            return {"type": "boolean"}
        if k_clean == "maxratevalue":
            return {"type": "float", "min": 0.0, "step": 0.1}
        if k_clean == "prevaluefromfilemaxage":
            return {"type": "int", "min": 0, "step": 60}

    # Alignment.ref<N> / coordinate fields (X, Y, W, H)
    if k_clean in ("x", "y", "w", "h"):
        return {"type": "int", "min": 0, "step": 1}

    # Boolean detection by key name suffix or value
    val_clean = str(value).strip().lower()
    if (
        k_clean.endswith("enabled")
        or k_clean.startswith("is")
        or val_clean in ("true", "false")
    ):
        return {"type": "boolean"}

    # Numeric detection heuristics for ad-hoc custom parameters
    if re.match(r"^-?\d+$", val_clean):
        return {"type": "int", "step": 1}
    if re.match(r"^-?\d+\.\d+$", val_clean):
        return {"type": "float", "step": 0.1}

    return {"type": "text"}
