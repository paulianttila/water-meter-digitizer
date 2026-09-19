"""Service status and control endpoints (poller, MQTT, zero-flow leak monitor)."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from context import AppContext, get_app_context
from decorators.decorators import log_execution_time

router = APIRouter(tags=["services"])


@router.get("/leak/status")
@log_execution_time
def get_leak_status(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> Response:
    tracker = ctx.zero_flow_tracker
    status = (
        tracker.get_status().to_dict() if tracker else {"enabled": False, "state": "OK"}
    )
    return Response(json.dumps(status), media_type="application/json")


@router.post("/leak/reset")
@log_execution_time
def reset_leak_status(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> Response:
    tracker = ctx.zero_flow_tracker
    if tracker is None:
        raise HTTPException(status_code=400, detail="Leak tracker not initialized")
    status = tracker.reset().to_dict()
    return Response(json.dumps(status), media_type="application/json")


@router.get("/poller/status")
@log_execution_time
def get_poller_status(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> Response:
    poller = ctx.poller
    status = poller.get_status() if poller else {"enabled": False, "running": False}
    return Response(json.dumps(status), media_type="application/json")


@router.post("/poller/trigger")
@log_execution_time
def trigger_poller(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> Response:
    poller = ctx.poller
    if poller is None:
        raise HTTPException(status_code=400, detail="Poller service not initialized")
    poller.trigger_now()
    return Response(
        json.dumps({"message": "Poller triggered successfully"}),
        media_type="application/json",
    )


@router.get("/mqtt/status")
@log_execution_time
def get_mqtt_status(
    ctx: Annotated[AppContext, Depends(get_app_context)],
) -> Response:
    mqtt_svc = ctx.mqtt_service
    status = (
        mqtt_svc.get_status() if mqtt_svc else {"enabled": False, "connected": False}
    )
    return Response(json.dumps(status), media_type="application/json")
