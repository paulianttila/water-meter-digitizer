"""Service accessor bridging FastAPI application state to GUI callbacks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from api.routes_meter import get_meter_data
from processor.digitizer import MeterResult
from storage.base import StorageBackend
from utils.image_service import get_cached_image_base64
from version import __version__ as VERSION

if TYPE_CHECKING:
    from fastapi import FastAPI

    from configuration import Config
    from services.config_file_service import ConfigFileService

logger = logging.getLogger(__name__)


class ServiceAccessor:
    """Adapts FastAPI application state and services into clean accessor methods."""

    def __init__(
        self,
        app_instance: FastAPI,
        config_file_service: ConfigFileService | None = None,
        default_config: Config | None = None,
    ) -> None:
        self._app = app_instance
        self._config_file_service = config_file_service
        self._default_config = default_config

    @property
    def app(self) -> FastAPI:
        return self._app

    @property
    def config_file_service(self) -> ConfigFileService | None:
        return self._config_file_service

    def get_config(self) -> Config:
        cfg = getattr(self._app.state, "config", None)
        if cfg is not None:
            return cfg
        if self._default_config is not None:
            return self._default_config
        from configuration import Config

        return Config()

    def get_config_version(self) -> int:
        return getattr(self._app.state, "config_version", 1)

    def get_storage(self) -> StorageBackend | None:
        return getattr(self._app.state, "storage", None)

    def get_meter_data(
        self,
        url: str = "",
        saveimages: bool = False,
        config: Config | None = None,
    ) -> MeterResult:
        return get_meter_data(
            url=url,
            saveimages=saveimages,
            app_instance=self._app,
            config=config,
        )

    def get_image_as_base64_str(self, image_name: str) -> str:
        cache = getattr(self._app.state, "image_cache", None)
        cfg = self.get_config()
        b64 = get_cached_image_base64(cache, image_name, cfg)
        if b64 is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        return b64

    def get_health_data(self) -> dict[str, Any]:
        from utils.diagnostics import collect_health_status

        cfg = self.get_config()
        ver = getattr(self._app.state, "version", VERSION)
        return collect_health_status(self._app.state, cfg, ver)

    def get_leak_status(self) -> dict[str, Any]:
        tracker = getattr(self._app.state, "zero_flow_tracker", None)
        return (
            tracker.get_status().to_dict()
            if tracker
            else {"enabled": False, "state": "OK"}
        )

    def reset_leak_status(self) -> dict[str, Any]:
        tracker = getattr(self._app.state, "zero_flow_tracker", None)
        if tracker:
            return tracker.reset().to_dict()
        return {"enabled": False, "state": "OK"}

    def get_poller_status(self) -> dict[str, Any]:
        poller = getattr(self._app.state, "poller", None)
        return poller.get_status() if poller else {"enabled": False, "running": False}

    def trigger_poller(self) -> dict[str, Any]:
        poller = getattr(self._app.state, "poller", None)
        if poller:
            poller.trigger_now()
            return {"status": "success", "message": "Poller triggered successfully"}
        return {"status": "error", "message": "Poller service not initialized"}

    def get_mqtt_status(self) -> dict[str, Any]:
        mqtt_svc = getattr(self._app.state, "mqtt_service", None)
        return (
            mqtt_svc.get_status()
            if mqtt_svc
            else {"enabled": False, "connected": False}
        )

    def get_previous_values(self) -> dict[str, dict[str, str]]:
        import previous_value

        cfg = self.get_config()
        pv_file = getattr(cfg, "previous_value_file", "/config/prevalue.ini")
        return previous_value.get_all_previous_values(pv_file)

    def set_previous_value(self, name: str, value: str) -> dict[str, Any]:
        import previous_value

        cfg = self.get_config()
        pv_file = getattr(cfg, "previous_value_file", "/config/prevalue.ini")
        if not value or not isinstance(value, str):
            raise ValueError("Value cannot be empty")
        cleaned_value = value.strip()
        val_float = float(cleaned_value)
        if val_float < 0:
            raise ValueError("Value cannot be negative")
        if not name or not name.strip():
            raise ValueError("Meter name cannot be empty")
        cleaned_name = name.strip()
        previous_value.save_previous_value_to_file(pv_file, cleaned_name, cleaned_value)
        return {
            "status": "success",
            "message": (
                f"Successfully updated baseline for '{cleaned_name}' to "
                f"{cleaned_value}"
            ),
            "meter": cleaned_name,
            "value": cleaned_value,
            "error": "",
        }
