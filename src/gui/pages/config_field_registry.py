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
    ("default", "configdir"): {
        "type": "text",
        "description": "Directory path for configuration files and models",
    },
    ("default", "datadir"): {
        "type": "text",
        "description": "Directory path for databases, snapshots, and persistent data",
    },
    ("default", "previousvaluefile"): {
        "type": "text",
        "description": "File path for persisting previous meter values",
    },
    ("default", "digitalmodelsdir"): {
        "type": "text",
        "description": "Directory containing digital digit recognition models",
    },
    ("default", "analogmodelsdir"): {
        "type": "text",
        "description": "Directory containing analog needle recognition models",
    },
    # [ImageSource]
    ("imagesource", "url"): {
        "type": "text",
        "description": "Source image URL (e.g. http://, https://, or file://)",
    },
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
    # [Crop]
    ("crop", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable image cropping before alignment",
    },
    ("crop", "x"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "X-coordinate of top-left crop bounding box corner (in pixels)",
    },
    ("crop", "y"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Y-coordinate of top-left crop bounding box corner (in pixels)",
    },
    ("crop", "w"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Width of crop bounding box (in pixels)",
    },
    ("crop", "h"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Height of crop bounding box (in pixels)",
    },
    # [Resize]
    ("resize", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable image resizing before alignment",
    },
    ("resize", "w"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Target width in pixels for resized image",
    },
    ("resize", "h"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Target height in pixels for resized image",
    },
    # [Digits], [Analog]
    ("digits", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable digital digit recognition",
    },
    ("digits", "names"): {
        "type": "text",
        "description": "Comma-separated list of digital digit ROI names",
    },
    ("digits", "modelfile"): {
        "type": "text",
        "description": "File path of neural network model for digit classification",
    },
    ("digits", "model"): {
        "type": "select",
        "options": ["digital100", "digital", "analog100", "analog", "auto"],
        "description": "CNN inference model for digits",
    },
    ("analog", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable analog dial needle recognition",
    },
    ("analog", "names"): {
        "type": "text",
        "description": "Comma-separated list of analog dial ROI names",
    },
    ("analog", "modelfile"): {
        "type": "text",
        "description": "File path of neural network model for analog needle classification",
    },
    ("analog", "model"): {
        "type": "select",
        "options": ["analog100", "analog", "digital100", "digital", "auto"],
        "description": "CNN inference model for analog needles",
    },
    # [ImageProcessing]
    ("imageprocessing", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable image processing and filtering",
    },
    ("imageprocessing", "contrast"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
        "description": "Contrast adjustment factor (1.0 = unchanged)",
    },
    ("imageprocessing", "brightness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
        "description": "Brightness adjustment factor (1.0 = unchanged)",
    },
    ("imageprocessing", "color"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
        "description": "Color saturation factor (1.0 = unchanged)",
    },
    ("imageprocessing", "sharpness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
        "description": "Sharpness enhancement factor (1.0 = unchanged)",
    },
    ("imageprocessing", "gamma"): {
        "type": "float",
        "min": 0.1,
        "max": 5.0,
        "step": 0.1,
        "description": "Gamma correction factor (1.0 = unchanged)",
    },
    ("imageprocessing", "grayscale"): {
        "type": "boolean",
        "description": "Convert camera image to grayscale before processing",
    },
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
        "description": "Radius of Gaussian blur for unsharp masking (in pixels)",
    },
    ("imageprocessing", "unsharpamount"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
        "description": "Strength factor for unsharp masking sharpness boost",
    },
    ("imageprocessing", "unsharpthreshold"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
        "description": "Minimum brightness difference threshold to apply unsharp mask",
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
        "description": "Luminance threshold (0-255) to detect specular glare hotspots",
    },
    ("imageprocessing", "glareinpaintradius"): {
        "type": "int",
        "min": 1,
        "max": 50,
        "step": 1,
        "description": "Inpainting neighborhood radius in pixels (Fast Marching)",
    },
    ("imageprocessing", "glareclahecliplimit"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.5,
        "description": "Contrast limiting threshold factor for CLAHE equalization",
    },
    ("imageprocessing", "glareclahegridsize"): {
        "type": "int",
        "min": 2,
        "max": 64,
        "step": 1,
        "description": "Tile grid division size for CLAHE (e.g. 8 for 8x8 grid)",
    },
    ("imageprocessing", "autocontrast"): {
        "type": "boolean",
        "description": "Apply histogram auto-contrast balancing to full image",
    },
    ("imageprocessing", "autocontrastcutofflow"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 0.5,
        "description": "Lower histogram percentile cutoff percentage for auto-contrast",
    },
    ("imageprocessing", "autocontrastcutoffhigh"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 0.5,
        "description": "Upper histogram percentile cutoff percentage for auto-contrast",
    },
    ("imageprocessing", "autocontrastignore"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
        "description": "Pixel intensity value to ignore in auto-contrast (or None)",
    },
    ("imageprocessing", "autocontrastcutimages"): {
        "type": "boolean",
        "description": "Apply auto-contrast individually to cropped ROI cutouts",
    },
    ("imageprocessing", "autocontrastcutimagescutofflow"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 0.5,
        "description": "Lower percentile cutoff for cropped ROI cutouts auto-contrast",
    },
    ("imageprocessing", "autocontrastcutimagescutoffhigh"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 0.5,
        "description": "Upper percentile cutoff for cropped ROI cutouts auto-contrast",
    },
    ("imageprocessing", "autocontrastcutimagesignore"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
        "description": "Pixel intensity value to ignore in cut ROI auto-contrast (or None)",
    },
    ("imageprocessing", "glaresuppressionenabled"): {
        "type": "boolean",
        "description": "Flag to enable specular glare and reflection suppression",
    },
    ("imageprocessing", "glareapplytocutimages"): {
        "type": "boolean",
        "description": "Apply glare suppression individually to cropped ROI cutouts",
    },
    ("imageprocessing", "autosharpencutimages"): {
        "type": "boolean",
        "description": "Apply sharpening filter individually to cropped ROI cutouts",
    },
    # [Alignment]
    ("alignment", "refs"): {
        "type": "text",
        "description": "Comma-separated list of reference image section names (e.g. ref0, ref1)",
    },
    # [History]
    ("history", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable historical readings and snapshot database storage",
    },
    ("history", "backend"): {
        "type": "select",
        "options": ["sqlite", "memory"],
        "description": "Storage backend engine",
    },
    ("history", "dburl"): {
        "type": "text",
        "description": "Database connection URL (e.g. sqlite:////data/meter.db)",
    },
    ("history", "maxmemorymb"): {
        "type": "float",
        "min": 1.0,
        "step": 5.0,
        "description": "Maximum in-memory SQLite cache size in MB",
    },
    ("history", "maxrecords"): {
        "type": "int",
        "min": 100,
        "step": 1000,
        "description": "Maximum number of historical meter readings to retain",
    },
    ("history", "retentiondays"): {
        "type": "int",
        "min": 1,
        "step": 1,
        "description": "Number of days to keep historical reading records",
    },
    ("history", "pruneinterval"): {
        "type": "int",
        "min": 1,
        "step": 10,
        "description": "Interval between database pruning sweeps (in minutes)",
    },
    ("history", "autovacuum"): {
        "type": "boolean",
        "description": "Perform incremental database vacuum during pruning",
    },
    # [Snapshots]
    ("snapshots", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable snapshot capturing and storage",
    },
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
        "description": "Days to keep raw uncompressed full-frame snapshots",
    },
    ("snapshots", "roistripretentiondays"): {
        "type": "int",
        "min": 0,
        "step": 1,
        "description": "Days to retain lightweight ROI strip snapshots",
    },
    ("snapshots", "idleheartbeatminutes"): {
        "type": "int",
        "min": 1,
        "step": 1,
        "description": "Minutes between idle keepalive heartbeat snapshots",
    },
    ("snapshots", "alwayssaveonanomaly"): {
        "type": "boolean",
        "description": "Always archive full camera frame when OCR error or low confidence occurs",
    },
    ("snapshots", "storagedir"): {
        "type": "text",
        "description": "Filesystem directory for compressed snapshot storage",
    },
    # [Poller]
    ("poller", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable scheduled background meter readouts",
    },
    ("poller", "cron"): {
        "type": "text",
        "description": "Cron schedule with second resolution (6 fields: s m h d m wd) or 5 fields (e.g. '*/15 * * * * *')",
    },
    ("poller", "runonstartup"): {
        "type": "boolean",
        "description": "Flag to run a readout immediately on application startup",
    },
    ("poller", "saveimages"): {
        "type": "boolean",
        "description": "Flag to save intermediate debug images during polled readouts",
    },
    ("poller", "retryintervalseconds"): {
        "type": "int",
        "min": 1,
        "step": 5,
        "description": "Delay in seconds before retrying failed reads",
    },
    ("poller", "consensusreads"): {
        "type": "int",
        "min": 1,
        "max": 10,
        "step": 1,
        "description": "Number of consecutive reads for temporal consensus/median filter (1=disabled)",
    },
    # [MQTT]
    ("mqtt", "enabled"): {
        "type": "boolean",
        "description": "Flag to enable MQTT client publishing and discovery",
    },
    ("mqtt", "broker"): {
        "type": "text",
        "description": "MQTT broker host name or IP address",
    },
    ("mqtt", "host"): {
        "type": "text",
        "description": "MQTT broker host name or IP address",
    },
    ("mqtt", "username"): {
        "type": "text",
        "description": "MQTT broker authentication username",
    },
    ("mqtt", "password"): {
        "type": "text",
        "description": "MQTT broker authentication password",
    },
    ("mqtt", "clientid"): {
        "type": "text",
        "description": "Client ID for MQTT connection",
    },
    ("mqtt", "topicprefix"): {
        "type": "text",
        "description": "Base topic prefix for MQTT telemetry publishing",
    },
    ("mqtt", "retain"): {
        "type": "boolean",
        "description": "Retain published MQTT messages on broker",
    },
    ("mqtt", "cleansession"): {
        "type": "boolean",
        "description": "Start clean session on MQTT broker connection",
    },
    ("mqtt", "tls"): {
        "type": "boolean",
        "description": "Enable TLS/SSL encryption for MQTT connection",
    },
    ("mqtt", "homeassistantdiscovery"): {
        "type": "boolean",
        "description": "Enable Home Assistant MQTT auto-discovery",
    },
    ("mqtt", "discoveryprefix"): {
        "type": "text",
        "description": "Home Assistant MQTT auto-discovery prefix (default: homeassistant)",
    },
    ("mqtt", "devicename"): {
        "type": "text",
        "description": "Device name for Home Assistant discovery",
    },
    ("mqtt", "deviceid"): {
        "type": "text",
        "description": "Unique device identifier for Home Assistant discovery",
    },
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
        "description": "MQTT keepalive ping interval in seconds",
    },
    ("mqtt", "qos"): {
        "type": "select",
        "options": ["0", "1", "2"],
        "description": "MQTT Publish Quality of Service (0=at most once, 1=at least once, 2=exactly once)",
    },
    ("mqtt", "protocol"): {
        "type": "select",
        "options": ["3.1.1", "5.0", "3.1"],
        "description": "MQTT protocol version",
    },
    ("mqtt", "tls_insecure"): {
        "type": "boolean",
        "description": "Allow self-signed broker certs or skip hostname check (insecure)",
    },
    ("mqtt", "tlsinsecure"): {
        "type": "boolean",
        "description": "Allow self-signed broker certs or skip hostname check (insecure)",
    },
    ("mqtt", "tls_ca_cert"): {
        "type": "text",
        "description": "Path to custom CA certificate file (.crt / .pem)",
    },
    ("mqtt", "cacert"): {
        "type": "text",
        "description": "Path to custom CA certificate file (.crt / .pem)",
    },
    ("mqtt", "tls_certfile"): {
        "type": "text",
        "description": "Client certificate path for mutual TLS (mTLS)",
    },
    ("mqtt", "clientcert"): {
        "type": "text",
        "description": "Client certificate path for mutual TLS (mTLS)",
    },
    ("mqtt", "tls_keyfile"): {
        "type": "text",
        "description": "Client private key path for mutual TLS (mTLS)",
    },
    ("mqtt", "clientkey"): {
        "type": "text",
        "description": "Client private key path for mutual TLS (mTLS)",
    },
    ("mqtt", "tls_psk_identity"): {
        "type": "text",
        "description": "Pre-Shared Key (PSK) identity string",
    },
    ("mqtt", "tls_psk"): {
        "type": "text",
        "description": "Pre-Shared Key (hex format or secret string)",
    },
    ("mqtt", "tls_psk_file"): {
        "type": "text",
        "description": "Docker secret file path containing the PSK (e.g. /run/secrets/mqtt_psk)",
    },
    ("mqtt", "tls_ciphers"): {
        "type": "text",
        "description": "Custom OpenSSL cipher suite specification",
    },
    ("mqtt", "ciphers"): {
        "type": "text",
        "description": "Custom OpenSSL cipher suite specification",
    },
    # [ZeroFlowMonitor]
    ("zeroflowmonitor", "enabled"): {
        "type": "boolean",
        "description": "Enable zero-flow continuous consumption leak detection",
    },
    ("zeroflowmonitor", "meter"): {
        "type": "text",
        "description": "Target meter name for leak monitoring",
    },
    ("zeroflowmonitor", "metername"): {
        "type": "text",
        "description": "Target meter name for leak monitoring",
    },
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
        "description": "Minimum flow rate to consider water actively flowing",
    },
    ("zeroflowmonitor", "resolvedebouncecount"): {
        "type": "int",
        "min": 1,
        "step": 1,
        "description": "Consecutive zero-flow readings required to resolve leak alert",
    },
    ("zeroflowmonitor", "maxhistoryevents"): {
        "type": "int",
        "min": 5,
        "step": 10,
        "description": "Maximum number of leak history events to retain in memory",
    },
    # [Meters], [Meter.*]
    ("meters", "names"): {
        "type": "text",
        "description": "Comma-separated list of logical meter names (e.g. digital, analog, total)",
    },
    ("meter", "value"): {
        "type": "text",
        "description": "Value template referencing digit/dial cutouts or sub-meters",
    },
    ("meter", "format"): {
        "type": "text",
        "description": "Value template referencing digit/dial cutouts or sub-meters",
    },
    ("meter", "consistencyenabled"): {
        "type": "boolean",
        "description": "Flag to enable rate consistency validation check",
    },
    ("meter", "allownegativerates"): {
        "type": "boolean",
        "description": "Flag to allow negative consumption rate changes",
    },
    ("meter", "maxratevalue"): {
        "type": "float",
        "min": 0.0,
        "step": 0.1,
        "description": "Maximum allowed consumption change rate threshold",
    },
    ("meter", "minratevalue"): {
        "type": "float",
        "min": 0.0,
        "step": 0.1,
        "description": "Minimum required consumption change rate threshold (0 = disabled)",
    },
    ("meter", "stalethresholdhours"): {
        "type": "float",
        "min": 0.0,
        "step": 1.0,
        "description": "Hours without consumption change before flagging as stale (0 = disabled)",
    },
    ("meter", "usepreviousvalue"): {
        "type": "boolean",
        "description": "Replace unreadable digits/dials (N) with last known valid reading",
    },
    ("meter", "prevaluefromfilemaxage"): {
        "type": "int",
        "min": 0,
        "step": 60,
        "description": "Maximum age in minutes to trust previous value from file (0 = no limit)",
    },
    ("meter", "useextendedresolution"): {
        "type": "boolean",
        "description": "Append fractional sub-digit decimal resolution from analog needle",
    },
    ("meter", "unit"): {
        "type": "text",
        "description": "Measurement unit string for readout (e.g. m3, L, kWh)",
    },
    ("meter", "detectnegativesign"): {
        "type": "boolean",
        "description": "Detect negative sign indicator on meter readout",
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


def build_line_tooltips(text: str) -> dict[int, str]:
    """Map each [section] header and key= line in INI text to documentation tooltips.

    1-indexed line numbers are mapped to human-readable strings formatted with
    descriptions, types, ranges, and allowed values.
    """
    tooltips: dict[int, str] = {}
    current_section = ""
    section_re = re.compile(r"^\s*\[([^\]]+)\]\s*(?:[;#].*)?$")
    key_re = re.compile(r"^\s*([^#;=:\s][^=:]*?)\s*[:=]\s*(.*)$")

    for i, line in enumerate(text.splitlines(), start=1):
        sec_m = section_re.match(line)
        if sec_m:
            current_section = sec_m.group(1).strip()
            sec_lower = current_section.lower()
            sec_clean = sec_lower.replace("_", "").replace(".", "")

            if "." in current_section:
                base, sub = current_section.split(".", 1)
                base_low = base.lower()
                if "alignment" in base_low:
                    tooltips[i] = f"[{current_section}] — Reference marker '{sub}'"
                elif "digit" in base_low:
                    tooltips[i] = f"[{current_section}] — Digital digit ROI '{sub}'"
                elif "analog" in base_low:
                    tooltips[i] = (
                        f"[{current_section}] — Analog dial needle ROI '{sub}'"
                    )
                elif "meter" in base_low:
                    tooltips[i] = (
                        f"[{current_section}] — Meter configuration for '{sub}'"
                    )
                else:
                    tooltips[i] = f"[{current_section}] — Subsection '{sub}'"
            else:
                known = {k for (s, k) in FIELD_SCHEMAS if s in (sec_clean, sec_lower)}
                if known:
                    tooltips[i] = f"[{current_section}] — {len(known)} documented keys"
                else:
                    tooltips[i] = f"[{current_section}]"
            continue

        key_m = key_re.match(line)
        if key_m and current_section:
            key = key_m.group(1).strip()
            val_raw = key_m.group(2)
            val_clean = re.sub(r"\s*[;#].*$", "", val_raw).strip()

            sec_lower = current_section.lower()
            sec_clean = sec_lower.replace("_", "").replace(".", "")
            k_lower = key.lower()
            k_clean = k_lower.replace("_", "")
            lookup_key = (sec_clean, k_clean)

            # Check if this is a known schema key or recognized pattern
            is_known_key = (
                lookup_key in FIELD_SCHEMAS
                or (sec_lower, k_lower) in FIELD_SCHEMAS
                or (
                    sec_clean.startswith("meter")
                    and ("meter", k_clean) in FIELD_SCHEMAS
                )
                or (
                    (
                        "." in current_section
                        or sec_clean in ("crop", "resize", "alignment")
                    )
                    and k_clean in ("x", "y", "w", "h", "image")
                )
            )

            if not is_known_key:
                continue

            schema = get_field_schema(current_section, key, val_clean)
            parts: list[str] = []

            desc = schema.get("description") or schema.get("title")
            if not desc:
                if k_clean == "x":
                    desc = "Target X-coordinate in pixel space"
                elif k_clean == "y":
                    desc = "Target Y-coordinate in pixel space"
                elif k_clean == "w":
                    desc = "Target width in pixels"
                elif k_clean == "h":
                    desc = "Target height in pixels"
                elif k_clean == "image":
                    desc = "File path of reference image"

            if desc:
                parts.append(desc)

            field_type = schema.get("type")
            if field_type == "text":
                field_type = "str"
            if field_type:
                parts.append(f"Type: {field_type}")

            mn, mx = schema.get("min"), schema.get("max")
            if mn is not None and mx is not None:
                parts.append(f"Range: {mn} - {mx}")
            elif mn is not None:
                parts.append(f"Min: {mn}")
            elif mx is not None:
                parts.append(f"Max: {mx}")

            opts = schema.get("options") or schema.get("enum")
            if opts:
                parts.append(f"Values: {', '.join(str(o) for o in opts)}")

            if parts:
                tooltips[i] = "  |  ".join(parts)

    return tooltips
