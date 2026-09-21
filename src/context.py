"""Application context container providing structured dependency injection for FastAPI routes and backend services."""

from dataclasses import dataclass

from fastapi import Request

from configuration import Config
from services.leak.tracker import ZeroFlowTracker
from services.mqtt.client import MQTTService
from services.poller.scheduler import BackgroundPoller
from storage.base import StorageBackend
from utils.cache import ImageCache


@dataclass
class AppContext:
    """Strongly-typed application context container holding singleton service instances."""

    config: Config
    config_file: str
    config_version: int
    storage: StorageBackend | None
    cache: ImageCache
    zero_flow_tracker: ZeroFlowTracker | None
    mqtt_service: MQTTService | None
    poller: BackgroundPoller | None
    version: str
    start_time: float
    started_at: str

    @property
    def image_cache(self) -> ImageCache:
        return self.cache


def get_app_context(request: Request) -> AppContext:
    """FastAPI dependency provider returning the active AppContext instance."""
    return AppContext(
        config=getattr(request.app.state, "config", None),
        config_file=getattr(request.app.state, "config_file", ""),
        config_version=getattr(request.app.state, "config_version", 1),
        storage=getattr(request.app.state, "storage", None),
        cache=getattr(request.app.state, "image_cache", None),
        zero_flow_tracker=getattr(request.app.state, "zero_flow_tracker", None),
        mqtt_service=getattr(request.app.state, "mqtt_service", None),
        poller=getattr(request.app.state, "poller", None),
        version=getattr(request.app.state, "version", ""),
        start_time=getattr(request.app.state, "start_time", 0.0),
        started_at=getattr(request.app.state, "started_at", ""),
    )
