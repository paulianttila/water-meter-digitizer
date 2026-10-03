import os
from typing import Any, Literal

import croniter
from pydantic import BaseModel, Field, field_validator, model_validator

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
    full_image: bool = False
    cut_images: bool = False
    mode: str = "clahe"  # "clahe", "inpaint", "illumination_normalize", "combined"
    inpaint_threshold: int = 230
    inpaint_radius: int = 3
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8

    @model_validator(mode="before")
    @classmethod
    def _map_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "enabled" in data and "full_image" not in data:
                data["full_image"] = data.pop("enabled")
            if "apply_to_cut_images" in data and "cut_images" not in data:
                data["cut_images"] = data.pop("apply_to_cut_images")
        return data

    @property
    def enabled(self) -> bool:
        return self.full_image or self.cut_images

    @enabled.setter
    def enabled(self, val: bool) -> None:
        self.full_image = val

    @property
    def apply_to_cut_images(self) -> bool:
        return self.cut_images

    @apply_to_cut_images.setter
    def apply_to_cut_images(self, val: bool) -> None:
        self.cut_images = val


class Denoise(BaseModel):
    full_image: bool = False
    cut_images: bool = False
    method: str = "bilateral"  # "bilateral", "nlmeans", "median", "median_bilateral"
    diameter: int = 5
    sigma_color: float = 50.0
    sigma_space: float = 50.0
    strength: float = 7.0
    template_window: int = 7
    search_window: int = 15

    @model_validator(mode="before")
    @classmethod
    def _map_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "enabled" in data and "full_image" not in data:
                data["full_image"] = data.pop("enabled")
            if "apply_to_cut_images" in data and "cut_images" not in data:
                data["cut_images"] = data.pop("apply_to_cut_images")
        return data

    @property
    def enabled(self) -> bool:
        return self.full_image or self.cut_images

    @enabled.setter
    def enabled(self, val: bool) -> None:
        self.full_image = val

    @property
    def apply_to_cut_images(self) -> bool:
        return self.cut_images

    @apply_to_cut_images.setter
    def apply_to_cut_images(self, val: bool) -> None:
        self.cut_images = val


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
    denoise: Denoise = Field(default_factory=Denoise)


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
    cron: str = "0 */5 * * * *"
    run_on_startup: bool = True
    save_images: bool = False
    retry_interval_seconds: int = 30
    consensus_reads: int = Field(default=1, ge=1, le=10)

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Poller cron expression cannot be empty")
        v_clean = v.strip()
        if not croniter.croniter.is_valid(v_clean, second_at_beginning=True):
            raise ValueError(f"Invalid cron expression: '{v_clean}'")
        return v_clean


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
    tls_ca_cert: str = ""
    tls_insecure: bool = False
    tls_certfile: str = ""
    tls_keyfile: str = ""
    tls_psk_identity: str = ""
    tls_psk: str = ""
    tls_psk_file: str = ""
    tls_ciphers: str = ""
    qos: int = Field(default=1, ge=0, le=2)
    clean_session: bool = True
    protocol: Literal["3.1.1", "5.0", "3.1"] = "3.1.1"
    retain: bool = True
    homeassistant_discovery: bool = True
    discovery_prefix: str = "homeassistant"
    device_name: str = "Water Meter Digitizer"
    device_id: str = "water_meter_digitizer"

    def get_resolved_psk(self) -> str:
        """Resolve PSK secret from direct value or Docker secret file."""
        if self.tls_psk:
            return self.tls_psk.strip()
        if self.tls_psk_file and os.path.exists(self.tls_psk_file):
            with open(self.tls_psk_file, encoding="utf-8") as f:
                return f.read().strip()
        return ""


class ZeroFlowMonitor(BaseModel):
    enabled: bool = False
    meter_name: str = "total"
    value_type: ValueType = ValueType.CUMULATIVE
    continuous_flow_hours: float = 2.0
    min_leak_volume: float = 0.010
    flow_threshold: float = 0.001
    resolve_debounce_count: int = 2
    max_history_events: int = 50
