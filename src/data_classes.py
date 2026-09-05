import re
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict


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
    use_previous_value: bool = False
    pre_value_from_file_max_age: int = 0
    use_extended_resolution: bool = False
    unit: str = ""

    @property
    def value_names(self) -> list[str]:
        return re.findall(r"\{(.*?)\}", self.format)


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


class ModelHealth(BaseModel):
    enabled: bool = False
    path: str = ""
    exists: bool = False
    size_bytes: int | None = None


class ModelsHealth(BaseModel):
    digital: ModelHealth
    analog: ModelHealth


class UptimeHealth(BaseModel):
    uptime_seconds: float = 0.0
    uptime_human: str = "0s"
    started_at: str = ""


class SystemHealth(BaseModel):
    version: str = ""
    python_version: str = ""
    platform: str = ""


class HealthResponse(BaseModel):
    status: str = "healthy"  # "healthy", "degraded", or "unhealthy"
    uptime: UptimeHealth
    camera: CameraHealth
    memory: MemoryHealth
    cache: CacheHealth
    models: ModelsHealth
    system: SystemHealth
