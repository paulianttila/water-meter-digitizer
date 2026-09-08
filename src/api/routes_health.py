"""Health, healthcheck, and diagnostic endpoints."""

from datetime import datetime, timezone
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from data_classes import HealthResponse
from decorators.decorators import log_execution_time
from utils.diagnostics import (
    check_camera_reachability,
    format_uptime,
    get_models_info,
    get_process_memory_info,
    get_system_info,
)

router = APIRouter(tags=["health"])


def get_allowed_asset_directories(config=None) -> list[str]:
    """Return list of allowed base directory paths for local file:// URIs."""
    allowed: list[str] = []
    if config:
        if getattr(config, "config_dir", None):
            allowed.append(config.config_dir)
        if getattr(config, "data_dir", None):
            allowed.append(config.data_dir)
        if getattr(config, "image_tmp_dir", None):
            allowed.append(config.image_tmp_dir)
    allowed.append(os.getcwd())
    return allowed


@router.get("/healthcheck", response_class=HTMLResponse)
@log_execution_time
def healthcheck():
    return "Health - OK"


@router.get("/health", response_model=HealthResponse)
@log_execution_time
def get_health(request: Request) -> HealthResponse:
    now = time.time()
    start_time = getattr(request.app.state, "start_time", now)
    started_at = getattr(
        request.app.state, "started_at", datetime.now(timezone.utc).isoformat()
    )
    uptime_seconds = round(now - start_time, 2)
    uptime_human = format_uptime(uptime_seconds)

    config = getattr(request.app.state, "config", None)
    version = getattr(request.app.state, "version", "8.0.0")

    image_source_url = config.image_source.url if config else ""

    # Check camera reachability
    camera_diag = check_camera_reachability(
        image_source_url,
        timeout=2.0,
        allowed_directories=get_allowed_asset_directories(config),
    )

    # Memory info
    mem_diag = get_process_memory_info()

    # Cache info
    image_cache = getattr(request.app.state, "image_cache", None)
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

    # Models info
    digital_enabled = config.digital_readout.enabled if config else False
    digital_modelfile = config.digital_readout.model_file if config else ""
    analog_enabled = config.analog_readout.enabled if config else False
    analog_modelfile = config.analog_readout.model_file if config else ""

    models_diag = get_models_info(
        digital_enabled=digital_enabled,
        digital_modelfile=digital_modelfile,
        analog_enabled=analog_enabled,
        analog_modelfile=analog_modelfile,
    )

    # System info
    system_diag = get_system_info(version)

    # Determine status:
    # "unhealthy" if camera configured but unreachable or enabled model missing
    # "degraded" if camera not configured
    # "healthy" otherwise
    status = "healthy"
    if not image_source_url or not camera_diag["reachable"]:
        status = "degraded"

    for model_key in ("digital", "analog"):
        m = models_diag[model_key]
        if m["enabled"] and not m["exists"]:
            status = "unhealthy"

    return HealthResponse(
        status=status,
        uptime={
            "uptime_seconds": uptime_seconds,
            "uptime_human": uptime_human,
            "started_at": started_at,
        },
        camera=camera_diag,
        memory=mem_diag,
        cache=cache_diag,
        models=models_diag,
        system=system_diag,
    )
