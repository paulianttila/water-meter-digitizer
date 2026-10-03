"""Service accessor bridging FastAPI application state to GUI callbacks."""

from __future__ import annotations

import logging
import math
import os
import time
from collections.abc import Callable
from pathlib import Path
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

    def is_config_missing(self) -> bool:
        return bool(getattr(self._app.state, "config_missing", False))

    def get_target_config_file(self) -> str:
        return str(getattr(self._app.state, "target_config_file", ""))

    def copy_default_config(self) -> bool:
        from config.seed import copy_default_config

        target = self.get_target_config_file()
        if not target:
            return False
        success = copy_default_config(target)
        if success:
            self._app.state.config_missing = False
        return success

    def init_profile_for_wizard(self) -> bool:
        from config.seed import init_profile_for_wizard

        target = self.get_target_config_file()
        if not target:
            return False
        success = init_profile_for_wizard(target)
        if success:
            self._app.state.config_missing = False
        return success

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

    def _resolve_models_dir(self, model_type: str) -> Path | None:
        cfg = self.get_config()
        configured_dir = (
            cfg.digital_models_dir if model_type == "digital" else cfg.analog_models_dir
        )
        if configured_dir:
            p = Path(configured_dir)
            if p.is_dir():
                return p.resolve()
            p_strip = Path(configured_dir.lstrip("/"))
            if p_strip.is_dir():
                return p_strip.resolve()

        # Only check project fallback paths if configured_dir was default /config or empty
        if not configured_dir or configured_dir.startswith("/config"):
            candidates = [
                Path(__file__).resolve().parents[2]
                / "config"
                / "neuralnets"
                / model_type,
                Path("config") / "neuralnets" / model_type,
                Path("/config") / "neuralnets" / model_type,
            ]
            cfg_env = os.environ.get("CONFIG_FILE")
            if cfg_env:
                cfg_parent = Path(cfg_env).resolve().parent
                candidates.insert(0, cfg_parent / "neuralnets" / model_type)

            for cand in candidates:
                if cand.is_dir():
                    return cand.resolve()
        return None

    def list_cnn_models(self, model_type: str) -> list[dict[str, Any]]:
        models_dir = self._resolve_models_dir(model_type)
        if not models_dir or not models_dir.is_dir():
            logger.warning("Models directory not found for %s", model_type)
            return []

        models: list[dict[str, Any]] = []
        for path in sorted(models_dir.rglob("*.tflite")):
            try:
                rel = path.relative_to(models_dir)
                if len(rel.parts) > 1:
                    display_name = f"{rel.parent} / {path.name}"
                    category = str(rel.parts[0])
                else:
                    display_name = path.name
                    category = "general"
            except Exception:
                display_name = path.name
                category = "general"

            name_lower = path.name.lower()
            quantized = (
                "_q." in name_lower
                or "-q." in name_lower
                or "_q_" in name_lower
                or "-q_" in name_lower
            )

            try:
                size_kb = round(path.stat().st_size / 1024, 1)
            except Exception:
                size_kb = 0.0

            models.append(
                {
                    "file": str(path.resolve()),
                    "name": display_name,
                    "filename": path.name,
                    "category": category,
                    "quantized": quantized,
                    "size_kb": size_kb,
                }
            )

        models.sort(key=lambda m: (m["category"], m["quantized"], m["name"]))
        return models

    def evaluate_crop_model(
        self, image_base64: str, model_file: str, is_digital: bool
    ) -> dict[str, Any]:
        from utils.image import convert_base64_str_to_image

        start = time.perf_counter()
        if not image_base64:
            return {
                "value": None,
                "confidence": 0.0,
                "latency_ms": 0.0,
                "model_file": model_file,
                "error": "No image data provided",
            }

        try:
            pil_img = convert_base64_str_to_image(image_base64)
            if is_digital:
                from cnn.digital_counter_cnn import DigitalCounterCNN

                cnn = DigitalCounterCNN(modelfile=model_file, dx=20, dy=32)
            else:
                from cnn.analog_needle_cnn import AnalogNeedleCNN

                cnn = AnalogNeedleCNN(modelfile=model_file, dx=32, dy=32)

            raw_val, conf = cnn.readout_with_confidence(pil_img)
            latency_ms = round((time.perf_counter() - start) * 1000, 1)

            val: float | int | str
            if isinstance(raw_val, float):
                val = "N" if math.isnan(raw_val) else round(raw_val, 2)
            else:
                val = raw_val

            return {
                "value": val,
                "confidence": round(float(conf), 1),
                "latency_ms": latency_ms,
                "model_file": model_file,
                "error": None,
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.warning(
                "Error evaluating crop with model %s: %s",
                model_file,
                e,
                exc_info=True,
            )
            return {
                "value": None,
                "confidence": 0.0,
                "latency_ms": latency_ms,
                "model_file": model_file,
                "error": str(e),
            }

    def benchmark_crop_models(
        self, image_base64: str, is_digital: bool
    ) -> list[dict[str, Any]]:
        model_type = "digital" if is_digital else "analog"
        candidate_models = self.list_cnn_models(model_type)
        results: list[dict[str, Any]] = []

        for cand in candidate_models:
            res = self.evaluate_crop_model(image_base64, cand["file"], is_digital)
            item = {
                **cand,
                "value": res["value"],
                "confidence": res["confidence"],
                "latency_ms": res["latency_ms"],
                "error": res["error"],
            }
            results.append(item)

        results.sort(
            key=lambda x: (
                x["error"] is None and x["value"] is not None and x["value"] != "N",
                x["confidence"],
                -x["latency_ms"],
            ),
            reverse=True,
        )
        return results

    def apply_model_to_config(
        self,
        model_file: str,
        is_digital: bool,
        use_config_fn: Callable[[], None] | None = None,
    ) -> bool:
        cfg = self.get_config()
        if is_digital:
            cfg.digital_readout.model_file = model_file
            cfg.digital_readout.model = "auto"
        else:
            cfg.analog_readout.model_file = model_file
            cfg.analog_readout.model = "auto"

        saved_str = cfg.save_to_string()
        if self._config_file_service:
            self._config_file_service.save(saved_str)

        if hasattr(self._app, "state"):
            self._app.state.config = cfg

        if use_config_fn:
            use_config_fn()
        return True
