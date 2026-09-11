"""Historical meter reading and consumption endpoints."""

import json
from datetime import UTC, datetime, timedelta

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request, Response

from decorators.decorators import log_execution_time
from storage.seed import seed_demo_history
from utils.visual_diff import (
    calculate_image_ssim,
    compress_image_to_bytes,
    generate_difference_heatmap,
)

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

    start = datetime.now(UTC) - timedelta(days=days) if days > 0 else None
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
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "meters": {k: v.model_dump() for k, v in r.meters.items()},
            "digital_results": r.digital_results,
            "analog_results": r.analog_results,
            "error": r.error,
            "frame_type": r.frame_type,
            "has_frame": bool(r.frame_type or r.frame_path),
            "flow_detected": r.flow_detected,
            "confidence_scores": r.confidence_scores,
        }
        for r in records
    ]
    return Response(json.dumps(data), media_type="application/json")


@router.get("/timeline")
@log_execution_time
def get_history_timeline(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    anomalies_only: bool = False,
    frames_only: bool = False,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps([]), media_type="application/json")

    records = storage.get_timeline(
        limit=limit,
        offset=offset,
        anomalies_only=anomalies_only,
        frames_only=frames_only,
    )
    data = [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "meters": {k: v.model_dump() for k, v in r.meters.items()},
            "digital_results": r.digital_results,
            "analog_results": r.analog_results,
            "error": r.error,
            "frame_type": r.frame_type,
            "has_frame": bool(r.frame_type or r.frame_path),
            "flow_detected": r.flow_detected,
            "confidence_scores": r.confidence_scores,
        }
        for r in records
    ]
    return Response(json.dumps(data), media_type="application/json")


@router.get("/frame/{reading_id}")
@log_execution_time
def get_snapshot_frame(reading_id: int, request: Request) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=404, detail="Storage not available")

    data, mime = storage.get_frame_bytes(reading_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Frame not found")

    return Response(content=data, media_type=mime or "image/jpeg")


@router.get("/frame/{reading_id}/diff")
@log_execution_time
def get_frame_diff(
    reading_id: int,
    request: Request,
    compare_id: int | None = Query(default=None),
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=404, detail="Storage not available")

    cur_bytes, _ = storage.get_frame_bytes(reading_id)
    if not cur_bytes:
        raise HTTPException(status_code=404, detail="Current frame not found")

    comp_bytes = None
    if compare_id is not None:
        comp_bytes, _ = storage.get_frame_bytes(compare_id)
    else:
        # Fallback: compare with previous reading in timeline
        records = storage.get_timeline(limit=5)
        for rec in records:
            if rec.id is not None and rec.id != reading_id and rec.frame_type:
                comp_bytes, _ = storage.get_frame_bytes(rec.id)
                compare_id = rec.id
                break

    if not comp_bytes:
        # Self compare fallback
        comp_bytes = cur_bytes

    cur_img = cv2.imdecode(np.frombuffer(cur_bytes, np.uint8), cv2.IMREAD_COLOR)
    comp_img = cv2.imdecode(np.frombuffer(comp_bytes, np.uint8), cv2.IMREAD_COLOR)

    if cur_img is None or comp_img is None:
        raise HTTPException(status_code=500, detail="Failed decoding image bytes")

    ssim_score = calculate_image_ssim(cur_img, comp_img)
    is_anomaly = ssim_score < 0.85

    return Response(
        json.dumps(
            {
                "reading_id": reading_id,
                "compare_id": compare_id,
                "ssim_similarity": ssim_score,
                "is_anomaly": is_anomaly,
                "diff_image_url": f"/history/frame/{reading_id}/diff_image?compare_id={compare_id or reading_id}",
            }
        ),
        media_type="application/json",
    )


@router.get("/frame/{reading_id}/diff_image")
@log_execution_time
def get_frame_diff_image(
    reading_id: int,
    request: Request,
    compare_id: int | None = Query(default=None),
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=404, detail="Storage not available")

    cur_bytes, _ = storage.get_frame_bytes(reading_id)
    if not cur_bytes:
        raise HTTPException(status_code=404, detail="Current frame not found")

    comp_bytes = None
    if compare_id is not None and compare_id != reading_id:
        comp_bytes, _ = storage.get_frame_bytes(compare_id)
    if not comp_bytes:
        comp_bytes = cur_bytes

    cur_img = cv2.imdecode(np.frombuffer(cur_bytes, np.uint8), cv2.IMREAD_COLOR)
    comp_img = cv2.imdecode(np.frombuffer(comp_bytes, np.uint8), cv2.IMREAD_COLOR)

    if cur_img is None or comp_img is None:
        raise HTTPException(status_code=500, detail="Failed decoding images")

    heatmap = generate_difference_heatmap(cur_img, comp_img)
    diff_bytes = compress_image_to_bytes(heatmap, format_type="jpeg", quality=80)
    return Response(content=diff_bytes, media_type="image/jpeg")


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
        "total_snapshots": summary.total_snapshots,
        "snapshot_disk_bytes": summary.snapshot_disk_bytes,
        "snapshot_mode": summary.snapshot_mode,
    }
    return Response(json.dumps(data), media_type="application/json")


@router.post("/snapshots/prune")
@log_execution_time
def prune_snapshots_endpoint(
    request: Request,
    retention_days: int | None = None,
    max_disk_mb: float | None = None,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=400, detail="Storage backend not active")
    deleted = storage.prune_snapshots(
        retention_days=retention_days, max_disk_mb=max_disk_mb
    )
    return Response(
        json.dumps(
            {"message": f"Pruned {deleted} snapshots", "deleted_count": deleted}
        ),
        media_type="application/json",
    )


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
