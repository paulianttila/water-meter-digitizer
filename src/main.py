"""Main application entry point and service orchestrator for water-meter-digitizer."""

import argparse
import contextlib
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import utils.image
from api.error_handlers import register_exception_handlers
from api.routes_health import router as health_router
from api.routes_history import router as history_router
from api.routes_meter import get_meter_data, set_app_ref
from api.routes_meter import router as meter_router
from api.routes_mock_camera import router as mock_camera_router
from api.routes_services import router as services_router
from api.routes_system import router as system_router
from configuration import Config, ensure_config_initialized
from context import AppContext
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

init_log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(
    stream=sys.stdout,
    level=init_log_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def _sync_app_context() -> None:
    """Synchronize app.state.context with active application state."""
    app.state.context = AppContext(
        config=getattr(app.state, "config", config),
        config_file=getattr(app.state, "config_file", config_file),
        config_version=getattr(app.state, "config_version", 1),
        storage=getattr(app.state, "storage", None),
        cache=getattr(app.state, "image_cache", None),
        zero_flow_tracker=getattr(app.state, "zero_flow_tracker", None),
        mqtt_service=getattr(app.state, "mqtt_service", None),
        poller=getattr(app.state, "poller", None),
        version=getattr(app.state, "version", VERSION),
        start_time=getattr(app.state, "start_time", 0.0),
        started_at=getattr(app.state, "started_at", ""),
    )


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
    _sync_app_context()


def stop_services() -> None:
    """Stop background poller and MQTT client services."""
    poller = getattr(app.state, "poller", None)
    if poller is not None:
        poller.stop()

    mqtt_svc = getattr(app.state, "mqtt_service", None)
    if mqtt_svc is not None:
        mqtt_svc.stop()
    _sync_app_context()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_config()
    yield
    stop_services()


# --- Application Bootstrap ---
OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Core system endpoints: version, GUI redirect, and dynamic configuration reload.",
    },
    {
        "name": "health",
        "description": "Liveness and diagnostic health status reporting system diagnostics, memory, and camera reachability.",
    },
    {
        "name": "meter",
        "description": "Real-time water meter digitizer readout, ROI visualization, intermediate processing crops, and baseline management.",
    },
    {
        "name": "history",
        "description": "Historical meter reading queries, consumption aggregations, and snapshot Time Machine comparison metrics.",
    },
    {
        "name": "services",
        "description": "Telemetry and control for background poller, MQTT publisher, and zero-flow leak detector.",
    },
    {
        "name": "simulation",
        "description": "Procedural mock water meter image generation and automated test feeds.",
    },
]

app = FastAPI(
    title="Water Meter Digitizer API",
    description=(
        "High-performance edge AI digitizer for analog & digital water meters with "
        "real-time neural network inference, MQTT publishing, background polling, "
        "historical consumption analytics, and procedural mock camera simulation."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "syntaxHighlight.theme": "monokai",
    },
    lifespan=lifespan,
)
set_app_ref(app)

app.state.version = VERSION
app.state.config_file = config_file
app.state.config = config
app.state.config_version = 1
app.state.image_cache = ImageCache(max_size=50, ttl_seconds=300.0)
app.state.storage = get_storage_backend(config)
app.state.zero_flow_tracker = ZeroFlowTracker(config.zero_flow_monitor)
app.state.start_time = time.time()
app.state.started_at = datetime.now().astimezone().isoformat()
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
_sync_app_context()


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
app.include_router(mock_camera_router)

# Register RFC 7807 Domain Exception Handlers
register_exception_handlers(app)


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
                    proc = (
                        ImageProcessor()
                        .set_image(source_img.copy())
                        .draw_meter_rois(cfg)
                    )
                    return proc.get_image_as_base64_str()
        raise HTTPException(status_code=404, detail="Image not found")
    return utils.image.convert_image_base64str(img)


def load_config_file() -> str:
    with _config_lock, open(config_file) as f:
        return f.read()


def save_config_file(data: str) -> None:
    from config_history import ConfigHistoryManager

    with _config_lock:
        # Validate syntax before writing
        Config().load_from_string(data)
        if os.path.exists(config_file):
            ConfigHistoryManager.create_backup(config_file)
        with open(config_file, "w") as f:
            f.write(data)


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


def load_config_backup(backup_name: str) -> str:
    from config_history import ConfigHistoryManager

    with _config_lock:
        return ConfigHistoryManager.get_backup_content(
            backup_name, config_file=config_file
        )


def init_gui(app_instance: FastAPI) -> None:
    """Initialize NiceGUI interface with delegated backend callbacks."""
    from gui.callbacks_impl import CallbacksImpl
    from storage.frame_service import FrameService

    def _get_health_data() -> dict[str, Any]:
        from utils.diagnostics import collect_health_status

        cfg = getattr(app_instance.state, "config", config)
        ver = getattr(app_instance.state, "version", VERSION)
        return collect_health_status(app_instance.state, cfg, ver)

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

    frame_service = FrameService(
        storage=lambda: getattr(app_instance.state, "storage", None)
    )

    callbacks = CallbacksImpl(
        get_meter_data_fn=lambda url="", saveimages=False, config=None: get_meter_data(
            url=url,
            saveimages=saveimages,
            app_instance=app_instance,
            config=config,
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
        load_backup_fn=load_config_backup,
        get_health_data_fn=_get_health_data,
        get_leak_status_fn=_get_leak_status,
        reset_leak_status_fn=_reset_leak_status,
        get_poller_status_fn=_get_poller_status,
        trigger_poller_fn=_trigger_poller,
        get_mqtt_status_fn=_get_mqtt_status,
        get_previous_values_fn=_get_previous_values,
        set_previous_value_fn=_set_previous_value,
        get_config_version_fn=lambda: getattr(app_instance.state, "config_version", 1),
        frame_service=frame_service,
    )
    import gui.frontend as frontend

    frontend.init(app_instance, callbacks)


@log_execution_time
def init_config() -> None:
    """Load configuration file and reconfigure services and logging levels."""
    from cnn.pool import clear_interpreter_pools

    with _config_lock:
        clear_interpreter_pools()
        global config
        new_config = Config().load_from_file(ini_file=config_file)
        config = new_config
        app.state.config = new_config
        app.state.config_file = config_file
        app.state.config_version = getattr(app.state, "config_version", 0) + 1
        target_log_level = getattr(logging, str(config.log_level).upper(), logging.INFO)
        logging.getLogger().setLevel(target_log_level)
        logger.setLevel(target_log_level)
        app.state.storage = get_storage_backend(config)
        start_services()

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
