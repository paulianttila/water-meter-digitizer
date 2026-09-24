"""Main Config class encapsulating application configuration state."""

import configparser
import io
import os
from typing import TextIO

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.exceptions import ConfigurationMissing
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
from config.seed import ensure_config_initialized
from config.serializer import (
    load_cnn_params,
    load_config_from_parser,
    save_config_to_io,
)
from data_classes import MeterConfig
from services.leak.models import ValueType


class Config(BaseSettings):
    """Application configuration model with INI file serialization and env overrides."""

    model_config = SettingsConfigDict(
        env_prefix="METER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    log_level: str = "INFO"
    config_dir: str = "/config"
    data_dir: str = "/data"
    previous_value_file: str = "/config/prevalue.ini"
    digital_models_dir: str = "/config/neuralnets/digital"
    analog_models_dir: str = "/config/neuralnets/analog"
    min_confidence_threshold: float = 60.0
    image_source: ImageSource = Field(default_factory=ImageSource)
    digital_readout: CNNParams = Field(default_factory=CNNParams)
    analog_readout: CNNParams = Field(default_factory=CNNParams)
    alignment: Alignment = Field(default_factory=Alignment)
    meter_configs: list[MeterConfig] = Field(default_factory=list)
    crop: Crop = Field(default_factory=Crop)
    resize: Resize = Field(default_factory=Resize)
    image_processing: ImageProcessing = Field(default_factory=ImageProcessing)
    history: History = Field(default_factory=History)
    snapshots: Snapshots = Field(default_factory=Snapshots)
    poller: Poller = Field(default_factory=Poller)
    mqtt: MQTT = Field(default_factory=MQTT)
    zero_flow_monitor: ZeroFlowMonitor = Field(default_factory=ZeroFlowMonitor)

    @classmethod
    def create_clean_default(
        cls,
        config_dir: str = "/config",
        data_dir: str = "/data",
    ) -> "Config":
        """Construct a pristine default configuration with clean boilerplate values."""
        return cls(
            log_level="INFO",
            config_dir=config_dir,
            data_dir=data_dir,
            digital_models_dir=f"{config_dir}/neuralnets/digital",
            analog_models_dir=f"{config_dir}/neuralnets/analog",
            previous_value_file=f"{config_dir}/prevalue.ini",
            min_confidence_threshold=60.0,
            image_source=ImageSource(url="", timeout=30, min_size=10000),
            crop=Crop(enabled=False, x=0, y=0, w=0, h=0),
            resize=Resize(enabled=False, w=0, h=0),
            image_processing=ImageProcessing(
                enabled=False,
                contrast=1.0,
                brightness=1.0,
                color=1.0,
                sharpness=1.0,
                grayscale=False,
                autocontrast=AutoContrast(
                    enabled=False,
                    cutoff_low=2.0,
                    cutoff_high=45.0,
                    ignore=None,
                ),
                autocontrast_cut_images=AutoContrast(
                    enabled=False,
                    cutoff_low=2.0,
                    cutoff_high=45.0,
                    ignore=None,
                ),
                glare_suppression=GlareSuppression(
                    enabled=False,
                    mode="clahe",
                    inpaint_threshold=230,
                    inpaint_radius=3,
                    clahe_clip_limit=2.0,
                    clahe_grid_size=8,
                    apply_to_cut_images=False,
                ),
            ),
            alignment=Alignment(
                rotate_angle=0.0,
                ref_images=[],
                post_rotate_angle=0.0,
            ),
            meter_configs=[
                MeterConfig(
                    name="total",
                    format="",
                    consistency_enabled=False,
                    allow_negative_rates=False,
                    max_rate_value=0.0,
                    use_previous_value=False,
                    pre_value_from_file_max_age=0,
                    use_extended_resolution=False,
                    unit="",
                )
            ],
            digital_readout=CNNParams(
                enabled=False,
                model_file=f"{config_dir}/neuralnets/digital/class100/dig-class100_0168_s2_q.tflite",
                model="auto",
                cut_images=[],
            ),
            analog_readout=CNNParams(
                enabled=False,
                model_file=f"{config_dir}/neuralnets/analog/continuous/ana-cont_1209_s2.tflite",
                model="auto",
                cut_images=[],
            ),
            poller=Poller(
                enabled=False,
                cron="0 */5 * * * *",
                run_on_startup=True,
                save_images=False,
                retry_interval_seconds=30,
            ),
            mqtt=MQTT(
                enabled=False,
                broker="localhost",
                port=1883,
                username="",
                password="",  # nosec B106
                client_id="water-meter-digitizer",
                topic_prefix="watermeter",
                keepalive=60,
                tls=False,
                retain=True,
                homeassistant_discovery=True,
                discovery_prefix="homeassistant",
                device_name="Water Meter Digitizer",
                device_id="water_meter_digitizer",
            ),
            zero_flow_monitor=ZeroFlowMonitor(
                enabled=False,
                meter_name="total",
                value_type=ValueType.CUMULATIVE,
                continuous_flow_hours=2.0,
                min_leak_volume=0.010,
                flow_threshold=0.001,
                resolve_debounce_count=2,
                max_history_events=50,
            ),
            history=History(
                enabled=True,
                backend="sqlite",
                db_url=f"sqlite:///{data_dir}/history.db",
                max_memory_mb=20.0,
                max_records=50000,
                retention_days=30,
                auto_vacuum=True,
                prune_interval=50,
            ),
            snapshots=Snapshots(
                enabled=True,
                mode="smart_tiered",
                format="webp",
                quality=75,
                max_disk_mb=500.0,
                recent_full_frame_days=2,
                roi_strip_retention_days=14,
                idle_heartbeat_minutes=15,
                always_save_on_anomaly=True,
                storage_dir=f"{data_dir}/snapshots",
            ),
        )

    @staticmethod
    def _deep_merge_dict(target: dict, source: dict) -> None:
        """Recursively merge nested dictionary source into target."""
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                Config._deep_merge_dict(target[key], value)
            else:
                target[key] = value

    def apply_env_overrides(self) -> "Config":
        """Re-apply environment variable overrides (METER_*) on top of loaded configuration."""
        from pydantic_settings import EnvSettingsSource

        source = EnvSettingsSource(
            Config, env_prefix="METER_", env_nested_delimiter="__"
        )
        env_data = source()
        if not env_data:
            return self

        current_data = self.model_dump()
        self._deep_merge_dict(current_data, env_data)
        updated = Config.model_validate(current_data)
        self.__dict__.update(updated.__dict__)
        return self

    def load_from_string(self, config_string: str, apply_env: bool = True) -> "Config":
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=("#", ";"),
        )
        config.read_string(config_string)
        loaded = self.load_config(config)
        if apply_env:
            loaded.apply_env_overrides()
        return loaded

    def save_to_string(self) -> str:
        output = io.StringIO()
        self._save_to_io(output)
        return output.getvalue()

    def load_from_file(
        self,
        ini_file: str = "config.ini",
        auto_seed: bool = True,
        apply_env: bool = True,
    ) -> "Config":
        if not os.path.exists(ini_file) and auto_seed:
            ensure_config_initialized(ini_file)

        if not os.path.exists(ini_file):
            raise ConfigurationMissing(f"Configuration file '{ini_file}' not found")

        ini_dir = os.path.dirname(os.path.abspath(ini_file))
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=("#", ";"),
        )
        config.read(ini_file)

        env_config_dir = os.environ.get("CONFIG_DIR")
        raw_cfg_dir = config.get("DEFAULT", "ConfigDir", fallback="/config").strip()
        if env_config_dir:
            config.set("DEFAULT", "ConfigDir", env_config_dir)
        elif (
            raw_cfg_dir == "/config"
            and not os.path.exists("/config")
            and os.path.exists(ini_dir)
        ):
            config.set("DEFAULT", "ConfigDir", ini_dir)

        loaded = self.load_config(config)
        if apply_env:
            loaded.apply_env_overrides()
        return loaded

    def create_backup(self, ini_file: str = "config.ini", tag: str = "") -> "Config":
        from config.history_manager import ConfigHistoryManager

        ConfigHistoryManager.create_backup(ini_file, tag=tag)
        return self

    def save_to_file(
        self,
        ini_file: str = "config.ini",
        make_backup: bool = False,
        backup_tag: str = "",
    ) -> "Config":
        if make_backup and os.path.exists(ini_file):
            self.create_backup(ini_file, tag=backup_tag)
        with open(ini_file, "w") as configfile:
            self._save_to_io(configfile)
        return self

    def _save_to_io(self, fp: TextIO) -> "Config":
        save_config_to_io(self, fp)
        return self

    def to_ini_string(self) -> str:
        """Serialize configuration model to an INI formatted string."""
        return self.save_to_string()

    @classmethod
    def from_ini_string(cls, ini_text: str, apply_env: bool = True) -> "Config":
        """Create a new Config instance loaded from an INI string."""
        instance = cls()
        return instance.load_from_string(ini_text, apply_env=apply_env)

    def load_config(self, config: configparser.ConfigParser) -> "Config":
        return load_config_from_parser(self, config)

    def load_cnn_params(
        self, section: str, config: configparser.ConfigParser
    ) -> CNNParams:
        """Load CNN readout parameters from an INI section."""
        return load_cnn_params(section, config)
