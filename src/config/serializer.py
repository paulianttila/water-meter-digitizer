"""Serialization and deserialization between INI files and Pydantic Config models."""

from __future__ import annotations

import configparser
import logging
from typing import TYPE_CHECKING, TextIO

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
from config.paths import format_config_path
from data_classes import ImagePosition, MeterConfig, RefImage
from services.leak.models import ValueType

if TYPE_CHECKING:
    from config.main import Config

logger = logging.getLogger(__name__)


def _safe_getint(
    config: configparser.ConfigParser, section: str, option: str, fallback: int = 0
) -> int:
    try:
        return config.getint(section, option, fallback=fallback)
    except ValueError as e:
        raw_val = config.get(section, option, fallback=None)
        raise ValueError(
            f"Invalid integer value '{raw_val}' for [{section}] -> {option}"
        ) from e


def _safe_getfloat(
    config: configparser.ConfigParser, section: str, option: str, fallback: float = 0.0
) -> float:
    try:
        return config.getfloat(section, option, fallback=fallback)
    except ValueError as e:
        raw_val = config.get(section, option, fallback=None)
        raise ValueError(
            f"Invalid float value '{raw_val}' for [{section}] -> {option}"
        ) from e


def _safe_getboolean(
    config: configparser.ConfigParser, section: str, option: str, fallback: bool = False
) -> bool:
    try:
        return config.getboolean(section, option, fallback=fallback)
    except ValueError as e:
        raw_val = config.get(section, option, fallback=None)
        raise ValueError(
            f"Invalid boolean value '{raw_val}' for [{section}] -> {option}"
        ) from e


def load_cnn_params(section: str, config: configparser.ConfigParser) -> CNNParams:
    """Load CNN readout parameters from an INI section."""
    readout_enabled = _safe_getboolean(config, section, "Enabled", fallback=False)
    model_file = config.get(section, "Modelfile", fallback="")
    model = config.get(section, "Model", fallback="auto").lower()
    detect_negative_sign = _safe_getboolean(
        config, section, "DetectNegativeSign", fallback=False
    )
    images = []
    if readout_enabled:
        names = config.get(section, "names", fallback="")
        if names == "":
            raise ConfigurationMissing(
                f"Section {section} is missing names. "
                f"Please add a comma separated list of names or disable "
                f"the {section} readout."
            )
        for name in [x.strip() for x in names.split(",") if x.strip()]:
            x = _safe_getint(config, f"{section}.{name}", "x", fallback=0)
            y = _safe_getint(config, f"{section}.{name}", "y", fallback=0)
            w = _safe_getint(config, f"{section}.{name}", "w", fallback=0)
            h = _safe_getint(config, f"{section}.{name}", "h", fallback=0)
            images.append(ImagePosition(name=name, x=x, y=y, w=w, h=h))
    return CNNParams(
        enabled=readout_enabled,
        model_file=model_file,
        model=model,
        detect_negative_sign=detect_negative_sign,
        cut_images=images,
    )


def load_config_from_parser(cfg: Config, config: configparser.ConfigParser) -> Config:
    """Populate a Config instance from a parsed ConfigParser."""
    # General Parameters
    cfg.log_level = config.get("DEFAULT", "LogLevel", fallback="INFO")
    cfg.config_dir = config.get("DEFAULT", "ConfigDir", fallback="/config")
    cfg.data_dir = config.get("DEFAULT", "DataDir", fallback="/data")
    cfg.digital_models_dir = config.get(
        "DEFAULT", "DigitalModelsDir", fallback="/config/neuralnets/digital"
    )
    cfg.analog_models_dir = config.get(
        "DEFAULT", "AnalogModelsDir", fallback="/config/neuralnets/analog"
    )
    cfg.previous_value_file = config.get(
        "DEFAULT", "PreviousValueFile", fallback="/config/prevalue.ini"
    )
    cfg.min_confidence_threshold = _safe_getfloat(
        config, "DEFAULT", "MinConfidenceThreshold", fallback=60.0
    )

    # Image Source Parameters
    url = config.get("ImageSource", "URL", fallback="")
    timeout = _safe_getint(config, "ImageSource", "Timeout", fallback=30)
    min_size = _safe_getint(config, "ImageSource", "MinSize", fallback=10000)
    cfg.image_source = ImageSource(
        url=url,
        timeout=timeout,
        min_size=min_size,
    )

    # Digital & Analog ReadOut Parameters
    cfg.digital_readout = load_cnn_params("Digits", config)
    cfg.analog_readout = load_cnn_params("Analog", config)

    # Alignment Parameters
    rotate_angle = _safe_getfloat(config, "Alignment", "RotationAngle", fallback=0.0)
    post_rotate_angle = _safe_getfloat(
        config, "Alignment", "PostRotationAngle", fallback=0.0
    )

    refs = config.get("Alignment", "Refs", fallback="")
    ref_images = []
    for name in [x.strip() for x in refs.split(",") if x.strip()]:
        image = config.get(f"Alignment.{name}", "image", fallback="")
        x = _safe_getint(config, f"Alignment.{name}", "x", fallback=0)
        y = _safe_getint(config, f"Alignment.{name}", "y", fallback=0)
        w = _safe_getint(config, f"Alignment.{name}", "w", fallback=0)
        h = _safe_getint(config, f"Alignment.{name}", "h", fallback=0)
        ref_images.append(RefImage(name=name, x=x, y=y, w=w, h=h, file_name=image))
    cfg.alignment = Alignment(
        rotate_angle=rotate_angle,
        ref_images=ref_images,
        post_rotate_angle=post_rotate_angle,
    )

    # Crop Parameters
    crop_enabled = _safe_getboolean(config, "Crop", "Enabled", fallback=False)
    crop_x = _safe_getint(config, "Crop", "x", fallback=0)
    crop_y = _safe_getint(config, "Crop", "y", fallback=0)
    crop_w = _safe_getint(config, "Crop", "w", fallback=0)
    crop_h = _safe_getint(config, "Crop", "h", fallback=0)
    cfg.crop = Crop(enabled=crop_enabled, x=crop_x, y=crop_y, w=crop_w, h=crop_h)

    # Resize Parameters
    resize_enabled = _safe_getboolean(config, "Resize", "Enabled", fallback=False)
    resize_w = _safe_getint(config, "Resize", "w", fallback=0)
    resize_h = _safe_getint(config, "Resize", "h", fallback=0)
    cfg.resize = Resize(enabled=resize_enabled, w=resize_w, h=resize_h)

    # Image Processing Parameters
    image_processing_enabled = _safe_getboolean(
        config, "ImageProcessing", "Enabled", fallback=False
    )
    image_processing_contrast = _safe_getfloat(
        config, "ImageProcessing", "Contrast", fallback=1.0
    )
    image_processing_brightness = _safe_getfloat(
        config, "ImageProcessing", "Brightness", fallback=1.0
    )
    image_processing_color = _safe_getfloat(
        config, "ImageProcessing", "Color", fallback=1.0
    )
    image_processing_sharpness = _safe_getfloat(
        config, "ImageProcessing", "Sharpness", fallback=1.0
    )
    image_processing_grayscale = _safe_getboolean(
        config, "ImageProcessing", "GrayScale", fallback=False
    )
    image_processing_autocontrast = _safe_getboolean(
        config, "ImageProcessing", "AutoContrast", fallback=False
    )
    image_processing_autocontrast_cutoff_low = _safe_getfloat(
        config, "ImageProcessing", "AutoContrastCutoffLow", fallback=2
    )
    image_processing_autocontrast_cutoff_high = _safe_getfloat(
        config, "ImageProcessing", "AutoContrastCutoffHigh", fallback=45
    )
    val = config.get("ImageProcessing", "AutoContrastIgnore", fallback="None")
    if val == "None":
        image_processing_autocontrast_ignore = None
    else:
        image_processing_autocontrast_ignore = _safe_getint(
            config, "ImageProcessing", "AutoContrastIgnore", fallback=0
        )
    image_processing_autocontrast_cut_images = _safe_getboolean(
        config, "ImageProcessing", "AutoContrastCutImages", fallback=False
    )
    image_processing_autocontrast_cut_images_cutoff_low = _safe_getfloat(
        config, "ImageProcessing", "AutoContrastCutImagesCutoffLow", fallback=2
    )
    image_processing_autocontrast_cut_images_cutoff_high = _safe_getfloat(
        config, "ImageProcessing", "AutoContrastCutImagesCutoffHigh", fallback=45
    )
    val = config.get("ImageProcessing", "AutoContrastCutImagesIgnore", fallback="None")
    if val == "None":
        image_processing_autocontrast_cut_images_ignore = None
    else:
        image_processing_autocontrast_cut_images_ignore = _safe_getint(
            config, "ImageProcessing", "AutoContrastCutImagesIgnore", fallback=0
        )

    glare_enabled = _safe_getboolean(
        config, "ImageProcessing", "GlareSuppressionEnabled", fallback=False
    )
    glare_mode = config.get("ImageProcessing", "GlareSuppressionMode", fallback="clahe")
    glare_inpaint_threshold = _safe_getint(
        config, "ImageProcessing", "GlareInpaintThreshold", fallback=230
    )
    glare_inpaint_radius = _safe_getint(
        config, "ImageProcessing", "GlareInpaintRadius", fallback=3
    )
    glare_clahe_clip_limit = _safe_getfloat(
        config, "ImageProcessing", "GlareClaheClipLimit", fallback=2.0
    )
    glare_clahe_grid_size = _safe_getint(
        config, "ImageProcessing", "GlareClaheGridSize", fallback=8
    )
    glare_apply_to_cut_images = _safe_getboolean(
        config, "ImageProcessing", "GlareApplyToCutImages", fallback=False
    )

    image_processing_gamma = _safe_getfloat(
        config, "ImageProcessing", "Gamma", fallback=1.0
    )
    image_processing_sharpness_mode = config.get(
        "ImageProcessing", "SharpnessMode", fallback="standard"
    ).lower()
    image_processing_unsharp_radius = _safe_getfloat(
        config, "ImageProcessing", "UnsharpRadius", fallback=1.0
    )
    image_processing_unsharp_amount = _safe_getfloat(
        config, "ImageProcessing", "UnsharpAmount", fallback=1.5
    )
    image_processing_unsharp_threshold = _safe_getint(
        config, "ImageProcessing", "UnsharpThreshold", fallback=3
    )
    image_processing_auto_sharpen_cut = _safe_getboolean(
        config, "ImageProcessing", "AutoSharpenCutImages", fallback=False
    )

    cfg.image_processing = ImageProcessing(
        enabled=image_processing_enabled,
        contrast=image_processing_contrast,
        brightness=image_processing_brightness,
        color=image_processing_color,
        sharpness=image_processing_sharpness,
        grayscale=image_processing_grayscale,
        gamma=image_processing_gamma,
        sharpness_mode=image_processing_sharpness_mode,
        unsharp_radius=image_processing_unsharp_radius,
        unsharp_amount=image_processing_unsharp_amount,
        unsharp_threshold=image_processing_unsharp_threshold,
        auto_sharpen_cut_images=image_processing_auto_sharpen_cut,
        autocontrast=AutoContrast(
            enabled=image_processing_autocontrast,
            cutoff_low=image_processing_autocontrast_cutoff_low,
            cutoff_high=image_processing_autocontrast_cutoff_high,
            ignore=image_processing_autocontrast_ignore,
        ),
        autocontrast_cut_images=AutoContrast(
            enabled=image_processing_autocontrast_cut_images,
            cutoff_low=image_processing_autocontrast_cut_images_cutoff_low,
            cutoff_high=image_processing_autocontrast_cut_images_cutoff_high,
            ignore=image_processing_autocontrast_cut_images_ignore,
        ),
        glare_suppression=GlareSuppression(
            enabled=glare_enabled,
            mode=glare_mode,
            inpaint_threshold=glare_inpaint_threshold,
            inpaint_radius=glare_inpaint_radius,
            clahe_clip_limit=glare_clahe_clip_limit,
            clahe_grid_size=glare_clahe_grid_size,
            apply_to_cut_images=glare_apply_to_cut_images,
        ),
    )

    # Meter Parameters
    meter_configs = []
    meter_vals = config.get("Meters", "Names", fallback="")
    for name in [x.strip() for x in meter_vals.split(",") if x.strip()]:
        format_val = config.get(f"Meter.{name}", "Value", fallback="")
        consistency_enabled = _safe_getboolean(
            config, f"Meter.{name}", "ConsistencyEnabled", fallback=False
        )
        allow_negative_rates = _safe_getboolean(
            config, f"Meter.{name}", "AllowNegativeRates", fallback=False
        )
        max_rate_value = _safe_getfloat(
            config, f"Meter.{name}", "MaxRateValue", fallback=0.0
        )
        min_rate_value = _safe_getfloat(
            config, f"Meter.{name}", "MinRateValue", fallback=0.0
        )
        stale_threshold_hours = _safe_getfloat(
            config, f"Meter.{name}", "StaleThresholdHours", fallback=0.0
        )
        use_previous_value = _safe_getboolean(
            config, f"Meter.{name}", "UsePreviousValue", fallback=False
        ) or _safe_getboolean(
            config, f"Meter.{name}", "UsePreviuosValue", fallback=False
        )
        pre_value_from_file_max_age = _safe_getint(
            config, f"Meter.{name}", "PreValueFromFileMaxAge", fallback=0
        )
        use_extended_resolution = _safe_getboolean(
            config, f"Meter.{name}", "UseExtendedResolution", fallback=False
        )
        unit = config.get(f"Meter.{name}", "Unit", fallback=None)
        detect_neg_meter = _safe_getboolean(
            config, f"Meter.{name}", "DetectNegativeSign", fallback=False
        )
        quality_high_min_confidence = _safe_getfloat(
            config,
            f"Meter.{name}",
            "QualityHighMinConfidence",
            fallback=_safe_getfloat(
                config, "Meters", "QualityHighMinConfidence", fallback=80.0
            ),
        )
        quality_high_avg_confidence = _safe_getfloat(
            config,
            f"Meter.{name}",
            "QualityHighAvgConfidence",
            fallback=_safe_getfloat(
                config, "Meters", "QualityHighAvgConfidence", fallback=85.0
            ),
        )
        quality_warning_min_confidence = _safe_getfloat(
            config,
            f"Meter.{name}",
            "QualityWarningMinConfidence",
            fallback=_safe_getfloat(
                config, "Meters", "QualityWarningMinConfidence", fallback=60.0
            ),
        )
        quality_warning_avg_confidence = _safe_getfloat(
            config,
            f"Meter.{name}",
            "QualityWarningAvgConfidence",
            fallback=_safe_getfloat(
                config, "Meters", "QualityWarningAvgConfidence", fallback=65.0
            ),
        )

        if consistency_enabled and max_rate_value <= 0:
            logger.warning(
                "Meter '%s': ConsistencyEnabled is True but MaxRateValue is 0 (or unset). "
                "Rate-of-change check is disabled; only negative-rate check will be enforced.",
                name,
            )

        if (
            consistency_enabled
            and min_rate_value > 0
            and max_rate_value > 0
            and min_rate_value > max_rate_value
        ):
            logger.warning(
                "Meter '%s': MinRateValue (%.3f) is greater than MaxRateValue (%.3f).",
                name,
                min_rate_value,
                max_rate_value,
            )

        meter_configs.append(
            MeterConfig(
                name=name,
                format=format_val,
                consistency_enabled=consistency_enabled,
                allow_negative_rates=allow_negative_rates,
                max_rate_value=max_rate_value,
                min_rate_value=min_rate_value,
                stale_threshold_hours=stale_threshold_hours,
                use_previous_value=use_previous_value,
                pre_value_from_file_max_age=pre_value_from_file_max_age,
                use_extended_resolution=use_extended_resolution,
                unit=unit if unit is not None else "",
                detect_negative_sign=detect_neg_meter,
                quality_high_min_confidence=quality_high_min_confidence,
                quality_high_avg_confidence=quality_high_avg_confidence,
                quality_warning_min_confidence=quality_warning_min_confidence,
                quality_warning_avg_confidence=quality_warning_avg_confidence,
            )
        )
    cfg.meter_configs = meter_configs

    # History / Storage Parameters
    history_enabled = _safe_getboolean(config, "History", "Enabled", fallback=True)
    history_backend = config.get("History", "Backend", fallback="sqlite")
    db_url = config.get("History", "DBUrl", fallback="")
    max_memory_mb = _safe_getfloat(config, "History", "MaxMemoryMB", fallback=20.0)
    max_records = _safe_getint(config, "History", "MaxRecords", fallback=50000)
    retention_days = _safe_getint(config, "History", "RetentionDays", fallback=30)
    auto_vacuum = _safe_getboolean(config, "History", "AutoVacuum", fallback=True)
    prune_interval = _safe_getint(config, "History", "PruneInterval", fallback=50)

    if not db_url:
        if history_backend.lower() == "memory":
            db_url = "sqlite:///:memory:"
        else:
            db_url = f"sqlite:///{cfg.data_dir}/history.db"

    cfg.history = History(
        enabled=history_enabled,
        backend=history_backend,
        db_url=db_url,
        max_memory_mb=max_memory_mb,
        max_records=max_records,
        retention_days=retention_days,
        auto_vacuum=auto_vacuum,
        prune_interval=prune_interval,
    )

    # Poller Parameters
    cfg.poller = Poller(
        enabled=_safe_getboolean(config, "Poller", "Enabled", fallback=False),
        cron=config.get("Poller", "Cron", fallback="0 */5 * * * *").strip(),
        run_on_startup=_safe_getboolean(
            config, "Poller", "RunOnStartup", fallback=True
        ),
        save_images=_safe_getboolean(config, "Poller", "SaveImages", fallback=False),
        retry_interval_seconds=_safe_getint(
            config, "Poller", "RetryIntervalSeconds", fallback=30
        ),
        consensus_reads=_safe_getint(config, "Poller", "ConsensusReads", fallback=1),
    )

    # MQTT Parameters
    raw_protocol = config.get("MQTT", "Protocol", fallback="3.1.1").strip()
    if raw_protocol not in ("3.1.1", "5.0", "3.1"):
        raw_protocol = "3.1.1"

    cfg.mqtt = MQTT(
        enabled=_safe_getboolean(config, "MQTT", "Enabled", fallback=False),
        broker=config.get("MQTT", "Broker", fallback="localhost"),
        port=_safe_getint(config, "MQTT", "Port", fallback=1883),
        username=config.get("MQTT", "Username", fallback=""),
        password=config.get("MQTT", "Password", fallback=""),
        client_id=config.get("MQTT", "ClientID", fallback="water-meter-digitizer"),
        topic_prefix=config.get("MQTT", "TopicPrefix", fallback="watermeter"),
        keepalive=_safe_getint(config, "MQTT", "KeepAlive", fallback=60),
        tls=_safe_getboolean(config, "MQTT", "TLS", fallback=False),
        tls_ca_cert=config.get("MQTT", "TLS_CACert", fallback=""),
        tls_insecure=_safe_getboolean(config, "MQTT", "TLS_Insecure", fallback=False),
        tls_certfile=config.get("MQTT", "TLS_CertFile", fallback=""),
        tls_keyfile=config.get("MQTT", "TLS_KeyFile", fallback=""),
        tls_psk_identity=config.get("MQTT", "TLS_PSK_Identity", fallback=""),
        tls_psk=config.get("MQTT", "TLS_PSK", fallback=""),
        tls_psk_file=config.get("MQTT", "TLS_PSK_File", fallback=""),
        tls_ciphers=config.get("MQTT", "TLS_Ciphers", fallback=""),
        qos=max(0, min(2, _safe_getint(config, "MQTT", "QoS", fallback=1))),
        clean_session=_safe_getboolean(config, "MQTT", "CleanSession", fallback=True),
        protocol=raw_protocol,
        retain=_safe_getboolean(config, "MQTT", "Retain", fallback=True),
        homeassistant_discovery=_safe_getboolean(
            config, "MQTT", "HomeAssistantDiscovery", fallback=True
        ),
        discovery_prefix=config.get(
            "MQTT", "DiscoveryPrefix", fallback="homeassistant"
        ),
        device_name=config.get("MQTT", "DeviceName", fallback="Water Meter Digitizer"),
        device_id=config.get("MQTT", "DeviceID", fallback="water_meter_digitizer"),
    )

    # Zero-Flow & Leak Monitor Parameters
    raw_val_type = config.get(
        "ZeroFlowMonitor", "ValueType", fallback="cumulative"
    ).lower()
    val_type = (
        ValueType.FLOW_RATE
        if raw_val_type in ("flow_rate", "flow", "rate")
        else ValueType.CUMULATIVE
    )

    cfg.zero_flow_monitor = ZeroFlowMonitor(
        enabled=_safe_getboolean(config, "ZeroFlowMonitor", "Enabled", fallback=False),
        meter_name=config.get("ZeroFlowMonitor", "MeterName", fallback="total"),
        value_type=val_type,
        continuous_flow_hours=_safe_getfloat(
            config, "ZeroFlowMonitor", "ContinuousFlowHours", fallback=2.0
        ),
        min_leak_volume=_safe_getfloat(
            config, "ZeroFlowMonitor", "MinLeakVolume", fallback=0.010
        ),
        flow_threshold=_safe_getfloat(
            config, "ZeroFlowMonitor", "FlowThreshold", fallback=0.001
        ),
        resolve_debounce_count=_safe_getint(
            config, "ZeroFlowMonitor", "ResolveDebounceCount", fallback=2
        ),
        max_history_events=_safe_getint(
            config, "ZeroFlowMonitor", "MaxHistoryEvents", fallback=50
        ),
    )

    # Snapshots Parameters
    snapshot_dir = config.get(
        "Snapshots", "StorageDir", fallback=f"{cfg.data_dir}/snapshots"
    )
    cfg.snapshots = Snapshots(
        enabled=_safe_getboolean(config, "Snapshots", "Enabled", fallback=True),
        mode=config.get("Snapshots", "Mode", fallback="smart_tiered").lower(),
        format=config.get("Snapshots", "Format", fallback="webp").lower(),
        quality=_safe_getint(config, "Snapshots", "Quality", fallback=75),
        max_disk_mb=_safe_getfloat(config, "Snapshots", "MaxDiskMB", fallback=500.0),
        recent_full_frame_days=_safe_getint(
            config, "Snapshots", "RecentFullFrameDays", fallback=2
        ),
        roi_strip_retention_days=_safe_getint(
            config, "Snapshots", "RoiStripRetentionDays", fallback=14
        ),
        idle_heartbeat_minutes=_safe_getint(
            config, "Snapshots", "IdleHeartbeatMinutes", fallback=15
        ),
        always_save_on_anomaly=_safe_getboolean(
            config, "Snapshots", "AlwaysSaveOnAnomaly", fallback=True
        ),
        storage_dir=snapshot_dir,
    )

    return cfg


def save_config_to_io(cfg: Config, fp: TextIO) -> None:
    """Serialize a Config instance into an INI stream."""
    config = configparser.ConfigParser()
    config.optionxform = str  # type: ignore[method-assign,assignment]
    config["DEFAULT"] = {
        "LogLevel": cfg.log_level,
        "ConfigDir": cfg.config_dir,
        "DataDir": format_config_path(cfg.data_dir, config_dir=cfg.config_dir),
        "DigitalModelsDir": format_config_path(
            cfg.digital_models_dir,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
        "AnalogModelsDir": format_config_path(
            cfg.analog_models_dir,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
        "PreviousValueFile": format_config_path(
            cfg.previous_value_file,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
        "MinConfidenceThreshold": str(cfg.min_confidence_threshold),
    }

    config["ImageSource"] = {
        "URL": format_config_path(
            cfg.image_source.url,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
        "Timeout": str(cfg.image_source.timeout),
        "MinSize": str(cfg.image_source.min_size),
    }

    config["Crop"] = {
        "Enabled": str(cfg.crop.enabled),
        "x": str(cfg.crop.x),
        "y": str(cfg.crop.y),
        "w": str(cfg.crop.w),
        "h": str(cfg.crop.h),
    }

    config["Resize"] = {
        "Enabled": str(cfg.resize.enabled),
        "w": str(cfg.resize.w),
        "h": str(cfg.resize.h),
    }

    config["ImageProcessing"] = {
        "Enabled": str(cfg.image_processing.enabled),
        "Contrast": str(cfg.image_processing.contrast),
        "Brightness": str(cfg.image_processing.brightness),
        "Color": str(cfg.image_processing.color),
        "Sharpness": str(cfg.image_processing.sharpness),
        "GrayScale": str(cfg.image_processing.grayscale),
        "Gamma": str(cfg.image_processing.gamma),
        "SharpnessMode": cfg.image_processing.sharpness_mode,
        "UnsharpRadius": str(cfg.image_processing.unsharp_radius),
        "UnsharpAmount": str(cfg.image_processing.unsharp_amount),
        "UnsharpThreshold": str(cfg.image_processing.unsharp_threshold),
        "AutoSharpenCutImages": str(cfg.image_processing.auto_sharpen_cut_images),
        "AutoContrast": str(cfg.image_processing.autocontrast.enabled),
        "AutoContrastCutoffLow": str(cfg.image_processing.autocontrast.cutoff_low),
        "AutoContrastCutoffHigh": str(cfg.image_processing.autocontrast.cutoff_high),
        "AutoContrastIgnore": str(cfg.image_processing.autocontrast.ignore),
        "AutoContrastCutImages": str(
            cfg.image_processing.autocontrast_cut_images.enabled
        ),
        "AutoContrastCutImagesCutoffLow": str(
            cfg.image_processing.autocontrast_cut_images.cutoff_low
        ),
        "AutoContrastCutImagesCutoffHigh": str(
            cfg.image_processing.autocontrast_cut_images.cutoff_high
        ),
        "AutoContrastCutImagesIgnore": str(
            cfg.image_processing.autocontrast_cut_images.ignore
        ),
        "GlareSuppressionEnabled": str(cfg.image_processing.glare_suppression.enabled),
        "GlareSuppressionMode": cfg.image_processing.glare_suppression.mode,
        "GlareInpaintThreshold": str(
            cfg.image_processing.glare_suppression.inpaint_threshold
        ),
        "GlareInpaintRadius": str(
            cfg.image_processing.glare_suppression.inpaint_radius
        ),
        "GlareClaheClipLimit": str(
            cfg.image_processing.glare_suppression.clahe_clip_limit
        ),
        "GlareClaheGridSize": str(
            cfg.image_processing.glare_suppression.clahe_grid_size
        ),
        "GlareApplyToCutImages": str(
            cfg.image_processing.glare_suppression.apply_to_cut_images
        ),
    }

    config["Alignment"] = {
        "RotationAngle": str(cfg.alignment.rotate_angle),
        "Refs": ", ".join([ref.name for ref in cfg.alignment.ref_images]),
        "PostRotationAngle": str(cfg.alignment.post_rotate_angle),
    }

    for ref in cfg.alignment.ref_images:
        config[f"Alignment.{ref.name}"] = {
            "Image": format_config_path(
                ref.file_name,
                config_dir=cfg.config_dir,
                data_dir=cfg.data_dir,
            ),
            "x": str(ref.x),
            "y": str(ref.y),
            "w": str(ref.w),
            "h": str(ref.h),
        }

    config["Meters"] = {
        "Names": ", ".join([meter.name for meter in cfg.meter_configs]),
    }

    for meter in cfg.meter_configs:
        config[f"Meter.{meter.name}"] = {
            "Value": meter.format,
            "ConsistencyEnabled": str(meter.consistency_enabled),
            "AllowNegativeRates": str(meter.allow_negative_rates),
            "MaxRateValue": str(meter.max_rate_value),
            "MinRateValue": str(meter.min_rate_value),
            "StaleThresholdHours": str(meter.stale_threshold_hours),
            "UsePreviousValue": str(meter.use_previous_value),
            "PreValueFromFileMaxAge": str(meter.pre_value_from_file_max_age),
            "UseExtendedResolution": str(meter.use_extended_resolution),
            "Unit": meter.unit if meter.unit is not None else "",
            "DetectNegativeSign": str(meter.detect_negative_sign),
            "QualityHighMinConfidence": str(meter.quality_high_min_confidence),
            "QualityHighAvgConfidence": str(meter.quality_high_avg_confidence),
            "QualityWarningMinConfidence": str(meter.quality_warning_min_confidence),
            "QualityWarningAvgConfidence": str(meter.quality_warning_avg_confidence),
        }

    config["Digits"] = {
        "Enabled": str(
            bool(cfg.digital_readout.enabled and cfg.digital_readout.cut_images)
        ),
        "ModelFile": format_config_path(
            cfg.digital_readout.model_file,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
            digital_models_dir=cfg.digital_models_dir,
        ),
        "Model": cfg.digital_readout.model,
        "DetectNegativeSign": str(cfg.digital_readout.detect_negative_sign),
        "Names": ", ".join([image.name for image in cfg.digital_readout.cut_images]),
    }

    config["Analog"] = {
        "Enabled": str(
            bool(cfg.analog_readout.enabled and cfg.analog_readout.cut_images)
        ),
        "ModelFile": format_config_path(
            cfg.analog_readout.model_file,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
            analog_models_dir=cfg.analog_models_dir,
        ),
        "Model": cfg.analog_readout.model,
        "Names": ", ".join([image.name for image in cfg.analog_readout.cut_images]),
    }

    for analog in cfg.analog_readout.cut_images:
        config[f"Analog.{analog.name}"] = {
            "x": str(analog.x),
            "y": str(analog.y),
            "w": str(analog.w),
            "h": str(analog.h),
        }

    for digital in cfg.digital_readout.cut_images:
        config[f"Digits.{digital.name}"] = {
            "x": str(digital.x),
            "y": str(digital.y),
            "w": str(digital.w),
            "h": str(digital.h),
        }

    config["History"] = {
        "Enabled": str(cfg.history.enabled),
        "Backend": cfg.history.backend,
        "DBUrl": format_config_path(
            cfg.history.db_url,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
        "MaxMemoryMB": str(cfg.history.max_memory_mb),
        "MaxRecords": str(cfg.history.max_records),
        "RetentionDays": str(cfg.history.retention_days),
        "AutoVacuum": str(cfg.history.auto_vacuum),
        "PruneInterval": str(cfg.history.prune_interval),
    }

    config["Poller"] = {
        "Enabled": str(cfg.poller.enabled),
        "Cron": cfg.poller.cron,
        "RunOnStartup": str(cfg.poller.run_on_startup),
        "SaveImages": str(cfg.poller.save_images),
        "RetryIntervalSeconds": str(cfg.poller.retry_interval_seconds),
        "ConsensusReads": str(cfg.poller.consensus_reads),
    }

    config["MQTT"] = {
        "Enabled": str(cfg.mqtt.enabled),
        "Broker": cfg.mqtt.broker,
        "Port": str(cfg.mqtt.port),
        "Username": cfg.mqtt.username,
        "Password": cfg.mqtt.password,
        "ClientID": cfg.mqtt.client_id,
        "TopicPrefix": cfg.mqtt.topic_prefix,
        "KeepAlive": str(cfg.mqtt.keepalive),
        "TLS": str(cfg.mqtt.tls),
        "TLS_CACert": cfg.mqtt.tls_ca_cert,
        "TLS_Insecure": str(cfg.mqtt.tls_insecure),
        "TLS_CertFile": cfg.mqtt.tls_certfile,
        "TLS_KeyFile": cfg.mqtt.tls_keyfile,
        "TLS_PSK_Identity": cfg.mqtt.tls_psk_identity,
        "TLS_PSK": cfg.mqtt.tls_psk,
        "TLS_PSK_File": cfg.mqtt.tls_psk_file,
        "TLS_Ciphers": cfg.mqtt.tls_ciphers,
        "QoS": str(cfg.mqtt.qos),
        "CleanSession": str(cfg.mqtt.clean_session),
        "Protocol": cfg.mqtt.protocol,
        "Retain": str(cfg.mqtt.retain),
        "HomeAssistantDiscovery": str(cfg.mqtt.homeassistant_discovery),
        "DiscoveryPrefix": cfg.mqtt.discovery_prefix,
        "DeviceName": cfg.mqtt.device_name,
        "DeviceID": cfg.mqtt.device_id,
    }

    config["ZeroFlowMonitor"] = {
        "Enabled": str(cfg.zero_flow_monitor.enabled),
        "MeterName": cfg.zero_flow_monitor.meter_name,
        "ValueType": (
            cfg.zero_flow_monitor.value_type.value
            if isinstance(cfg.zero_flow_monitor.value_type, ValueType)
            else str(cfg.zero_flow_monitor.value_type)
        ),
        "ContinuousFlowHours": str(cfg.zero_flow_monitor.continuous_flow_hours),
        "MinLeakVolume": str(cfg.zero_flow_monitor.min_leak_volume),
        "FlowThreshold": str(cfg.zero_flow_monitor.flow_threshold),
        "ResolveDebounceCount": str(cfg.zero_flow_monitor.resolve_debounce_count),
        "MaxHistoryEvents": str(cfg.zero_flow_monitor.max_history_events),
    }

    config["Snapshots"] = {
        "Enabled": str(cfg.snapshots.enabled),
        "Mode": cfg.snapshots.mode,
        "Format": cfg.snapshots.format,
        "Quality": str(cfg.snapshots.quality),
        "MaxDiskMB": str(cfg.snapshots.max_disk_mb),
        "RecentFullFrameDays": str(cfg.snapshots.recent_full_frame_days),
        "RoiStripRetentionDays": str(cfg.snapshots.roi_strip_retention_days),
        "IdleHeartbeatMinutes": str(cfg.snapshots.idle_heartbeat_minutes),
        "AlwaysSaveOnAnomaly": str(cfg.snapshots.always_save_on_anomaly),
        "StorageDir": format_config_path(
            cfg.snapshots.storage_dir,
            config_dir=cfg.config_dir,
            data_dir=cfg.data_dir,
        ),
    }

    config.write(fp, space_around_delimiters=False)
