"""Historical meter reading and consumption endpoints."""

from datetime import datetime, timedelta, timezone
import json

from fastapi import APIRouter, Request, Response

from decorators.decorators import log_execution_time
from storage.seed import seed_demo_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/consumption")
@log_execution_time
def get_history_consumption(
    request: Request,
    meter: str = "total",
    interval: str = "daily",
    days: int = 30,
    cumulative: bool = False,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps([]), media_type="application/json")

    start = datetime.now(timezone.utc) - timedelta(days=days) if days > 0 else None
    valid_intervals = {"hourly", "daily", "weekly"}
    use_interval = interval if interval in valid_intervals else "daily"

    records = storage.get_consumption(
        meter_name=meter,
        interval=use_interval,
        start=start,
    )

    cum_total = 0.0
    data = []
    for r in records:
        cum_total += r.consumption
        data.append(
            {
                "bucket": r.bucket,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "meter_name": r.meter_name,
                "unit": r.unit,
                "consumption": (round(cum_total, 3) if cumulative else r.consumption),
                "cumulative_consumption": round(cum_total, 3),
                "start_value": r.start_value,
                "end_value": r.end_value,
                "min_value": r.min_value,
                "max_value": r.max_value,
                "reading_count": r.reading_count,
            }
        )
    return Response(json.dumps(data), media_type="application/json")


@router.get("/readings")
@log_execution_time
def get_history_readings(
    request: Request,
    meter: str | None = None,
    limit: int = 100,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps([]), media_type="application/json")

    records = storage.get_readings(meter_name=meter, limit=limit)
    data = [
        {
            "timestamp": r.timestamp.isoformat(),
            "meters": {k: v.model_dump() for k, v in r.meters.items()},
            "digital_results": r.digital_results,
            "analog_results": r.analog_results,
            "error": r.error,
        }
        for r in records
    ]
    return Response(json.dumps(data), media_type="application/json")


@router.get("/stats")
@log_execution_time
def get_history_stats(request: Request) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps({}), media_type="application/json")

    summary = storage.get_summary()
    data = {
        "backend": summary.backend,
        "total_records": summary.total_records,
        "memory_usage_bytes": summary.memory_usage_bytes,
        "max_memory_bytes": summary.max_memory_bytes,
        "oldest_timestamp": (
            summary.oldest_timestamp.isoformat() if summary.oldest_timestamp else None
        ),
        "newest_timestamp": (
            summary.newest_timestamp.isoformat() if summary.newest_timestamp else None
        ),
        "meters_tracked": summary.meters_tracked,
    }
    return Response(json.dumps(data), media_type="application/json")


@router.post("/seed")
@log_execution_time
def seed_history(
    request: Request,
    days: int = 14,
    meter: str = "total",
    base_val: float = 300.0,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(
            json.dumps({"error": "Storage backend disabled", "seeded": 0}),
            media_type="application/json",
            status_code=400,
        )
    count = seed_demo_history(storage, meter_name=meter, days=days, base_val=base_val)
    return Response(
        json.dumps(
            {"message": f"Successfully seeded {count} records", "seeded": count}
        ),
        media_type="application/json",
    )


@router.post("/clear")
@log_execution_time
def clear_history(request: Request) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(
            json.dumps({"error": "Storage backend disabled"}),
            media_type="application/json",
            status_code=400,
        )
    storage.clear()
    return Response(
        json.dumps({"message": "History cleared successfully"}),
        media_type="application/json",
    )
