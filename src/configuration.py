"""Backward-compatibility facade for configuration module.

Re-exports all configuration models and utilities from the modular `config` package.
"""

from config.exceptions import ConfigurationMissing
from config.main import Config
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
from config.paths import format_config_path
from config.seed import (
    copy_default_config,
    ensure_config_initialized,
    find_seed_dir,
    init_profile_for_wizard,
)
from data_classes import ImagePosition, MeterConfig, RefImage

# Aliases for private legacy helpers
_find_seed_dir = find_seed_dir
_format_config_path = format_config_path

__all__ = [
    "MQTT",
    "Alignment",
    "AutoContrast",
    "CNNParams",
    "Config",
    "ConfigurationMissing",
    "Crop",
    "GlareSuppression",
    "History",
    "ImagePosition",
    "ImageProcessing",
    "ImageSource",
    "MeterConfig",
    "Poller",
    "RefImage",
    "Resize",
    "Snapshots",
    "ZeroFlowMonitor",
    "_find_seed_dir",
    "_format_config_path",
    "copy_default_config",
    "ensure_config_initialized",
    "find_seed_dir",
    "format_config_path",
    "init_profile_for_wizard",
]
