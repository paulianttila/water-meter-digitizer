"""Application context container providing structured dependency injection for FastAPI routes and backend services."""

from dataclasses import dataclass
from typing import Any

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

    @classmethod
    def from_app_state(
        cls,
        state: Any,
        default_config: Config | None = None,
        default_config_file: str = "",
        default_version: str = "",
    ) -> "AppContext":
        """Construct AppContext from an application state object."""
        return cls(
            config=getattr(state, "config", default_config),
            config_file=getattr(state, "config_file", default_config_file),
            config_version=getattr(state, "config_version", 1),
            storage=getattr(state, "storage", None),
            cache=getattr(state, "image_cache", None),
            zero_flow_tracker=getattr(state, "zero_flow_tracker", None),
            mqtt_service=getattr(state, "mqtt_service", None),
            poller=getattr(state, "poller", None),
            version=getattr(state, "version", default_version),
            start_time=getattr(state, "start_time", 0.0),
            started_at=getattr(state, "started_at", ""),
        )


def get_app_context(request: Request) -> AppContext:
    """FastAPI dependency provider returning the active AppContext instance."""
    return AppContext.from_app_state(request.app.state)
