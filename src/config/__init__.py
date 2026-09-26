"""Configuration package for water-meter-digitizer."""

from config.exceptions import ConfigurationMissing
from config.history_manager import BackupEntry, ConfigHistoryManager
from config.main import Config
from config.meter_presets import (
    DEFAULT_BUILTIN_PRESETS,
    MeterTypePreset,
    clear_presets_cache,
    get_available_template_images,
    get_preset_by_id,
    load_meter_presets,
    reload_meter_presets,
    sort_meter_presets,
)
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

__all__ = [
    "DEFAULT_BUILTIN_PRESETS",
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
    "MeterTypePreset",
    "Poller",
    "RefImage",
    "Resize",
    "Snapshots",
    "ZeroFlowMonitor",
    "clear_presets_cache",
    "copy_default_config",
    "ensure_config_initialized",
    "find_seed_dir",
    "format_config_path",
    "get_available_template_images",
    "get_preset_by_id",
    "init_profile_for_wizard",
    "load_meter_presets",
    "reload_meter_presets",
    "sort_meter_presets",
]
