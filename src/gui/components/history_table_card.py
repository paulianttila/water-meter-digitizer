"""Historical Meter Readings Table Component for NiceGUI."""

import json
from datetime import datetime, timedelta
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.theme import (
    DIALOG_CARD,
    DIALOG_HEADER_ROW,
    HEADING_SECTION,
    HEADING_SUBSECTION,
    ROW_ACTIONS,
    ROW_HEADER,
)
from storage.base import ReadingRecord
from storage.seed import seed_demo_history


class HistoryTableCard:
    """Component rendering historical readings in a searchable, paginated table with deep inspection and exports."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.current_meter = "total"
        self.record_limit = 100
        self.time_range_days = 7
        self.search_query = ""
        self.category_filter = "all"  # "all", "good", "anomalies", "flow", "snapshots"

    def render(self, container: ui.column) -> None:
        """Render the historical readings table inside the given container."""
        storage = self.callbacks.get_storage()
        if storage is None:
            with container:
                ui.label("History storage backend is disabled.").classes(
                    "text-gray-400 italic p-4"
                )
            return

        summary = storage.get_summary()
        tracked_meters = ["all"] + (summary.meters_tracked or ["total"])
        if self.current_meter not in tracked_meters:
            self.current_meter = tracked_meters[0]

        columns: list[dict[str, Any]] = [
            {
                "name": "id",
                "label": "#ID",
                "field": "id",
                "align": "center",
                "sortable": True,
                "classes": "font-mono text-xs text-slate-500",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
            {
                "name": "timestamp",
                "label": "Timestamp",
                "field": "timestamp",
                "required": True,
                "align": "left",
                "sortable": True,
                "classes": "font-mono text-xs text-gray-300",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
            {
                "name": "meters",
                "label": "Meter Readout",
                "field": "meters",
                "required": True,
                "align": "left",
                "sortable": True,
                "classes": "font-mono font-semibold text-xs text-cyan-300",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
            {
                "name": "digital",
                "label": "Digital Digits",
                "field": "digital",
                "align": "left",
                "classes": "font-mono text-xs text-cyan-200/90",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
            {
                "name": "analog",
                "label": "Analog Dials",
                "field": "analog",
                "align": "left",
                "classes": "font-mono text-xs text-amber-200/90",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
            {
                "name": "flow",
                "label": "Flow",
                "field": "flow",
                "align": "center",
                "sortable": True,
                "classes": "whitespace-nowrap min-w-[95px]",
                "headerClasses": "text-gray-400 font-semibold text-xs whitespace-nowrap min-w-[95px]",
                "style": "min-width: 95px; width: 95px;",
                "headerStyle": "min-width: 95px; width: 95px;",
            },
            {
                "name": "quality",
                "label": "Quality / Status",
                "field": "quality",
                "align": "center",
                "sortable": True,
                "classes": "whitespace-nowrap min-w-[125px]",
                "headerClasses": "text-gray-400 font-semibold text-xs whitespace-nowrap min-w-[125px]",
                "style": "min-width: 125px; width: 125px;",
                "headerStyle": "min-width: 125px; width: 125px;",
            },
            {
                "name": "actions",
                "label": "Inspect",
                "field": "id",
                "align": "center",
                "headerClasses": "text-gray-400 font-semibold text-xs",
            },
        ]

        with container:
            # 1. Top Controls Bar (instantiated once)
            with ui.row().classes(
                f"{ROW_HEADER} gap-3 flex-wrap "
                "bg-slate-900/60 p-3.5 rounded-2xl border border-white/10 shadow-lg backdrop-blur-md"
            ):

                def on_meter_change(e: Any) -> None:
                    self.current_meter = e.value
                    refresh_table()

                def on_limit_change(e: Any) -> None:
                    self.record_limit = int(e.value)
                    refresh_table()

                def on_range_change(e: Any) -> None:
                    self.time_range_days = int(e.value)
                    refresh_table()

                def on_category_change(e: Any) -> None:
                    self.category_filter = e.value
                    refresh_table()

                def on_search_change(e: Any) -> None:
                    self.search_query = (e.value or "").strip()
                    refresh_table()

                def on_seed_demo() -> None:
                    seed_demo_history(storage, "total", 14)
                    ui.notify("Seeded 14 days of demo readings", type="positive")
                    refresh_table()

                def on_clear() -> None:
                    storage.clear()
                    ui.notify("History cleared", type="info")
                    refresh_table()

                # Left Group: Filters
                with ui.row().classes("items-center gap-2.5 flex-wrap"):
                    ui.label("Meter:").classes("text-xs font-semibold text-gray-400")
                    ui.select(
                        options={m: m.upper() for m in tracked_meters},
                        value=self.current_meter,
                        on_change=on_meter_change,
                    ).props("dense outlined options-dense").classes(
                        "w-24 text-xs bg-slate-950 rounded-lg"
                    )

                    ui.label("Range:").classes("text-xs font-semibold text-gray-400")
                    ui.select(
                        options={
                            1: "24 Hours",
                            7: "7 Days",
                            14: "14 Days",
                            30: "30 Days",
                            0: "All Time",
                        },
                        value=self.time_range_days,
                        on_change=on_range_change,
                    ).props("dense outlined options-dense").classes(
                        "w-28 text-xs bg-slate-950 rounded-lg"
                    )

                    ui.label("Limit:").classes("text-xs font-semibold text-gray-400")
                    ui.select(
                        options={
                            50: "50 rows",
                            100: "100 rows",
                            250: "250 rows",
                            500: "500 rows",
                            1000: "1000 rows",
                        },
                        value=self.record_limit,
                        on_change=on_limit_change,
                    ).props("dense outlined options-dense").classes(
                        "w-28 text-xs bg-slate-950 rounded-lg"
                    )

                    # Category toggle
                    ui.toggle(
                        options={
                            "all": "All",
                            "good": "Good",
                            "anomalies": "Anomalies",
                            "flow": "Flow",
                            "snapshots": "Snapshots",
                        },
                        value=self.category_filter,
                        on_change=on_category_change,
                    ).props(
                        "dense rounded unelevated toggle-color=cyan text-color=grey-4"
                    ).classes(
                        "text-xs font-medium bg-slate-950/80 p-0.5"
                    )

                # Right Group: Search, Actions, Exports
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    ui.input(
                        placeholder="Search logs...",
                        value=self.search_query,
                        on_change=on_search_change,
                    ).props("dense outlined debounce=300 clearable").classes(
                        "w-40 text-xs bg-slate-950 rounded-lg"
                    )

                    def on_export_csv() -> None:
                        if not self.raw_readings:
                            ui.notify(
                                "No readings available to export",
                                type="warning",
                            )
                            return
                        lines = [
                            "ID,Timestamp,Meters,Quality,Avg_Confidence,Flow_Detected,Frame_Type,Digital_Digits,Analog_Dials,Error"
                        ]
                        for r in self.raw_readings:
                            rid = str(r.id or "")
                            ts = (
                                r.timestamp.astimezone().isoformat()
                                if r.timestamp
                                else ""
                            )
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
                            conf_val = (
                                f"{sum(conf_list) / len(conf_list):.1f}"
                                if conf_list
                                else "100.0"
                            )
                            flow_str = "true" if r.flow_detected else "false"
                            f_type = r.frame_type or ""
                            dig_str = "; ".join(
                                f"{k}:{v}" for k, v in r.digital_results.items()
                            )
                            ana_str = "; ".join(
                                f"{k}:{v}" for k, v in r.analog_results.items()
                            )
                            err_clean = (r.error or "").replace('"', '""')
                            lines.append(
                                f'{rid},"{ts}","{m_str}","{qual}",{conf_val},{flow_str},"{f_type}","{dig_str}","{ana_str}","{err_clean}"'
                            )
                        csv_text = "\n".join(lines)
                        ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"readings_{self.current_meter}_{ts_name}.csv"
                        ui.download(csv_text.encode("utf-8"), filename)
                        ui.notify(
                            f"Exported {len(self.raw_readings)} readings to {filename}",
                            type="positive",
                        )

                    def on_export_json() -> None:
                        if not self.raw_readings:
                            ui.notify(
                                "No readings available to export",
                                type="warning",
                            )
                            return
                        export_data = [
                            r.model_dump(mode="json") for r in self.raw_readings
                        ]
                        json_text = json.dumps(export_data, indent=2, default=str)
                        ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"readings_{self.current_meter}_{ts_name}.json"
                        ui.download(json_text.encode("utf-8"), filename)
                        ui.notify(
                            f"Exported {len(self.raw_readings)} readings to {filename}",
                            type="positive",
                        )

                    ui.button(icon="download", on_click=on_export_csv).props(
                        "flat dense round color=cyan aria-label='Export CSV'"
                    ).tooltip("Export CSV Data")

                    ui.button(icon="refresh", on_click=lambda: refresh_table()).props(
                        "flat dense round color=cyan aria-label='Refresh Readings'"
                    ).tooltip("Refresh Readings")

                    with (
                        ui.button(icon="more_vert").props(
                            "flat round dense color=gray aria-label='More options'"
                        ),
                        ui.menu().classes("bg-slate-900 border border-white/10"),
                    ):
                        ui.menu_item("Export CSV Data", on_click=on_export_csv).classes(
                            "text-xs text-cyan-300"
                        )
                        ui.menu_item(
                            "Export JSON Data", on_click=on_export_json
                        ).classes("text-xs text-cyan-300")
                        ui.menu_item(
                            "Seed 14d Demo Data", on_click=on_seed_demo
                        ).classes("text-xs text-gray-200")
                        ui.menu_item("Clear History", on_click=on_clear).classes(
                            "text-xs text-rose-400"
                        )

            # 2. Empty State Banner (No readings in range)
            with ui.element("div").classes(
                "w-full rounded-2xl border border-white/10 bg-slate-900/40 p-12 flex flex-col items-center justify-center gap-3"
            ) as no_readings_banner:
                no_readings_banner.visible = False
                ui.icon("history_toggle_off", color="gray").classes(
                    "text-5xl opacity-40"
                )
                ui.label(
                    "No historical reading records found in selected range."
                ).classes("text-sm text-gray-300 font-medium")
                ui.label(
                    "Readings will accumulate automatically as the digitizer captures meter frames."
                ).classes("text-xs text-gray-500")
                ui.button(
                    "Seed Demo Data",
                    icon="auto_fix_high",
                    on_click=on_seed_demo,
                ).props("unelevated color=primary size=sm").classes("mt-2 rounded-xl")

            # 3. KPI Summary Bar (persistent elements with in-place text mutation)
            with ui.row().classes("w-full gap-4 flex-wrap my-1") as kpi_row:
                kpi_row.visible = False

                # 1. Total Records
                with ui.element("div").classes(
                    "p-3.5 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                    "border border-white/10 shadow-lg flex-1 min-w-[150px]"
                ):
                    ui.label("TOTAL RECORDS").classes(
                        "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                    )
                    with ui.row().classes("items-baseline gap-1.5 mt-0.5"):
                        kpi_total_label = ui.label("0").classes(
                            "font-['Outfit'] text-2xl font-bold text-cyan-300"
                        )
                        kpi_total_sub_label = ui.label("").classes(
                            "text-xs font-semibold text-slate-500"
                        )
                        kpi_total_sub_label.visible = False

                # 2. Success / Health Rate
                with ui.element("div").classes(
                    "p-3.5 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                    "border border-white/10 shadow-lg flex-1 min-w-[150px]"
                ):
                    ui.label("READING HEALTH").classes(
                        "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                    )
                    with ui.row().classes("items-baseline gap-1.5 mt-0.5"):
                        kpi_health_label = ui.label("100%").classes(
                            "font-['Outfit'] text-2xl font-bold text-emerald-300"
                        )
                        ui.label("Good").classes("text-xs font-semibold text-slate-400")

                # 3. Model Confidence
                with ui.element("div").classes(
                    "p-3.5 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                    "border border-white/10 shadow-lg flex-1 min-w-[150px]"
                ):
                    ui.label("AVG CONFIDENCE").classes(
                        "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                    )
                    with ui.row().classes("items-baseline gap-1.5 mt-0.5"):
                        kpi_conf_label = ui.label("100%").classes(
                            "font-['Outfit'] text-2xl font-bold text-white"
                        )
                        ui.label("Neural Score").classes(
                            "text-xs font-semibold text-slate-400"
                        )

                # 4. Flow Activity & Snapshots
                with ui.element("div").classes(
                    "p-3.5 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                    "border border-white/10 shadow-lg flex-1 min-w-[150px]"
                ):
                    ui.label("FLOW & SNAPSHOTS").classes(
                        "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                    )
                    with ui.row().classes("items-baseline gap-3 mt-0.5"):
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("water_drop", size="xs").classes("text-blue-400")
                            kpi_flow_label = ui.label("0").classes(
                                "font-['Outfit'] text-xl font-bold text-blue-300"
                            )
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("photo_camera", size="xs").classes("text-teal-400")
                            kpi_snapshot_label = ui.label("0").classes(
                                "font-['Outfit'] text-xl font-bold text-teal-300"
                            )

            def update_kpis(
                raw: list[ReadingRecord], filtered: list[ReadingRecord]
            ) -> None:
                total_loaded = len(raw)
                good_count = sum(
                    1
                    for r in raw
                    if not r.error
                    and next(
                        (m.quality for m in r.meters.values() if m.quality),
                        "good",
                    ).lower()
                    == "good"
                )
                health_pct = (
                    (good_count / total_loaded * 100.0) if total_loaded > 0 else 100.0
                )

                all_confs = [
                    m.confidence
                    for r in raw
                    for m in r.meters.values()
                    if getattr(m, "confidence", None) is not None
                ]
                avg_confidence = (
                    (sum(all_confs) / len(all_confs)) if all_confs else 100.0
                )
                flow_count = sum(1 for r in raw if r.flow_detected)
                snapshot_count = sum(1 for r in raw if r.frame_path or r.frame_type)

                kpi_total_label.text = str(len(filtered))
                if len(filtered) != total_loaded:
                    kpi_total_sub_label.text = f"/ {total_loaded}"
                    kpi_total_sub_label.visible = True
                else:
                    kpi_total_sub_label.visible = False

                health_color = (
                    "text-emerald-300"
                    if health_pct >= 95.0
                    else ("text-amber-300" if health_pct >= 85.0 else "text-rose-400")
                )
                kpi_health_label.text = f"{health_pct:.1f}%"
                kpi_health_label.classes(
                    replace=f"font-['Outfit'] text-2xl font-bold {health_color}"
                )

                kpi_conf_label.text = f"{avg_confidence:.1f}%"
                kpi_flow_label.text = str(flow_count)
                kpi_snapshot_label.text = str(snapshot_count)

            # 4. Filter Empty State (No search/category matches)
            with ui.element("div").classes(
                "w-full rounded-xl border border-white/10 bg-slate-900/40 p-8 flex flex-col items-center justify-center gap-2"
            ) as no_match_banner:
                no_match_banner.visible = False
                ui.icon("filter_list_off", color="gray").classes("text-4xl")
                ui.label(
                    "No readings match the active category or search query."
                ).classes("text-sm text-gray-400 font-medium")

            # 5. Persistent Quasar Table with Custom Visual Slots
            with ui.element("div").classes(
                "w-full rounded-2xl border border-white/10 overflow-hidden bg-slate-950/60 shadow-xl"
            ) as table_card:
                table_card.visible = False
                self.table = (
                    ui.table(
                        columns=columns,
                        rows=[],
                        row_key="id",
                        pagination=15,
                    )
                    .props("dark flat dense wrap-cells")
                    .classes("w-full")
                )

                # Flow badge slot
                self.table.add_slot(
                    "body-cell-flow",
                    """
                    <q-td :props="props" class="whitespace-nowrap">
                        <span v-if="props.value" class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30 whitespace-nowrap">
                            💧 Active
                        </span>
                        <span v-else class="inline-flex items-center text-[10px] text-slate-500 font-mono whitespace-nowrap">
                            ⏸️ Idle
                        </span>
                    </q-td>
                    """,
                )

                # Quality & Confidence slot
                self.table.add_slot(
                    "body-cell-quality",
                    """
                    <q-td :props="props" class="whitespace-nowrap">
                        <span v-if="props.value === 'GOOD'" class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 whitespace-nowrap">
                            {{ props.row.confidence }}% &bull; {{ props.value }}
                        </span>
                        <span v-else-if="props.value === 'ERROR'" class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 whitespace-nowrap">
                            {{ props.value }}
                        </span>
                        <span v-else-if="props.value === 'WARNING'" class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 whitespace-nowrap">
                            {{ props.row.confidence }}% &bull; {{ props.value }}
                        </span>
                        <span v-else class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">
                            {{ props.row.confidence }}% &bull; {{ props.value }}
                        </span>
                    </q-td>
                    """,
                )

                # Actions / Inspect slot
                self.table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props" auto-width>
                        <q-btn flat round dense size="sm" icon="visibility" color="cyan" @click="() => $parent.$emit('inspect_reading', props.value)" />
                    </q-td>
                    """,
                )

                def on_inspect_reading(e: Any) -> None:
                    reading_id = e.args if hasattr(e, "args") else e
                    if reading_id in self.reading_map:
                        self.open_reading_dialog(self.reading_map[reading_id])

                self.table.on("inspect_reading", on_inspect_reading)

            def refresh_table() -> None:
                start_time = (
                    datetime.now().astimezone() - timedelta(days=self.time_range_days)
                    if self.time_range_days > 0
                    else None
                )

                filter_meter = (
                    None if self.current_meter == "all" else self.current_meter
                )
                self.raw_readings = storage.get_readings(
                    meter_name=filter_meter,
                    start=start_time,
                    limit=self.record_limit,
                )

                if not self.raw_readings:
                    no_readings_banner.visible = True
                    kpi_row.visible = False
                    no_match_banner.visible = False
                    table_card.visible = False
                    if self.table is not None:
                        self.table.rows = []
                    return

                no_readings_banner.visible = False

                # Build dataset and apply category & search filters
                filtered_readings: list[ReadingRecord] = []
                for r in self.raw_readings:
                    # Category Filter
                    qual = (
                        "ERROR"
                        if r.error
                        else (
                            next(
                                (m.quality for m in r.meters.values() if m.quality),
                                "good",
                            ).upper()
                        )
                    )
                    has_frame = bool(r.frame_path or r.frame_type)
                    flow_active = bool(r.flow_detected)

                    if self.category_filter == "good" and qual != "GOOD":
                        continue
                    if self.category_filter == "anomalies" and (
                        qual not in ("ERROR", "WARNING") and not r.error
                    ):
                        continue
                    if self.category_filter == "flow" and not flow_active:
                        continue
                    if self.category_filter == "snapshots" and not has_frame:
                        continue

                    # Search Query Filter
                    if self.search_query:
                        q_lower = self.search_query.lower()
                        time_text = (
                            r.timestamp.astimezone()
                            .strftime("%Y-%m-%d %H:%M:%S")
                            .lower()
                        )
                        meter_text = " ".join(
                            f"{k}:{v.value if v.value is not None else v.raw_value}"
                            for k, v in r.meters.items()
                        ).lower()
                        dig_text = " ".join(
                            f"{k}:{v}" for k, v in r.digital_results.items()
                        ).lower()
                        ana_text = " ".join(
                            f"{k}:{v}" for k, v in r.analog_results.items()
                        ).lower()
                        err_text = (r.error or "").lower()

                        if (
                            q_lower not in time_text
                            and q_lower not in meter_text
                            and q_lower not in dig_text
                            and q_lower not in ana_text
                            and q_lower not in err_text
                        ):
                            continue

                    filtered_readings.append(r)

                kpi_row.visible = True
                update_kpis(self.raw_readings, filtered_readings)

                if not filtered_readings:
                    no_match_banner.visible = True
                    table_card.visible = False
                    if self.table is not None:
                        self.table.rows = []
                    return

                no_match_banner.visible = False
                table_card.visible = True

                # Build row records and storage map for inspection dialog
                reading_map: dict[int, ReadingRecord] = {}
                rows = []
                for idx, r in enumerate(filtered_readings):
                    row_id = r.id if r.id is not None else idx
                    reading_map[row_id] = r

                    time_str = r.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")

                    meter_display_parts = []
                    for m_name, m_val in r.meters.items():
                        val_str = (
                            f"{m_val.value:.4f}"
                            if m_val.value is not None
                            else m_val.raw_value
                        )
                        unit_str = f" {m_val.unit}" if m_val.unit else ""
                        meter_display_parts.append(f"{m_name}: {val_str}{unit_str}")

                    meter_summary = ", ".join(meter_display_parts) or "—"

                    dig_str = (
                        " ".join(f"{k}:{v}" for k, v in r.digital_results.items())
                        if r.digital_results
                        else "—"
                    )
                    ana_str = (
                        " ".join(f"{k}:{v}" for k, v in r.analog_results.items())
                        if r.analog_results
                        else "—"
                    )

                    quality = (
                        "Error"
                        if r.error
                        else (
                            next(
                                (m.quality for m in r.meters.values() if m.quality),
                                "good",
                            )
                        )
                    )
                    conf_scores = [
                        m.confidence
                        for m in r.meters.values()
                        if getattr(m, "confidence", None) is not None
                    ]
                    avg_conf = (
                        round(sum(conf_scores) / len(conf_scores), 1)
                        if conf_scores
                        else 100.0
                    )

                    rows.append(
                        {
                            "id": row_id,
                            "timestamp": time_str,
                            "meters": meter_summary,
                            "digital": dig_str,
                            "analog": ana_str,
                            "quality": quality.upper(),
                            "confidence": avg_conf,
                            "flow": r.flow_detected,
                            "has_snapshot": bool(r.frame_path or r.frame_type),
                            "error": r.error or "",
                        }
                    )

                self.reading_map = reading_map
                if self.table is not None:
                    self.table.rows = rows

            # Initial render of table data and KPI cards
            refresh_table()

    def open_reading_dialog(self, record: ReadingRecord) -> None:
        """Open a detailed inspection modal for a specific reading record."""
        rec_id = record.id or 0
        ts_str = record.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        frame_data_uri = self.callbacks.get_frame_data_uri(rec_id) if rec_id else None

        with (
            ui.dialog() as dialog,
            ui.card().classes(
                f"{DIALOG_CARD} min-w-[340px] md:min-w-[680px] max-w-4xl"
            ),
        ):
            with ui.row().classes(DIALOG_HEADER_ROW):
                with ui.row().classes(ROW_ACTIONS):
                    ui.icon("manage_search", size="sm").classes("text-cyan-400")
                    ui.label(f"Reading Record #{rec_id}").classes(
                        f"{HEADING_SECTION} text-lg text-white"
                    )
                    if record.flow_detected:
                        ui.badge("💧 Flow Detected", color="blue").classes(
                            "text-xs font-bold"
                        )
                    if record.error:
                        ui.badge("⚠️ Error", color="negative").classes(
                            "text-xs font-bold"
                        )

                ui.button(icon="close", on_click=dialog.close).props(
                    "flat round dense color=gray aria-label='Close dialog'"
                )

            with ui.column().classes("w-full gap-4 mt-4"):
                # Top Metadata Info
                with ui.row().classes(
                    f"{ROW_HEADER} bg-slate-950/60 p-3 rounded-xl border border-white/5 text-xs font-mono"
                ):
                    with ui.row().classes("items-center gap-1 text-slate-300"):
                        ui.icon("schedule", size="xs").classes("text-cyan-400")
                        ui.label(f"Timestamp: {ts_str}")

                    frame_type_str = record.frame_type or (
                        "Snapshot Saved" if frame_data_uri else "Numeric Only"
                    )
                    ui.badge(
                        f"Frame: {frame_type_str}",
                        color="teal" if frame_data_uri else "grey-8",
                    ).classes("text-xs font-mono")

                # Meter Readout Values
                if record.meters:
                    with ui.column().classes("w-full gap-1.5"):
                        ui.label("Meter Readouts & Post-Processed Values").classes(
                            HEADING_SUBSECTION
                        )
                        with ui.row().classes("w-full gap-3 flex-wrap"):
                            for m_name, m_val in record.meters.items():
                                with ui.element("div").classes(
                                    "flex-1 min-w-[160px] p-3 rounded-xl bg-slate-950/80 border border-white/10"
                                ):
                                    ui.label(m_name.upper()).classes(
                                        "text-[10px] font-mono text-cyan-400 font-bold"
                                    )
                                    val_display = (
                                        f"{m_val.value:.4f}"
                                        if m_val.value is not None
                                        else m_val.raw_value
                                    )
                                    with ui.row().classes("items-baseline gap-1 mt-1"):
                                        ui.label(val_display).classes(
                                            "font-['Outfit'] text-xl font-bold text-white"
                                        )
                                        if m_val.unit:
                                            ui.label(m_val.unit).classes(
                                                "text-xs text-slate-400"
                                            )
                                    with ui.row().classes(
                                        "items-center gap-2 mt-1 text-[10px] text-slate-400"
                                    ):
                                        ui.label(
                                            f"Conf: {getattr(m_val, 'confidence', 100.0):.1f}%"
                                        )
                                        ui.label(f"Quality: {m_val.quality}")

                # Camera Snapshot Frame Preview (if stored)
                if frame_data_uri:
                    with ui.column().classes("w-full gap-1.5"):
                        ui.label("Camera Snapshot Capture").classes(
                            "text-xs font-bold text-slate-400 uppercase tracking-wider"
                        )
                        with ui.element("div").classes(
                            "w-full max-h-[320px] rounded-xl bg-black/50 p-2 border border-cyan-500/20 flex items-center justify-center overflow-hidden"
                        ):
                            ui.image(frame_data_uri).props(
                                "fit=contain no-spinner"
                            ).classes("max-w-full max-h-[300px] rounded-lg")

                # Segmented ROIs Breakdown (Digits & Dials)
                dig_res = record.digital_results
                ana_res = record.analog_results
                conf_scores = record.confidence_scores

                if dig_res or ana_res:
                    with ui.column().classes("w-full gap-2"):
                        ui.label(
                            "Neural Network Segmentations & Confidence Breakdown"
                        ).classes(
                            "text-xs font-bold text-slate-400 uppercase tracking-wider"
                        )
                        with ui.row().classes("w-full gap-3 flex-wrap"):
                            if dig_res:
                                with ui.card().classes(
                                    "flex-1 min-w-[240px] p-3 bg-slate-950/80 border border-white/10 rounded-xl"
                                ):
                                    ui.label("Digital Drums").classes(
                                        "text-xs font-bold text-cyan-300 mb-2"
                                    )
                                    with ui.row().classes("gap-2 flex-wrap"):
                                        for k, v in dig_res.items():
                                            c_val = conf_scores.get(
                                                f"digital_{k}", 98.0
                                            )
                                            with ui.column().classes(
                                                "items-center p-2 bg-slate-900 rounded-lg border border-white/5 min-w-[46px]"
                                            ):
                                                ui.label(str(v)).classes(
                                                    "text-lg font-bold font-mono text-cyan-300"
                                                )
                                                ui.label(f"#{k}").classes(
                                                    "text-[10px] text-slate-400"
                                                )
                                                ui.label(f"{c_val:.0f}%").classes(
                                                    "text-[9px] text-emerald-400 font-bold"
                                                )

                            if ana_res:
                                with ui.card().classes(
                                    "flex-1 min-w-[240px] p-3 bg-slate-950/80 border border-white/10 rounded-xl"
                                ):
                                    ui.label("Analog Needle Dials").classes(
                                        "text-xs font-bold text-amber-300 mb-2"
                                    )
                                    with ui.row().classes("gap-2 flex-wrap"):
                                        for k, v in ana_res.items():
                                            c_val = conf_scores.get(f"analog_{k}", 99.0)
                                            with ui.column().classes(
                                                "items-center p-2 bg-slate-900 rounded-lg border border-white/5 min-w-[46px]"
                                            ):
                                                ui.label(str(v)).classes(
                                                    "text-lg font-bold font-mono text-amber-300"
                                                )
                                                ui.label(f"#{k}").classes(
                                                    "text-[10px] text-slate-400"
                                                )
                                                ui.label(f"{c_val:.0f}%").classes(
                                                    "text-[9px] text-emerald-400 font-bold"
                                                )

                # Error Details
                if record.error:
                    with ui.element("div").classes(
                        "w-full p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs font-mono"
                    ):
                        ui.label(f"⚠️ Error Trace: {record.error}")

                # JSON Representation Expandable
                with ui.expansion("Raw JSON Data", icon="code").classes(
                    "w-full bg-slate-950/60 border border-white/5 rounded-xl text-xs text-slate-300"
                ):
                    raw_json_str = json.dumps(
                        record.model_dump(mode="json"), indent=2, default=str
                    )
                    ui.markdown(f"```json\n{raw_json_str}\n```").classes(
                        "w-full overflow-x-auto text-[11px]"
                    )

            with ui.row().classes(
                "w-full justify-end items-center mt-3 pt-3 border-t border-white/10"
            ):
                ui.button("Close", on_click=dialog.close).props(
                    "unelevated color=primary size=sm"
                ).classes("rounded-xl px-4")

        dialog.open()
