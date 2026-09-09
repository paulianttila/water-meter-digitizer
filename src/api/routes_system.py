"""System routes: root dashboard, version, exit, and reload."""

import logging
import os
import signal
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from decorators.decorators import log_execution_time
from version import __version__

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))


def get_version(request: Request) -> str:
    """Retrieve application version from app state."""
    return getattr(request.app.state, "version", __version__)


@router.get("/", response_class=HTMLResponse)
@log_execution_time
def get_index(request: Request) -> Response:
    version = get_version(request)
    config = getattr(request.app.state, "config", None)
    meter_configs = config.meter_configs if config else []
    meters = [m.name for m in meter_configs]
    prev_value_meters = [
        m.name for m in meter_configs if getattr(m, "use_previous_value", False)
    ]
    if not prev_value_meters and meters:
        prev_value_meters = ["total"] if "total" in meters else [meters[0]]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "version": version,
            "meters": meters,
            "prev_value_meters": prev_value_meters,
        },
    )


@router.get("/version")
@log_execution_time
def get_version_endpoint(request: Request) -> dict[str, str]:
    return {"version": get_version(request)}


@router.get("/exit", response_class=HTMLResponse)
@log_execution_time
def do_exit():
    os.kill(os.getpid(), signal.SIGTERM)
    return "App will exit immediately"


@router.get("/reload", response_class=HTMLResponse)
@log_execution_time
def reload_config(request: Request, format: str = "html") -> Response:
    error_msg = None
    version = get_version(request)
    config_file = getattr(
        request.app.state,
        "config_file",
        os.environ.get("CONFIG_FILE", "/config/config.ini"),
    )
    init_config_fn = getattr(request.app.state, "init_config_fn", None)

    try:
        if init_config_fn:
            init_config_fn()
        else:
            from configuration import Config

            new_config = Config().load_from_file(ini_file=config_file)
            request.app.state.config = new_config
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        error_msg = str(e)

    config = getattr(request.app.state, "config", None)
    meter_count = len(config.meter_configs) if config else 0

    if format == "json" or "application/json" in request.headers.get("accept", ""):
        if error_msg:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"Failed to reload configuration: {error_msg}",
                    "version": version,
                    "config_file": config_file,
                },
                status_code=500,
            )
        return JSONResponse(
            {
                "status": "success",
                "message": "Configuration reloaded successfully",
                "version": version,
                "config_file": config_file,
                "meters_count": meter_count,
            }
        )

    status_code = 500 if error_msg else 200
    return templates.TemplateResponse(
        request=request,
        name="reload.html",
        context={
            "version": version,
            "error": error_msg,
            "config_file": config_file,
            "config_file_display": (
                Path(config_file).name if len(config_file) > 40 else config_file
            ),
            "reloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "meters_count": meter_count,
            "poller_enabled": config.poller.enabled if config else False,
            "mqtt_enabled": config.mqtt.enabled if config else False,
            "history_enabled": config.history.enabled if config else False,
        },
        status_code=status_code,
    )
