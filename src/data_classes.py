import re
from typing import Any

from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImagePosition(BaseModel):
    name: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class RefImage(ImagePosition):
    file_name: str = ""


class MeterConfig(BaseModel):
    name: str
    format: str
    consistency_enabled: bool = False
    allow_negative_rates: bool = False
    max_rate_value: float = 0.0
    min_rate_value: float = 0.0
    stale_threshold_hours: float = 0.0
    use_previous_value: bool = False
    pre_value_from_file_max_age: int = 0
    use_extended_resolution: bool = False
    unit: str = ""
    detect_negative_sign: bool = False

    @property
    def value_names(self) -> list[str]:
        return re.findall(r"\{(.*?)\}", self.format)


INVALID_DIGIT = "?"


class CutImageOptions(BaseModel):
    autocontrast: bool = False
    cutoff_low: float = Field(default=2.0, ge=0.0, le=100.0)
    cutoff_high: float = Field(default=45.0, ge=0.0, le=100.0)
    ignore: int | None = Field(default=2, ge=0, le=255)
    glare_suppression: bool = False
    glare_mode: str = "clahe"
    glare_inpaint_threshold: int = Field(default=230, ge=0, le=255)
    glare_inpaint_radius: int = Field(default=3, ge=1, le=50)
    glare_clahe_clip_limit: float = Field(default=2.0, ge=0.1, le=40.0)
    glare_clahe_grid_size: int = Field(default=8, ge=1, le=64)
    unsharp: bool = False
    unsharp_radius: float = Field(default=1.0, ge=0.1, le=20.0)
    unsharp_amount: float = Field(default=1.5, ge=0.0, le=10.0)
    unsharp_threshold: int = Field(default=3, ge=0, le=255)

    @model_validator(mode="after")
    def validate_cutoffs(self) -> "CutImageOptions":
        if self.cutoff_low + self.cutoff_high >= 100.0:
            raise ValueError(
                f"Sum of cutoff_low ({self.cutoff_low}) and cutoff_high ({self.cutoff_high}) must be less than 100"
            )
        return self


class CutImage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    image: Image


class CameraHealth(BaseModel):
    url: str = ""
    reachable: bool = False
    latency_ms: float | None = None
    status_code: int | None = None
    error: str | None = None


class MemoryHealth(BaseModel):
    rss_mb: float = 0.0
    peak_rss_mb: float = 0.0
    platform: str = ""


class CacheHealth(BaseModel):
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_ratio_percent: float = 0.0
    current_size: int = 0
    max_size: int = 0
    ttl_seconds: float = 0.0
    cached_keys: list[str] = []


class ModelMetrics(BaseModel):
    inferences: int = 0
    avg_inference_ms: float | None = None
    min_inference_ms: float | None = None
    max_inference_ms: float | None = None
    last_inference_ms: float | None = None
    last_inference_at: str | None = None
    pool_size: int = 0
    created_instances: int = 0
    available_instances: int = 0
    active_inferences: int = 0
    input_shape: list[int] | None = None
    output_shape: list[int] | None = None
    quantized: bool = False


class ModelHealth(BaseModel):
    enabled: bool = False
    path: str = ""
    exists: bool = False
    size_bytes: int | None = None
    metrics: ModelMetrics | None = None


class ModelsHealth(BaseModel):
    digital: ModelHealth
    analog: ModelHealth
    total_inferences: int = 0
    avg_inference_ms: float | None = None


class UptimeHealth(BaseModel):
    uptime_seconds: float = 0.0
    uptime_human: str = "0s"
    started_at: str = ""


class SystemHealth(BaseModel):
    version: str = ""
    python_version: str = ""
    platform: str = ""


class DictAccessMixin:
    """Backward-compatibility mixin providing dict subscripting and .get() on Pydantic models.

    .. note:: Technical Debt / Migration Guidance
        This mixin allows legacy code and templates expecting dictionary-like access
        (e.g. `model["field"]`, `model.get("field")`, `'field' in model`) to operate on
        Pydantic v2 `BaseModel` instances without immediate refactoring.

        For new code:
        - Prefer direct typed attribute access: `model.field`
        - For dictionary serialization: use `model.model_dump()`
        - For dynamic attribute lookup: use `getattr(model, "field", default)`
    """

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class HealthResponse(BaseModel, DictAccessMixin):
    status: str = "healthy"  # "healthy", "degraded", or "unhealthy"
    uptime: UptimeHealth = Field(default_factory=UptimeHealth)
    camera: CameraHealth = Field(default_factory=CameraHealth)
    memory: MemoryHealth = Field(default_factory=MemoryHealth)
    cache: CacheHealth = Field(default_factory=CacheHealth)
    models: ModelsHealth = Field(
        default_factory=lambda: ModelsHealth(
            digital=ModelHealth(), analog=ModelHealth()
        )
    )
    system: SystemHealth = Field(default_factory=SystemHealth)


class PollerStatus(BaseModel, DictAccessMixin):
    enabled: bool = False
    running: bool = False
    is_polling: bool = False
    interval_seconds: int = 300
    last_run: str | None = None
    next_run: str | None = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_error: str = ""


class MQTTStatus(BaseModel, DictAccessMixin):
    enabled: bool = False
    connected: bool = False
    broker: str = "localhost"
    port: int = 1883
    topic_prefix: str = "watermeter"
    homeassistant_discovery: bool = True
    client_id: str = "water-meter-digitizer"
    last_published_topics: list[str] = Field(default_factory=list)
    last_published_readout: str | None = None


class ConfigBackupInfo(BaseModel, DictAccessMixin):
    name: str
    created_at: str = ""
    formatted_time: str = ""
    size_bytes: int = 0
    tag: str = ""
    is_auto: bool = True


class TimelineFrame(BaseModel, DictAccessMixin):
    id: int | None = None
    timestamp: str = ""
    meters: dict[str, Any] = Field(default_factory=dict)
    digital_results: dict[str, Any] = Field(default_factory=dict)
    analog_results: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    frame_type: str | None = None
    has_frame: bool = False
    flow_detected: bool = False
    confidence_scores: dict[str, float] = Field(default_factory=dict)


class VisualDiffMetrics(BaseModel, DictAccessMixin):
    reading_id: int = 0
    compare_id: int | None = None
    ssim_similarity: float = 1.0
    is_anomaly: bool = False
    diff_image_url: str = ""
    error: str = ""
