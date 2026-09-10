from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from data_classes import HealthResponse
from decorators.decorators import log_execution_time
from utils.diagnostics import collect_health_status, get_allowed_asset_directories
from version import __version__

__all__ = ["get_allowed_asset_directories", "router"]

router = APIRouter(tags=["health"])


@router.get("/healthcheck", response_class=HTMLResponse)
@log_execution_time
def healthcheck():
    return "Health - OK"


@router.get("/health", response_model=HealthResponse)
@log_execution_time
def get_health(request: Request) -> HealthResponse:
    config = getattr(request.app.state, "config", None)
    version = getattr(request.app.state, "version", __version__)
    data = collect_health_status(request.app.state, config, version)
    return HealthResponse(**data)
