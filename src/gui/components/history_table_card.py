"""Historical Meter Readings Table Component for NiceGUI."""

from datetime import UTC, datetime, timedelta
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from storage.seed import seed_demo_history


class HistoryTableCard:
    """Component rendering historical readings in a searchable, paginated table."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.current_meter = "total"
        self.record_limit = 100
        self.time_range_days = 7

    def render(self, container: ui.column) -> None:
        """Render the historical readings table inside the given container."""

        def refresh_table() -> None:
            container.clear()
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

            start_time = (
                datetime.now(UTC) - timedelta(days=self.time_range_days)
                if self.time_range_days > 0
                else None
            )

            filter_meter = None if self.current_meter == "all" else self.current_meter
            readings = storage.get_readings(
                meter_name=filter_meter,
                start=start_time,
                limit=self.record_limit,
            )

            with container:
                # Top Filter Bar
                with ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap "
                    "bg-slate-900/60 p-3 rounded-xl border border-white/10"
                ):

                    def on_meter_change(e) -> None:
                        self.current_meter = e.value
                        refresh_table()

                    def on_limit_change(e) -> None:
                        self.record_limit = int(e.value)
                        refresh_table()

                    def on_range_change(e) -> None:
                        self.time_range_days = int(e.value)
                        refresh_table()

                    def on_seed_demo() -> None:
                        seed_demo_history(storage, "total", 14)
                        ui.notify("Seeded 14 days of demo readings", type="positive")
                        refresh_table()

                    def on_clear() -> None:
                        storage.clear()
                        ui.notify("History cleared", type="info")
                        refresh_table()

                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.label("Meter:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options={m: m.upper() for m in tracked_meters},
                            value=self.current_meter,
                            on_change=on_meter_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950"
                        )

                        ui.label("Range:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
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
                            "w-28 text-xs bg-slate-950"
                        )

                        ui.label("Limit:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options={
                                50: "50 rows",
                                100: "100 rows",
                                250: "250 rows",
                                500: "500 rows",
                            },
                            value=self.record_limit,
                            on_change=on_limit_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950"
                        )

                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            "Refresh",
                            icon="refresh",
                            on_click=refresh_table,
                        ).props("flat dense color=cyan text-xs")

                        with (
                            ui.button(icon="more_vert").props(
                                "flat round dense color=gray"
                            ),
                            ui.menu().classes("bg-slate-900 border border-white/10"),
                        ):
                            ui.menu_item(
                                "Seed 14d Demo Data", on_click=on_seed_demo
                            ).classes("text-xs text-gray-200")
                            ui.menu_item("Clear History", on_click=on_clear).classes(
                                "text-xs text-rose-400"
                            )

                if not readings:
                    with ui.element("div").classes(
                        "w-full rounded-xl border border-white/10 bg-slate-900/40 p-8 flex flex-col items-center justify-center gap-3"
                    ):
                        ui.icon("history_toggle_off", color="gray").classes("text-4xl")
                        ui.label(
                            "No historical reading records found in selected range."
                        ).classes("text-sm text-gray-400")
                        ui.button(
                            "Seed Demo Data",
                            icon="auto_fix_high",
                            on_click=on_seed_demo,
                        ).props("unelevated color=primary size=sm")
                    return

                # Build Table Rows & Columns
                rows = []
                for idx, r in enumerate(readings):
                    time_str = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                    # Primary reading summary
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

                    # Digital results string
                    dig_str = (
                        " ".join(f"{k}:{v}" for k, v in r.digital_results.items())
                        if r.digital_results
                        else "—"
                    )

                    # Analog results string
                    ana_str = (
                        " ".join(f"{k}:{v}" for k, v in r.analog_results.items())
                        if r.analog_results
                        else "—"
                    )

                    # Status / Quality & Confidence
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
                            "id": idx,
                            "timestamp": time_str,
                            "meters": meter_summary,
                            "digital": dig_str,
                            "analog": ana_str,
                            "quality": quality.upper(),
                            "confidence": avg_conf,
                            "error": r.error or "",
                        }
                    )

                columns: list[dict[str, Any]] = [
                    {
                        "name": "timestamp",
                        "label": "Timestamp (UTC)",
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
                        "classes": "font-mono text-xs text-gray-300",
                        "headerClasses": "text-gray-400 font-semibold text-xs",
                    },
                    {
                        "name": "analog",
                        "label": "Analog Dials",
                        "field": "analog",
                        "align": "left",
                        "classes": "font-mono text-xs text-gray-300",
                        "headerClasses": "text-gray-400 font-semibold text-xs",
                    },
                    {
                        "name": "quality",
                        "label": "Quality / Status",
                        "field": "quality",
                        "align": "center",
                        "sortable": True,
                        "classes": "text-xs font-semibold",
                        "headerClasses": "text-gray-400 font-semibold text-xs",
                    },
                ]

                with ui.element("div").classes(
                    "w-full rounded-xl border border-white/10 overflow-hidden bg-slate-950/40"
                ):
                    table = (
                        ui.table(
                            columns=columns,
                            rows=rows,
                            row_key="id",
                            pagination=15,
                        )
                        .props("dark flat dense wrap-cells")
                        .classes("w-full")
                    )

                    table.add_slot(
                        "body-cell-quality",
                        """
                        <q-td :props="props">
                            <span v-if="props.value === 'GOOD'" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                {{ props.row.confidence }}% &bull; {{ props.value }}
                            </span>
                            <span v-else-if="props.value === 'ERROR'" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                                {{ props.value }}
                            </span>
                            <span v-else-if="props.value === 'WARNING'" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                {{ props.row.confidence }}% &bull; {{ props.value }}
                            </span>
                            <span v-else class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-cyan-400 border border-cyan-500/30">
                                {{ props.row.confidence }}% &bull; {{ props.value }}
                            </span>
                        </q-td>
                        """,
                    )

        refresh_table()
