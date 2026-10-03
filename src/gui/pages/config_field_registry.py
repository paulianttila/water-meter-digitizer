"""Configuration Field Registry for auto-generating UI field schemas from Pydantic models."""

from __future__ import annotations

import configparser
import contextlib
import enum
import re
import types
from typing import Any, Literal, NamedTuple, get_args, get_origin

from pydantic.fields import FieldInfo

from config.models import (
    MQTT,
    Alignment,
    AutoContrast,
    CNNParams,
    Crop,
    Denoise,
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
    ("imageprocessing", "autocontrastfullimage"): {
        "type": "boolean",
        "description": "Apply histogram auto-contrast balancing to full meter image",
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
    ("imageprocessing", "glaresuppressionfullimage"): {
        "type": "boolean",
        "description": "Flag to enable specular glare suppression on full image",
    },
    ("imageprocessing", "glaresuppressioncutimages"): {
        "type": "boolean",
        "description": "Apply glare suppression individually to cropped ROI cutouts",
    },
    ("imageprocessing", "glaresuppressionenabled"): {
        "type": "boolean",
        "description": "Flag to enable specular glare and reflection suppression",
    },
    ("imageprocessing", "glareapplytocutimages"): {
        "type": "boolean",
        "description": "Apply glare suppression individually to cropped ROI cutouts",
    },
    ("imageprocessing", "denoisefullimage"): {
        "type": "boolean",
        "description": "Flag to enable noise reduction filtering on full image",
    },
    ("imageprocessing", "denoisecutimages"): {
        "type": "boolean",
        "description": "Apply noise reduction individually to cropped ROI cutouts",
    },
    ("imageprocessing", "denoiseenabled"): {
        "type": "boolean",
        "description": "Flag to enable edge-preserving noise reduction filtering",
    },
    ("imageprocessing", "denoiseapplytocutimages"): {
        "type": "boolean",
        "description": "Apply noise reduction individually to cropped ROI cutouts",
    },
    ("imageprocessing", "denoisemethod"): {
        "type": "select",
        "options": ["bilateral", "nlmeans", "median", "median_bilateral"],
        "description": "Algorithm for edge-preserving noise reduction",
    },
    ("imageprocessing", "denoisediameter"): {
        "type": "int",
        "min": 1,
        "max": 15,
        "step": 2,
        "description": "Pixel neighborhood diameter for bilateral or median filter",
    },
    ("imageprocessing", "denoisesigmacolor"): {
        "type": "float",
        "min": 5.0,
        "max": 150.0,
        "step": 5.0,
        "description": "Filter sigma in the color space for bilateral filtering",
    },
    ("imageprocessing", "denoisesigmaspace"): {
        "type": "float",
        "min": 5.0,
        "max": 150.0,
        "step": 5.0,
        "description": "Filter sigma in the coordinate space for bilateral filtering",
    },
    ("imageprocessing", "denoisestrength"): {
        "type": "float",
        "min": 1.0,
        "max": 30.0,
        "step": 0.5,
        "description": "Filter strength parameter (h) for Non-Local Means denoising",
    },
    ("imageprocessing", "denoisetemplatewindow"): {
        "type": "int",
        "min": 3,
        "max": 15,
        "step": 2,
        "description": "Size in pixels of template patch for NL-Means",
    },
    ("imageprocessing", "denoisesearchwindow"): {
        "type": "int",
        "min": 7,
        "max": 35,
        "step": 2,
        "description": "Size in pixels of search window for NL-Means",
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
                "denoise",
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
        (Denoise, "denoise"),
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


def find_ini_line(
    text: str, section: str | None = None, key: str | None = None
) -> int | None:
    """Find the 1-indexed line number of a section and/or key in INI text.

    If key is specified and found inside the section, returns the line of the key.
    If key is not found (or not specified) but section is found, returns the section header line.
    If section is not found but key is specified, returns the line of the key anywhere in text.
    """
    if not text:
        return None

    lines = text.splitlines()
    sec_clean = section.strip("[]'\"").lower() if section else None
    key_clean = key.strip("'\"").lower() if key else None

    def norm_sec(s: str) -> str:
        return s.replace("_", "").replace("-", "").lower()

    cur_sec: str | None = None
    target_sec_line: int | None = None

    for idx, line in enumerate(lines, start=1):
        line_s = line.strip()
        if not line_s or line_s.startswith(("#", ";")):
            continue

        # Check section header
        if line_s.startswith("[") and "]" in line_s:
            cur_sec = line_s[1 : line_s.index("]")].strip()
            is_match = False
            if sec_clean:
                cur_lower = cur_sec.lower()
                is_match = (
                    cur_lower == sec_clean
                    or norm_sec(cur_sec) == norm_sec(sec_clean)
                    or cur_lower.endswith("." + sec_clean)
                    or sec_clean.endswith("." + cur_lower)
                    or cur_lower.startswith(sec_clean + ".")
                    or sec_clean.startswith(cur_lower + ".")
                )

            if is_match:
                target_sec_line = idx
                if not key_clean:
                    return idx
            continue

        # If inside matching section, look for key
        if target_sec_line is not None and cur_sec:
            cur_lower = cur_sec.lower()
            is_in_target = (
                cur_lower == sec_clean
                or norm_sec(cur_sec) == norm_sec(sec_clean or "")
                or (sec_clean and cur_lower.endswith("." + sec_clean))
                or (sec_clean and cur_lower.startswith(sec_clean + "."))
            )
            if is_in_target and key_clean and ("=" in line or ":" in line):
                delim = "=" if "=" in line else ":"
                k = line.split(delim, 1)[0].strip().lower()
                if (
                    k == key_clean
                    or k.replace("_", "") == key_clean.replace("_", "")
                    or k.replace("-", "") == key_clean.replace("-", "")
                ):
                    return idx

    # If section was found but key wasn't, return section header line
    if target_sec_line is not None:
        return target_sec_line

    # If key was specified and section wasn't found, look for key anywhere in text
    if key_clean:
        for idx, line in enumerate(lines, start=1):
            line_s = line.strip()
            if not line_s or line_s.startswith(("#", ";")):
                continue
            if "=" in line or ":" in line:
                delim = "=" if "=" in line else ":"
                k = line.split(delim, 1)[0].strip().lower()
                if (
                    k == key_clean
                    or k.replace("_", "") == key_clean.replace("_", "")
                    or k.replace("-", "") == key_clean.replace("-", "")
                ):
                    return idx

    # If only section was specified
    if sec_clean:
        for idx, line in enumerate(lines, start=1):
            line_s = line.strip()
            if line_s.startswith("[") and "]" in line_s:
                s = line_s[1 : line_s.index("]")].strip().lower()
                if (
                    s == sec_clean
                    or norm_sec(s) == norm_sec(sec_clean)
                    or s.endswith("." + sec_clean)
                    or s.startswith(sec_clean + ".")
                ):
                    return idx

    return None


class SyntaxErrorInfo(NamedTuple):
    """Structured information about a configuration syntax error."""

    lineno: int | None
    position: int | None  # 0-indexed character offset into document string
    message: str


def extract_syntax_error_info(text: str, error: Exception) -> SyntaxErrorInfo:
    """Extract 1-indexed line number, document position, and clean description from a config error."""
    lineno: int | None = None
    msg: str = str(error)
    sec_candidate: str | None = None
    key_candidate: str | None = None

    if isinstance(error, configparser.MissingSectionHeaderError):
        lineno = error.lineno
        raw = error.args[2].strip() if len(error.args) > 2 else "no section"
        msg = f"Missing section header: {raw}"
    elif isinstance(error, configparser.ParsingError) and getattr(
        error, "errors", None
    ):
        lineno, raw_line = error.errors[0]
        msg = f"Parsing error on line {lineno}: {raw_line.strip()}"
    elif isinstance(
        error,
        (
            configparser.DuplicateSectionError,
            configparser.DuplicateOptionError,
        ),
    ):
        lineno = getattr(error, "lineno", None)
        sec_candidate = getattr(error, "section", None)
        key_candidate = getattr(error, "option", None)
        raw_msg = getattr(error, "message", None) or str(error)
        msg = f"{error.__class__.__name__}: {raw_msg}"
    else:
        # Check standard configparser section / option attributes
        sec_candidate = getattr(error, "section", None)
        key_candidate = getattr(error, "option", None)

        # Check Pydantic validation error details if available
        if hasattr(error, "errors") and callable(error.errors):
            with contextlib.suppress(Exception):
                err_list = error.errors()
                if err_list:
                    loc = err_list[0].get("loc", ())
                    if len(loc) >= 2:
                        sec_candidate = sec_candidate or str(loc[0])
                        key_candidate = key_candidate or str(loc[-1])
                    elif len(loc) == 1:
                        key_candidate = key_candidate or str(loc[0])

        # Regex check for explicit line numbers in error message
        m = re.search(r"(?:\[line\s*(\d+)\]|line\s+(\d+))", str(error), re.IGNORECASE)
        if m:
            candidate = int(m.group(1) or m.group(2))
            lines_count = len(text.splitlines()) if text else 1
            if 1 <= candidate <= max(lines_count, 1):
                lineno = candidate

        # Extract section and key from error message text if not already known
        err_str = str(error)

        # Pattern: for [section] -> option
        if not sec_candidate or not key_candidate:
            m_sec_opt = re.search(
                r"for\s+\[([^\]]+)\]\s*->\s*([a-zA-Z0-9_\-\.]+)",
                err_str,
                re.IGNORECASE,
            )
            if m_sec_opt:
                sec_candidate = sec_candidate or m_sec_opt.group(1)
                key_candidate = key_candidate or m_sec_opt.group(2)

        # Pattern: in section '...' or section '...'
        if not sec_candidate:
            m_sec = re.search(
                r"(?:in\s+section|section)\s+['\"\[]?([a-zA-Z0-9_\-\.]+)['\"\]]?",
                err_str,
                re.IGNORECASE,
            )
            if m_sec:
                sec_candidate = m_sec.group(1)

        # Pattern: [section] anywhere in error
        if not sec_candidate:
            m_bracket = re.search(r"\[([a-zA-Z0-9_\-\.]+)\]", err_str)
            if m_bracket:
                sec_candidate = m_bracket.group(1)

        # Pattern: meter '...'
        if not sec_candidate:
            m_meter = re.search(
                r"meter\s+['\"]([a-zA-Z0-9_\-\.]+)['\"]", err_str, re.IGNORECASE
            )
            if m_meter:
                sec_candidate = f"Meter.{m_meter.group(1)}"

        # Pattern: option '...' or key '...' or parameter '...' or field '...'
        if not key_candidate:
            m_key = re.search(
                r"(?:option|key|parameter|field)\s+['\"]([a-zA-Z0-9_\-\.]+)['\"]",
                err_str,
                re.IGNORECASE,
            )
            if m_key:
                key_candidate = m_key.group(1)

        # Pattern: '...' is missing
        if not key_candidate:
            m_missing = re.search(
                r"['\"]([a-zA-Z0-9_\-\.]+)['\"]\s+is\s+missing",
                err_str,
                re.IGNORECASE,
            )
            if m_missing:
                key_candidate = m_missing.group(1)

        # Special keywords
        if not key_candidate and "cron" in err_str.lower():
            key_candidate = "Cron"
            sec_candidate = sec_candidate or "Poller"
        if not key_candidate and "names" in err_str.lower():
            key_candidate = "names"

    # Map Pydantic model names to INI sections if applicable
    section_map = {
        "mqtt": "MQTT",
        "image_processing": "ImageProcessing",
        "digital_readout": "Digits",
        "analog_readout": "Analog",
        "poller": "Poller",
        "web": "Web",
        "debug": "Debug",
        "post_processing": "PostProcessing",
        "default": "DEFAULT",
        "alignment": "Alignment",
    }
    if sec_candidate and sec_candidate.lower() in section_map:
        sec_candidate = section_map[sec_candidate.lower()]

    # If no line number was detected directly, resolve line via section and/or key
    if lineno is None and (sec_candidate or key_candidate):
        lineno = find_ini_line(text, section=sec_candidate, key=key_candidate)

    if lineno is None:
        lineno = 1

    # Calculate character offset in document for widget placement
    pos: int = 0
    if lineno and lineno >= 1:
        lines = text.splitlines(keepends=True)
        if lines and lineno <= len(lines):
            pos = sum(len(line) for line in lines[: lineno - 1]) + len(
                lines[lineno - 1].rstrip("\r\n")
            )
        elif lines:
            pos = len(text)
        else:
            pos = 0

    return SyntaxErrorInfo(lineno=lineno, position=pos, message=msg)


def build_syntax_error_decorations(
    text: str, error: Exception
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Build CodeMirror decorations and line tooltips for a syntax error.

    Returns:
        (decorations, line_tooltips)
    """
    err = extract_syntax_error_info(text, error)
    decorations: list[dict[str, Any]] = []
    tooltips = build_line_tooltips(text)

    if err.lineno is not None and err.lineno >= 1:
        decorations.append(
            {
                "kind": "line",
                "line": err.lineno,
                "class": "cm-error-line",
            }
        )
        if err.position is not None:
            short_msg = err.message
            if len(short_msg) > 60:
                short_msg = short_msg[:57] + "..."
            decorations.append(
                {
                    "kind": "widget",
                    "position": err.position,
                    "text": f" ❌ {short_msg}",
                    "class": "cm-error-widget",
                }
            )
        tooltips[err.lineno] = f"❌ Syntax Error: {err.message}"

    return decorations, tooltips
