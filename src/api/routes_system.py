"""System routes: root redirect, version, and reload."""

import logging
import os

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from decorators.decorators import log_execution_time
from version import __version__

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


def get_version(request: Request) -> str:
    """Retrieve application version from app state."""
    return getattr(request.app.state, "version", __version__)


@router.get("/gui")
@log_execution_time
def redirect_gui() -> RedirectResponse:
    """Backward-compatible redirect from /gui to /."""
    return RedirectResponse(url="/", status_code=307)


@router.get("/version")
@log_execution_time
def get_version_endpoint(request: Request) -> dict[str, str]:
    return {"version": get_version(request)}


@router.get("/reload")
@router.post("/reload")
@log_execution_time
def reload_config(request: Request) -> Response:
    """Hot-reload configuration from disk and reinitialize services."""
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
