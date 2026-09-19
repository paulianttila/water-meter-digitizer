from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from context import AppContext, get_app_context
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
def get_health(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> HealthResponse:
    data = collect_health_status(ctx, ctx.config, ctx.version or __version__)
    return HealthResponse(**data)
