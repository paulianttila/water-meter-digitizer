"""Export utilities for historical meter readings (CSV and JSON formats)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from storage.base import ReadingRecord


def export_readings_csv(readings: list[ReadingRecord], meter_name: str) -> None:
    """Export reading records to CSV and trigger browser download."""
    if not readings:
        ui.notify("No readings available to export", type="warning")
        return

    lines = [
        "ID,Timestamp,Meters,Quality,Avg_Confidence,Flow_Detected,Frame_Type,Digital_Digits,Analog_Dials,Error"
    ]
    for r in readings:
        rid = str(r.id or "")
        ts = r.timestamp.astimezone().isoformat() if r.timestamp else ""
        m_parts = [
            f"{k}={v.value if v.value is not None else v.raw_value}{v.unit}"
            for k, v in r.meters.items()
        ]
        m_str = "; ".join(m_parts)
        qual = (
            "ERROR"
            if r.error
            else next(
                (m.quality for m in r.meters.values() if m.quality),
                "good",
            ).upper()
        )
        conf_list = [
            m.confidence
            for m in r.meters.values()
            if getattr(m, "confidence", None) is not None
        ]
        conf_val = f"{sum(conf_list) / len(conf_list):.1f}" if conf_list else "100.0"
        flow_str = "true" if r.flow_detected else "false"
        f_type = r.frame_type or ""
        dig_str = "; ".join(f"{k}:{v}" for k, v in r.digital_results.items())
        ana_str = "; ".join(f"{k}:{v}" for k, v in r.analog_results.items())
        err_clean = (r.error or "").replace('"', '""')
        lines.append(
            f'{rid},"{ts}","{m_str}","{qual}",{conf_val},{flow_str},"{f_type}","{dig_str}","{ana_str}","{err_clean}"'
        )

    csv_text = "\n".join(lines)
    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"readings_{meter_name}_{ts_name}.csv"
    ui.download(csv_text.encode("utf-8"), filename)
    ui.notify(
        f"Exported {len(readings)} readings to {filename}",
        type="positive",
    )


def export_readings_json(readings: list[ReadingRecord], meter_name: str) -> None:
    """Export reading records to JSON and trigger browser download."""
    if not readings:
        ui.notify("No readings available to export", type="warning")
        return

    export_data = [r.model_dump(mode="json") for r in readings]
    json_text = json.dumps(export_data, indent=2, default=str)
    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"readings_{meter_name}_{ts_name}.json"
    ui.download(json_text.encode("utf-8"), filename)
    ui.notify(
        f"Exported {len(readings)} readings to {filename}",
        type="positive",
    )
