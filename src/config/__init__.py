"""Configuration package for water-meter-digitizer."""

from config.exceptions import ConfigurationMissing
from config.history_manager import BackupEntry, ConfigHistoryManager
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
from config.seed import ensure_config_initialized, find_seed_dir
from data_classes import ImagePosition, MeterConfig, RefImage

__all__ = [
    "MQTT",
    "Alignment",
    "AutoContrast",
    "BackupEntry",
    "CNNParams",
    "Config",
    "ConfigHistoryManager",
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
    "ensure_config_initialized",
    "find_seed_dir",
    "format_config_path",
]
