"""Main application entry point and service orchestrator for water-meter-digitizer."""

import argparse
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
from services.config_file_service import ConfigFileService
from services.leak.tracker import ZeroFlowTracker
from services.mqtt.client import MQTTService
from services.poller.scheduler import BackgroundPoller
from storage import get_storage_backend
from utils.cache import ImageCache
from utils.decorators import log_execution_time
from utils.image_service import get_cached_image_base64
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
config_file_service = ConfigFileService(lambda: config_file, _config_lock)


def _configure_third_party_loggers() -> None:
    """Suppress verbose logs from third-party libraries."""
    for name in ("urllib3", "asyncio", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)


init_log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(
    stream=sys.stdout,
    level=init_log_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
_configure_third_party_loggers()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def _sync_app_context(target_app: FastAPI | None = None) -> None:
    """Synchronize app.state.context with active application state."""
    app_inst = target_app or app
    app_inst.state.context = AppContext.from_app_state(
        app_inst.state,
        default_config=getattr(app_inst.state, "config", None) or config,
        default_config_file=getattr(app_inst.state, "config_file", None) or config_file,
        default_version=getattr(app_inst.state, "version", None) or VERSION,
    )


def start_services(
    previous_config: Config | None = None,
    target_app: FastAPI | None = None,
) -> None:
    """Stop existing services and restart active services based on current configuration."""
    app_inst = target_app or app
    cfg = getattr(app_inst.state, "config", config)

    stop_services(target_app=app_inst)
    app_inst.state.zero_flow_tracker = ZeroFlowTracker(cfg.zero_flow_monitor)

    mqtt_svc = MQTTService(
        config=cfg.mqtt,
        meter_configs=cfg.meter_configs,
        version=VERSION,
    )
    if cfg.mqtt.enabled:
        mqtt_svc.start()
    app_inst.state.mqtt_service = mqtt_svc

    poller = BackgroundPoller(
        config=cfg.poller,
        readout_func=get_meter_data,
        mqtt_service=mqtt_svc if cfg.mqtt.enabled else None,
    )
    if cfg.poller.enabled:
        poller.start()
    app_inst.state.poller = poller

    _sync_app_context(app_inst)


def stop_services(target_app: FastAPI | None = None) -> None:
    """Stop background poller and MQTT client services."""
    app_inst = target_app or app
    poller = getattr(app_inst.state, "poller", None)
    if poller is not None:
        poller.stop()

    mqtt_svc = getattr(app_inst.state, "mqtt_service", None)
    if mqtt_svc is not None:
        mqtt_svc.stop()
    _sync_app_context(app_inst)


@asynccontextmanager
async def lifespan(app_inst: FastAPI):
    init_config(target_app=app_inst)
    yield
    stop_services(target_app=app_inst)


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


def create_app(custom_config_file: str | None = None) -> FastAPI:
    """Application factory creating a configured FastAPI app instance."""
    cfg_path = custom_config_file or config_file
    ensure_config_initialized(cfg_path)

    app_instance = FastAPI(
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
    set_app_ref(app_instance)

    app_config = (
        Config().load_from_file(ini_file=cfg_path) if custom_config_file else config
    )

    app_instance.state.version = VERSION
    app_instance.state.config_file = cfg_path
    app_instance.state.config = app_config
    app_instance.state.config_version = 1
    app_instance.state.image_cache = ImageCache(max_size=50, ttl_seconds=300.0)
    app_instance.state.storage = get_storage_backend(app_config)
    app_instance.state.zero_flow_tracker = None
    app_instance.state.start_time = time.time()
    app_instance.state.started_at = datetime.now().astimezone().isoformat()
    app_instance.state.mqtt_service = None
    app_instance.state.poller = None
    app_instance.state.init_config_fn = lambda: init_config(app_instance)

    # Mount static files
    app_instance.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "web" / "static")),
        name="static",
    )

    # Register REST Routers
    app_instance.include_router(system_router)
    app_instance.include_router(health_router)
    app_instance.include_router(meter_router)
    app_instance.include_router(history_router)
    app_instance.include_router(services_router)
    app_instance.include_router(mock_camera_router)

    # Register RFC 7807 Domain Exception Handlers
    register_exception_handlers(app_instance)

    _sync_app_context(app_instance)
    return app_instance


app = create_app()


# --- Helper Functions for NiceGUI Bridge ---
def get_image_as_base64_str(image_name: str) -> str:
    cache = getattr(app.state, "image_cache", None)
    cfg = getattr(app.state, "config", None) or config
    b64 = get_cached_image_base64(cache, image_name, cfg)
    if b64 is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return b64


def load_config_file() -> str:
    return config_file_service.load()


def save_config_file(data: str) -> None:
    config_file_service.save(data)


def list_config_backups() -> list[dict[str, Any]]:
    return config_file_service.list_backups()


def restore_config_backup(backup_name: str) -> None:
    config_file_service.restore_backup(backup_name)


def undo_last_config() -> str | None:
    return config_file_service.undo_last()


def create_config_snapshot(tag: str = "") -> str | None:
    return config_file_service.create_snapshot(tag=tag)


def delete_config_backup(backup_name: str) -> bool:
    return config_file_service.delete_backup(backup_name)


def diff_config_backup(backup_name: str) -> list[str]:
    return config_file_service.diff_backup(backup_name)


def load_config_backup(backup_name: str) -> str:
    return config_file_service.load_backup(backup_name)


def init_gui(app_instance: FastAPI) -> None:
    """Initialize NiceGUI interface with delegated backend callbacks."""
    import gui.frontend as frontend
    from gui.callbacks_impl import CallbacksImpl
    from gui.service_accessor import ServiceAccessor

    accessor = ServiceAccessor(
        app_instance,
        config_file_service=config_file_service,
        default_config=getattr(app_instance.state, "config", None) or config,
    )
    callbacks = CallbacksImpl.from_service_accessor(
        accessor,
        use_config_fn=lambda: init_config(app_instance),
    )
    frontend.init(app_instance, callbacks)


@log_execution_time
def init_config(target_app: FastAPI | None = None) -> None:
    """Load configuration file and reconfigure services and logging levels."""
    from cnn.pool import clear_interpreter_pools

    app_inst = target_app or app
    with _config_lock:
        clear_interpreter_pools()
        global config
        old_config = getattr(app_inst.state, "config", None)
        target_cfg_file = (
            config_file
            if target_app is None
            else getattr(app_inst.state, "config_file", config_file)
        )
        new_config = Config().load_from_file(ini_file=target_cfg_file)
        config = new_config
        app_inst.state.config = new_config
        app_inst.state.config_file = target_cfg_file
        app_inst.state.config_version = getattr(app_inst.state, "config_version", 0) + 1
        target_log_level = getattr(logging, str(config.log_level).upper(), logging.INFO)
        logging.getLogger().setLevel(target_log_level)
        logger.setLevel(target_log_level)
        app_inst.state.storage = get_storage_backend(config)
        start_services(previous_config=old_config, target_app=app_inst)

        _configure_third_party_loggers()


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
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        help="Server port",
        default=int(os.environ.get("SERVER_PORT", "3000")),
    )

    args = parser.parse_args()
    config_file = args.config_file
    init_config()
    init_gui(app)

    port = args.port
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104
        port=port,
        log_level="info" if logger.level == logging.DEBUG else "warning",
    )
