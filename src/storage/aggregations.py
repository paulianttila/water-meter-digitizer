"""Time-series aggregations and consumption calculations for historical meter readings."""

from collections import defaultdict
from datetime import datetime
from typing import Literal

from .base import ConsumptionRecord, ReadingRecord


def aggregate_consumption(
    readings: list[ReadingRecord],
    meter_name: str = "total",
    interval: Literal["hourly", "daily", "weekly", "monthly"] = "daily",
    is_flow_rate: bool = False,
) -> list[ConsumptionRecord]:
    """Group chronological meter readings into regular time bins and calculate consumption."""
    if not readings:
        return []

    def get_bucket_key(ts: datetime) -> str:
        if interval == "hourly":
            return ts.strftime("%Y-%m-%d %H:00")
        if interval == "weekly":
            return f"{ts.year}-W{ts.isocalendar()[1]:02d}"
        if interval == "monthly":
            return ts.strftime("%Y-%m")
        return ts.strftime("%Y-%m-%d")

    bucket_groups: dict[str, list[tuple[datetime, float, str]]] = defaultdict(list)
    for r in readings:
        if meter_name in r.meters:
            m = r.meters[meter_name]
            if m.value is not None:
                b_key = get_bucket_key(r.timestamp)
                bucket_groups[b_key].append((r.timestamp, m.value, m.unit))

    sorted_buckets = sorted(bucket_groups.keys())
    consumption_records: list[ConsumptionRecord] = []

    prev_end_value: float | None = None
    prev_end_time: datetime | None = None

    for b_key in sorted_buckets:
        items = bucket_groups[b_key]
        if not items:
            continue

        items_sorted = sorted(items, key=lambda x: x[0])
        start_t = items_sorted[0][0]
        end_t = items_sorted[-1][0]
        raw_unit = items_sorted[0][2]
        unit = raw_unit.split("/")[0] if is_flow_rate and "/" in raw_unit else raw_unit
        values = [x[1] for x in items_sorted]

        start_v = values[0]
        end_v = values[-1]
        min_v = min(values)
        max_v = max(values)
        cnt = len(values)

        bucket_delta = 0.0

        if is_flow_rate:
            divisor = 3600.0  # default per hour
            lower_u = raw_unit.lower()
            if "min" in lower_u:
                divisor = 60.0
            elif "/s" in lower_u or "sec" in lower_u:
                divisor = 1.0

            # Cross-bucket trapezoidal segment if previous reading is available
            if prev_end_time is not None and prev_end_value is not None:
                cross_dt = (start_t - prev_end_time).total_seconds()
                if 0 < cross_dt <= 7200.0:
                    avg_cross = (prev_end_value + start_v) / 2.0
                    bucket_delta += max(0.0, avg_cross * (cross_dt / divisor))

            # Within-bucket trapezoidal integration
            for i in range(1, len(items_sorted)):
                dt = (items_sorted[i][0] - items_sorted[i - 1][0]).total_seconds()
                if dt > 0:
                    avg_rate = (values[i] + values[i - 1]) / 2.0
                    bucket_delta += max(0.0, avg_rate * (dt / divisor))
        else:
            # Delta within bucket for cumulative meters
            for i in range(1, len(values)):
                diff = values[i] - values[i - 1]
                if diff > 0:
                    bucket_delta += diff

            # If there was a previous bucket reading, include cross-bucket jump
            if prev_end_value is not None:
                cross_diff = start_v - prev_end_value
                if 0 < cross_diff < 1000.0:
                    bucket_delta += cross_diff

        prev_end_value = end_v
        prev_end_time = end_t

        consumption_records.append(
            ConsumptionRecord(
                bucket=b_key,
                start_time=start_t,
                end_time=end_t,
                meter_name=meter_name,
                unit=unit,
                consumption=round(bucket_delta, 3),
                start_value=start_v,
                end_value=end_v,
                min_value=min_v,
                max_value=max_v,
                reading_count=cnt,
            )
        )

    return consumption_records
