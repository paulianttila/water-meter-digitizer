"""Pydantic data models for configuration sections."""

from pydantic import BaseModel, Field

from data_classes import ImagePosition, RefImage
from services.leak.models import ValueType


class ImageSource(BaseModel):
    url: str = ""
    timeout: int = 30
    min_size: int = 10000


class CNNParams(BaseModel):
    enabled: bool = False
    model_file: str = ""
    model: str = ""
    detect_negative_sign: bool = False
    cut_images: list[ImagePosition] = Field(default_factory=list)


class Alignment(BaseModel):
    rotate_angle: float = 0.0
    ref_images: list[RefImage] = Field(default_factory=list)
    post_rotate_angle: float = 0.0


class Crop(BaseModel):
    enabled: bool = False
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class Resize(BaseModel):
    enabled: bool = False
    w: int = 0
    h: int = 0


class AutoContrast(BaseModel):
    enabled: bool = False
    cutoff_low: float = 2.0
    cutoff_high: float = 45.0
    ignore: int | None = None


class GlareSuppression(BaseModel):
    enabled: bool = False
    mode: str = "clahe"  # "clahe", "inpaint", "illumination_normalize", "combined"
    inpaint_threshold: int = 230
    inpaint_radius: int = 3
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    apply_to_cut_images: bool = False


class ImageProcessing(BaseModel):
    enabled: bool = False
    contrast: float = 1.0
    brightness: float = 1.0
    color: float = 1.0
    sharpness: float = 1.0
    grayscale: bool = False
    gamma: float = 1.0
    sharpness_mode: str = "standard"  # "standard", "unsharp_mask", "auto"
    unsharp_radius: float = 1.0
    unsharp_amount: float = 1.5
    unsharp_threshold: int = 3
    auto_sharpen_cut_images: bool = False
    autocontrast: AutoContrast = Field(default_factory=AutoContrast)
    autocontrast_cut_images: AutoContrast = Field(default_factory=AutoContrast)
    glare_suppression: GlareSuppression = Field(default_factory=GlareSuppression)


class History(BaseModel):
    enabled: bool = True
    backend: str = "sqlite"
    db_url: str = ""
    max_memory_mb: float = 20.0
    max_records: int = 50000
    retention_days: int = 30
    auto_vacuum: bool = True
    prune_interval: int = 50


class Snapshots(BaseModel):
    enabled: bool = True
    mode: str = (
        "smart_tiered"  # "smart_tiered", "change_only", "roi_strips_only", "full_frames", "disabled"
    )
    format: str = "webp"  # "webp", "jpeg"
    quality: int = 75
    max_disk_mb: float = 500.0
    recent_full_frame_days: int = 2
    roi_strip_retention_days: int = 14
    idle_heartbeat_minutes: int = 15
    always_save_on_anomaly: bool = True
    storage_dir: str = "/data/snapshots"


class Poller(BaseModel):
    enabled: bool = False
    interval_seconds: int = 300
    sync_to_clock: bool = True
    run_on_startup: bool = True
    save_images: bool = False
    retry_interval_seconds: int = 30
    consensus_reads: int = Field(default=1, ge=1, le=10)


class MQTT(BaseModel):
    enabled: bool = False
    broker: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "water-meter-digitizer"
    topic_prefix: str = "watermeter"
    keepalive: int = 60
    tls: bool = False
    retain: bool = True
    homeassistant_discovery: bool = True
    discovery_prefix: str = "homeassistant"
    device_name: str = "Water Meter Digitizer"
    device_id: str = "water_meter_digitizer"


class ZeroFlowMonitor(BaseModel):
    enabled: bool = False
    meter_name: str = "total"
    value_type: ValueType = ValueType.CUMULATIVE
    continuous_flow_hours: float = 2.0
    min_leak_volume: float = 0.010
    flow_threshold: float = 0.001
    resolve_debounce_count: int = 2
    max_history_events: int = 50
