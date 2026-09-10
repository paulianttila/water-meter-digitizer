"""Main application entry point and service orchestrator for water-meter-digitizer."""

import argparse
import contextlib
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import utils.image
from api.routes_health import router as health_router
from api.routes_history import router as history_router
from api.routes_meter import get_meter_data, set_app_ref
from api.routes_meter import router as meter_router
from api.routes_services import router as services_router
from api.routes_system import router as system_router
from configuration import Config, ensure_config_initialized
from decorators.decorators import log_execution_time
from leak.tracker import ZeroFlowTracker
from mqtt.client import MQTTService
from poller.scheduler import BackgroundPoller
from processor.image import ImageProcessor
from storage import get_storage_backend
from utils.cache import ImageCache
from version import __version__ as VERSION

config_file = os.environ.get("CONFIG_FILE", "/config/config.ini")
ensure_config_initialized(config_file)

if not os.path.exists(config_file) and os.path.exists("config/config.ini"):
    config_file = "config/config.ini"

config = Config()
if os.path.exists(config_file):
    try:
        config.load_from_file(ini_file=config_file)
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to load config from {config_file}: {e}"
        )

_config_lock = threading.RLock()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent


def start_services() -> None:
    """Start MQTT service and background poller based on active config."""
    stop_services()

    app.state.zero_flow_tracker = ZeroFlowTracker(config.zero_flow_monitor)

    mqtt_svc = MQTTService(
        config=config.mqtt,
        meter_configs=config.meter_configs,
        version=VERSION,
    )
    if config.mqtt.enabled:
        mqtt_svc.start()
    app.state.mqtt_service = mqtt_svc

    poller = BackgroundPoller(
        config=config.poller,
        readout_func=get_meter_data,
        mqtt_service=mqtt_svc if config.mqtt.enabled else None,
    )
    if config.poller.enabled:
        poller.start()
    app.state.poller = poller


def stop_services() -> None:
    """Stop background poller and MQTT client services."""
    poller = getattr(app.state, "poller", None)
    if poller is not None:
        poller.stop()

    mqtt_svc = getattr(app.state, "mqtt_service", None)
    if mqtt_svc is not None:
        mqtt_svc.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_config()
    yield
    stop_services()


# --- Application Bootstrap ---
app = FastAPI(title="meter", lifespan=lifespan)
set_app_ref(app)

app.state.version = VERSION
app.state.config_file = config_file
app.state.config = config
app.state.image_cache = ImageCache(max_size=50, ttl_seconds=300.0)
app.state.storage = get_storage_backend(config)
app.state.zero_flow_tracker = ZeroFlowTracker(config.zero_flow_monitor)
app.state.start_time = time.time()
app.state.started_at = datetime.now(UTC).isoformat()
app.state.mqtt_service = MQTTService(
    config=config.mqtt,
    meter_configs=config.meter_configs,
    version=VERSION,
)
app.state.poller = BackgroundPoller(
    config=config.poller,
    readout_func=lambda *args, **kwargs: None,  # type: ignore
    mqtt_service=app.state.mqtt_service,
)
app.state.init_config_fn = lambda: init_config()

# Mount static files
app.mount(
    "/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static"
)

# Register REST Routers
app.include_router(system_router)
app.include_router(health_router)
app.include_router(meter_router)
app.include_router(history_router)
app.include_router(services_router)


# --- Helper Functions for NiceGUI Bridge ---
def get_image_as_base64_str(image_name: str) -> str:
    img = app.state.image_cache.get(image_name)
    if img is None:
        if image_name == "roi":
            with contextlib.suppress(Exception):
                cfg = getattr(app.state, "config", config)
                source_img = app.state.image_cache.get(
                    "final"
                ) or app.state.image_cache.get("aligned")
                if source_img is not None and cfg is not None:
                    from gui.theme import (
                        COLOR_ROI_ANALOG,
                        COLOR_ROI_DIGITAL,
                        COLOR_ROI_REFS,
                    )

                    proc = ImageProcessor().set_image(source_img.copy())
                    if cfg.alignment and cfg.alignment.ref_images:
                        proc.draw_roi(cfg.alignment.ref_images, COLOR_ROI_REFS)
                    if cfg.digital_readout and cfg.digital_readout.cut_images:
                        proc.draw_roi(cfg.digital_readout.cut_images, COLOR_ROI_DIGITAL)
                    if cfg.analog_readout and cfg.analog_readout.cut_images:
                        proc.draw_roi(cfg.analog_readout.cut_images, COLOR_ROI_ANALOG)
                    return proc.get_image_as_base64_str()
        raise HTTPException(status_code=404, detail="Image not found")
    return utils.image.convert_image_base64str(img)


def load_config_file() -> str:
    with _config_lock, open(config_file) as f:
        return f.read()


def save_config_file(data: str) -> None:
    with _config_lock:
        new_config = Config().load_from_string(data)
        new_config.save_to_file(config_file, make_backup=True)


def list_config_backups() -> list[dict[str, Any]]:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return [b.model_dump() for b in ConfigHistoryManager.list_backups(config_file)]


def restore_config_backup(backup_name: str) -> None:
    from config_history import ConfigHistoryManager

    with _config_lock:
        ConfigHistoryManager.restore_backup(config_file, backup_name)


def undo_last_config() -> str | None:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return ConfigHistoryManager.undo_last(config_file)


def create_config_snapshot(tag: str = "") -> str | None:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return ConfigHistoryManager.create_backup(config_file, tag=tag)


def delete_config_backup(backup_name: str) -> bool:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return ConfigHistoryManager.delete_backup(config_file, backup_name)


def diff_config_backup(backup_name: str) -> list[str]:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return ConfigHistoryManager.get_diff(
            load_config_file(), backup_name, config_file=config_file
        )


def init_gui(app_instance: FastAPI) -> None:
    """Initialize NiceGUI interface with delegated backend callbacks."""
    import gui.frontend as frontend
    from gui.callbacks_impl import CallbacksImpl

    def _get_health_data() -> dict[str, Any]:
        import time
        from datetime import UTC, datetime

        from api.routes_health import get_allowed_asset_directories
        from utils.diagnostics import (
            check_camera_reachability,
            format_uptime,
            get_models_info,
            get_process_memory_info,
            get_system_info,
        )

        now = time.time()
        start_time = getattr(app_instance.state, "start_time", now)
        started_at = getattr(
            app_instance.state, "started_at", datetime.now(UTC).isoformat()
        )
        uptime_seconds = round(now - start_time, 2)
        uptime_human = format_uptime(uptime_seconds)
        cfg = getattr(app_instance.state, "config", config)
        ver = getattr(app_instance.state, "version", VERSION)

        image_source_url = cfg.image_source.url if cfg else ""
        camera_diag = check_camera_reachability(
            image_source_url,
            timeout=2.0,
            allowed_directories=get_allowed_asset_directories(cfg),
        )
        mem_diag = get_process_memory_info()
        image_cache = getattr(app_instance.state, "image_cache", None)
        cache_diag = (
            image_cache.get_stats()
            if image_cache
            else {
                "hits": 0,
                "misses": 0,
                "hit_ratio_percent": 0.0,
                "current_size": 0,
                "max_size": 0,
                "total_evictions": 0,
                "ttl_seconds": 0.0,
            }
        )
        digital_enabled = cfg.digital_readout.enabled if cfg else False
        digital_modelfile = cfg.digital_readout.model_file if cfg else ""
        analog_enabled = cfg.analog_readout.enabled if cfg else False
        analog_modelfile = cfg.analog_readout.model_file if cfg else ""

        models_diag = get_models_info(
            digital_enabled=digital_enabled,
            digital_modelfile=digital_modelfile,
            analog_enabled=analog_enabled,
            analog_modelfile=analog_modelfile,
        )
        system_diag = get_system_info(ver)

        status = "healthy"
        if not image_source_url or not camera_diag["reachable"]:
            status = "degraded"

        for model_key in ("digital", "analog"):
            m = models_diag[model_key]
            if m["enabled"] and not m["exists"]:
                status = "unhealthy"

        return {
            "status": status,
            "uptime": {
                "uptime_seconds": uptime_seconds,
                "uptime_human": uptime_human,
                "started_at": started_at,
            },
            "camera": camera_diag,
            "memory": mem_diag,
            "cache": cache_diag,
            "models": models_diag,
            "system": system_diag,
        }

    def _get_leak_status() -> dict[str, Any]:
        tracker = getattr(app_instance.state, "zero_flow_tracker", None)
        return (
            tracker.get_status().to_dict()
            if tracker
            else {"enabled": False, "state": "OK"}
        )

    def _reset_leak_status() -> dict[str, Any]:
        tracker = getattr(app_instance.state, "zero_flow_tracker", None)
        if tracker:
            return tracker.reset().to_dict()
        return {"enabled": False, "state": "OK"}

    def _get_poller_status() -> dict[str, Any]:
        poller = getattr(app_instance.state, "poller", None)
        return poller.get_status() if poller else {"enabled": False, "running": False}

    def _trigger_poller() -> dict[str, Any]:
        poller = getattr(app_instance.state, "poller", None)
        if poller:
            poller.trigger_now()
            return {"status": "success", "message": "Poller triggered successfully"}
        return {"status": "error", "message": "Poller service not initialized"}

    def _get_mqtt_status() -> dict[str, Any]:
        mqtt_svc = getattr(app_instance.state, "mqtt_service", None)
        return (
            mqtt_svc.get_status()
            if mqtt_svc
            else {"enabled": False, "connected": False}
        )

    def _get_previous_values() -> dict[str, dict[str, str]]:
        import previous_value

        cfg = getattr(app_instance.state, "config", config)
        pv_file = getattr(cfg, "previous_value_file", "/config/prevalue.ini")
        return previous_value.get_all_previous_values(pv_file)

    def _set_previous_value(name: str, value: str) -> dict[str, Any]:
        import previous_value

        cfg = getattr(app_instance.state, "config", config)
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

    callbacks = CallbacksImpl(
        get_meter_data_fn=lambda url="", saveimages=False: get_meter_data(
            url=url, saveimages=saveimages, app_instance=app_instance
        ),
        get_image_base64_fn=get_image_as_base64_str,
        get_config_fn=lambda: getattr(app_instance.state, "config", config),
        load_config_file_fn=load_config_file,
        save_config_file_fn=save_config_file,
        use_config_fn=init_config,
        get_storage_fn=lambda: getattr(app_instance.state, "storage", None),
        list_backups_fn=list_config_backups,
        restore_backup_fn=restore_config_backup,
        undo_backup_fn=undo_last_config,
        create_snapshot_fn=create_config_snapshot,
        delete_backup_fn=delete_config_backup,
        diff_backup_fn=diff_config_backup,
        get_health_data_fn=_get_health_data,
        get_leak_status_fn=_get_leak_status,
        reset_leak_status_fn=_reset_leak_status,
        get_poller_status_fn=_get_poller_status,
        trigger_poller_fn=_trigger_poller,
        get_mqtt_status_fn=_get_mqtt_status,
        get_previous_values_fn=_get_previous_values,
        set_previous_value_fn=_set_previous_value,
    )
    frontend.init(app_instance, callbacks)


@log_execution_time
def init_config() -> None:
    """Load configuration file and reconfigure services and logging levels."""
    with _config_lock:
        global config
        new_config = Config().load_from_file(ini_file=config_file)
        config = new_config
        app.state.config = new_config
        app.state.config_file = config_file
        logger.setLevel(config.log_level)
        app.state.storage = get_storage_backend(config)
        start_services()

        logging.getLogger("CNN.CNNBase").setLevel(logger.level)
    logging.getLogger("CNN.AnalogNeedleCNN").setLevel(logger.level)
    logging.getLogger("CNN.DigitalCounterCNN").setLevel(logger.level)
    logging.getLogger("Utils.DownloadUtils").setLevel(logger.level)
    logging.getLogger("Config").setLevel(logger.level)
    logging.getLogger("decorators.decorators").setLevel(logger.level)
    logging.getLogger("Processor").setLevel(logger.level)
    logging.getLogger("PreviousValueFile").setLevel(logger.level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="meter", description="Meter reading application"
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        help="Configuration file",
        default=config_file,
    )

    args = parser.parse_args()
    config_file = args.config_file
    init_config()
    init_gui(app)

    port = 3000
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104
        port=port,
        log_level="info" if logger.level == logging.DEBUG else "warning",
    )
