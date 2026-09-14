"""Historical Consumption Analytics Component for NiceGUI."""

from datetime import datetime, timedelta

from nicegui import ui

from callbacks import Callbacks
from storage.seed import seed_demo_history


class ConsumptionCard:
    """Component rendering historical consumption analytics, aggregations, and charts."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.current_meter = "total"
        self.current_interval = "daily"
        self.current_days = 14
        self.chart_style = "bar"
        self.view_mode = "combo"  # "differential", "cumulative", "combo"
        self.unit_mode = "L"  # "L" (Liters) or "m3" (Cubic meters)
        self.cumulative = False  # Backward-compatible property

    def render(self, container: ui.column) -> None:
        """Render the consumption view inside the provided container."""

        def render_consumption() -> None:
            container.clear()
            storage = self.callbacks.get_storage()
            if storage is None:
                with container:
                    ui.label("History storage backend is disabled.").classes(
                        "text-gray-400 italic p-4"
                    )
                return

            summary = storage.get_summary()
            tracked_meters = summary.meters_tracked or ["total"]
            if self.current_meter not in tracked_meters:
                self.current_meter = tracked_meters[0]

            now = datetime.now().astimezone()
            start_time = (
                now - timedelta(days=self.current_days)
                if self.current_days > 0
                else None
            )
            records = storage.get_consumption(
                meter_name=self.current_meter,
                interval=self.current_interval,  # type: ignore
                start=start_time,
            )

            # Prior period query for trend comparisons
            prior_total_m3: float | None = None
            if self.current_days > 0 and start_time is not None:
                prior_start = start_time - timedelta(days=self.current_days)
                prior_records = storage.get_consumption(
                    meter_name=self.current_meter,
                    interval=self.current_interval,  # type: ignore
                    start=prior_start,
                    end=start_time,
                )
                if prior_records:
                    prior_total_m3 = sum(
                        r.consumption
                        for r in prior_records
                        if r.consumption is not None
                    )

            # Unit conversion factors
            scale = 1000.0 if self.unit_mode == "L" else 1.0
            unit_label = "L" if self.unit_mode == "L" else "m³"
            cum_unit_label = "m³"

            with container:
                # Top Controls
                with ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap "
                    "bg-slate-900/60 p-3.5 rounded-2xl border border-white/10 shadow-lg backdrop-blur-md"
                ):

                    def on_meter_change(e) -> None:
                        self.current_meter = e.value
                        render_consumption()

                    def on_interval_change(e) -> None:
                        self.current_interval = e.value
                        render_consumption()

                    def on_days_change(e) -> None:
                        self.current_days = int(e.value)
                        render_consumption()

                    def on_view_mode_change(e) -> None:
                        self.view_mode = e.value
                        self.cumulative = e.value == "cumulative"
                        render_consumption()

                    def on_unit_mode_change(e) -> None:
                        self.unit_mode = e.value
                        render_consumption()

                    def on_style_change(e) -> None:
                        self.chart_style = e.value
                        render_consumption()

                    def on_export_csv() -> None:
                        if not records:
                            ui.notify("No records available to export", type="warning")
                            return
                        lines = [
                            "Bucket,Start Time,End Time,Consumption (m3),Consumption (L),End Reading (m3),Reading Count"
                        ]
                        for r in records:
                            st = r.start_time.isoformat() if r.start_time else ""
                            et = r.end_time.isoformat() if r.end_time else ""
                            c_m3 = f"{r.consumption or 0.0:.4f}"
                            c_l = f"{(r.consumption or 0.0) * 1000.0:.2f}"
                            ev = f"{r.end_value:.4f}" if r.end_value is not None else ""
                            lines.append(
                                f'"{r.bucket}","{st}","{et}",{c_m3},{c_l},{ev},{r.reading_count}'
                            )
                        csv_text = "\n".join(lines)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"consumption_{self.current_meter}_{self.current_interval}_{ts}.csv"
                        ui.download(csv_text.encode("utf-8"), filename)
                        ui.notify(
                            f"Exported {len(records)} records to {filename}",
                            type="positive",
                        )

                    def on_seed_demo() -> None:
                        seed_demo_history(storage, self.current_meter, 14)
                        ui.notify("Seeded 14 days of demo readings", type="positive")
                        render_consumption()

                    def on_clear_history() -> None:
                        storage.clear()
                        ui.notify("History cleared", type="info")
                        render_consumption()

                    # Left Group: Filters
                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.label("Meter:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options=tracked_meters,
                            value=self.current_meter,
                            on_change=on_meter_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950 rounded-lg"
                        )

                        ui.label("Interval:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options={
                                "hourly": "Hourly",
                                "daily": "Daily",
                                "weekly": "Weekly",
                                "monthly": "Monthly",
                            },
                            value=self.current_interval,
                            on_change=on_interval_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950 rounded-lg"
                        )

                        ui.label("Range:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options={
                                7: "7 Days",
                                14: "14 Days",
                                30: "30 Days",
                                90: "90 Days",
                                0: "All Time",
                            },
                            value=self.current_days,
                            on_change=on_days_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950 rounded-lg"
                        )

                    # Right Group: Mode, Units, Style, and Actions
                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        # View Mode Toggle: Differential | Cumulative | Combo
                        ui.toggle(
                            options={
                                "differential": "Differential",
                                "cumulative": "Cumulative",
                                "combo": "Combo (Dual)",
                            },
                            value=self.view_mode,
                            on_change=on_view_mode_change,
                        ).props(
                            "dense rounded unelevated toggle-color=cyan text-color=grey-4"
                        ).classes(
                            "text-xs font-medium bg-slate-950/80 p-0.5"
                        )

                        # Unit Mode Toggle: Liters (L) vs m³
                        ui.toggle(
                            options={
                                "L": "Liters (L)",
                                "m3": "m³",
                            },
                            value=self.unit_mode,
                            on_change=on_unit_mode_change,
                        ).props(
                            "dense rounded unelevated toggle-color=indigo text-color=grey-4"
                        ).classes(
                            "text-xs font-medium bg-slate-950/80 p-0.5"
                        )

                        if self.view_mode in ("differential", "combo"):
                            ui.toggle(
                                options={"bar": "Bar", "line": "Line"},
                                value=self.chart_style,
                                on_change=on_style_change,
                            ).props(
                                "dense rounded unelevated toggle-color=primary text-color=grey-4"
                            ).classes(
                                "text-xs font-medium bg-slate-950/80 p-0.5"
                            )

                        ui.button(icon="download", on_click=on_export_csv).props(
                            "flat dense round color=cyan"
                        ).tooltip("Export CSV Data")

                        with (
                            ui.button(icon="more_vert").props(
                                "flat round dense color=gray"
                            ),
                            ui.menu().classes("bg-slate-900 border border-white/10"),
                        ):
                            ui.menu_item(
                                "Export CSV Data", on_click=on_export_csv
                            ).classes("text-xs text-cyan-300")
                            ui.menu_item(
                                "Seed 14d Demo Data", on_click=on_seed_demo
                            ).classes("text-xs text-gray-200")
                            ui.menu_item(
                                "Clear History", on_click=on_clear_history
                            ).classes("text-xs text-rose-400")

                # Metrics Summary KPI Bar
                total_delta_m3 = sum(
                    r.consumption for r in records if r.consumption is not None
                )
                total_delta_display = total_delta_m3 * scale
                avg_delta_display = (
                    (total_delta_display / len(records)) if records else 0.0
                )
                peak_record = (
                    max(records, key=lambda r: r.consumption or 0.0)
                    if records
                    else None
                )
                peak_val_display = (
                    ((peak_record.consumption or 0.0) * scale) if peak_record else 0.0
                )

                # Trend percentage vs prior period
                trend_diff_pct: float | None = None
                if (
                    prior_total_m3 is not None
                    and prior_total_m3 > 0.0001
                    and total_delta_m3 is not None
                ):
                    trend_diff_pct = (
                        (total_delta_m3 - prior_total_m3) / prior_total_m3 * 100.0
                    )

                # Projected monthly volume (30-day baseline)
                days_span = max(1, self.current_days) if self.current_days > 0 else 30
                projected_m3 = (total_delta_m3 / days_span) * 30.0
                projected_display = projected_m3 * scale

                with ui.row().classes("w-full gap-4 flex-wrap my-1"):
                    # 1. Total in Range
                    with ui.element("div").classes(
                        "p-4 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                        "border border-white/10 shadow-lg flex-1 min-w-[170px]"
                    ):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label("TOTAL CONSUMPTION").classes(
                                "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                            )
                            if trend_diff_pct is not None:
                                is_lower = trend_diff_pct <= 0
                                badge_bg = (
                                    "bg-emerald-950/80 text-emerald-300 border-emerald-500/30"
                                    if is_lower
                                    else "bg-amber-950/80 text-amber-300 border-amber-500/30"
                                )
                                icon = "trending_down" if is_lower else "trending_up"
                                with ui.row().classes(
                                    f"items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border {badge_bg}"
                                ):
                                    ui.icon(icon, size="xs")
                                    ui.label(f"{abs(trend_diff_pct):.1f}% vs prior")

                        with ui.row().classes("items-baseline gap-1.5 mt-1"):
                            fmt = (
                                f"{total_delta_display:.1f}"
                                if self.unit_mode == "L"
                                else f"{total_delta_display:.3f}"
                            )
                            ui.label(fmt).classes(
                                "font-['Outfit'] text-2xl font-bold text-cyan-300"
                            )
                            ui.label(unit_label).classes(
                                "text-xs font-semibold text-slate-400"
                            )
                            if self.unit_mode == "L":
                                ui.label(f"({total_delta_m3:.3f} m³)").classes(
                                    "text-[11px] font-mono text-slate-500 ml-1"
                                )

                    # 2. Average Consumption
                    with ui.element("div").classes(
                        "p-4 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                        "border border-white/10 shadow-lg flex-1 min-w-[170px]"
                    ):
                        ui.label(f"AVG PER {self.current_interval.upper()}").classes(
                            "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1.5 mt-1"):
                            fmt_avg = (
                                f"{avg_delta_display:.1f}"
                                if self.unit_mode == "L"
                                else f"{avg_delta_display:.3f}"
                            )
                            ui.label(fmt_avg).classes(
                                "font-['Outfit'] text-2xl font-bold text-white"
                            )
                            ui.label(
                                f"{unit_label}/{self.current_interval[:3]}"
                            ).classes("text-xs font-semibold text-slate-400")

                    # 3. Peak Record
                    with ui.element("div").classes(
                        "p-4 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                        "border border-white/10 shadow-lg flex-1 min-w-[170px]"
                    ):
                        ui.label("PEAK IN PERIOD").classes(
                            "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1.5 mt-1"):
                            fmt_peak = (
                                f"{peak_val_display:.1f}"
                                if self.unit_mode == "L"
                                else f"{peak_val_display:.3f}"
                            )
                            ui.label(fmt_peak).classes(
                                "font-['Outfit'] text-2xl font-bold text-emerald-300"
                            )
                            ui.label(unit_label).classes(
                                "text-xs font-semibold text-slate-400"
                            )
                            if peak_record:
                                ui.label(f"({peak_record.bucket})").classes(
                                    "text-[10px] font-mono text-slate-500 truncate max-w-[110px]"
                                )

                    # 4. Projected Monthly Volume
                    with ui.element("div").classes(
                        "p-4 rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-950/80 "
                        "border border-white/10 shadow-lg flex-1 min-w-[170px]"
                    ):
                        ui.label("ESTIMATED MONTHLY").classes(
                            "text-[11px] font-semibold text-slate-400 uppercase tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1.5 mt-1"):
                            fmt_proj = (
                                f"{projected_display:.1f}"
                                if self.unit_mode == "L"
                                else f"{projected_display:.3f}"
                            )
                            ui.label(fmt_proj).classes(
                                "font-['Outfit'] text-2xl font-bold text-purple-300"
                            )
                            ui.label(f"{unit_label}/mo").classes(
                                "text-xs font-semibold text-slate-400"
                            )

                if not records:
                    with ui.element("div").classes(
                        "w-full rounded-2xl border border-white/10 bg-slate-900/40 p-12 flex flex-col items-center justify-center gap-3"
                    ):
                        ui.icon("bar_chart", color="gray").classes(
                            "text-5xl opacity-40"
                        )
                        ui.label("No consumption records in selected range.").classes(
                            "text-sm text-gray-300 font-medium"
                        )
                        ui.label(
                            "Readings will accumulate automatically as the background poller runs."
                        ).classes("text-xs text-gray-500")
                        ui.button(
                            "Seed Demo Data",
                            icon="auto_fix_high",
                            on_click=on_seed_demo,
                        ).props("unelevated color=primary size=sm").classes(
                            "mt-2 rounded-xl"
                        )
                    return

                # Build ECharts JSON options
                buckets = [r.bucket for r in records]

                # 1. Differential Data Series
                diff_data = [
                    round(
                        (r.consumption or 0.0) * scale,
                        2 if self.unit_mode == "L" else 3,
                    )
                    for r in records
                ]

                # 2. Cumulative Meter Index Series (always in physical m³)
                running_total_m3 = 0.0
                cum_data = []
                for r in records:
                    if r.end_value is not None:
                        cum_data.append(round(r.end_value, 3))
                    else:
                        running_total_m3 += r.consumption or 0.0
                        cum_data.append(round(running_total_m3, 3))

                # Build Series and Axis Configurations based on view_mode
                series = []
                legend_data = []
                y_axis = []

                # Benchmark Reference Lines
                diff_avg = (
                    round(sum(diff_data) / len(diff_data), 2) if diff_data else 0.0
                )
                mark_line_diff = {
                    "silent": True,
                    "symbol": "none",
                    "data": [
                        {
                            "type": "average",
                            "name": "Avg",
                            "lineStyle": {
                                "color": "#f59e0b",
                                "type": "dashed",
                                "width": 1.5,
                            },
                            "label": {
                                "formatter": f"Avg: {diff_avg} {unit_label}",
                                "color": "#f59e0b",
                                "position": "end",
                                "fontSize": 10,
                            },
                        }
                    ],
                }
                mark_point_diff = {
                    "symbol": "pin",
                    "symbolSize": 36,
                    "data": [
                        {
                            "type": "max",
                            "name": "Peak",
                            "itemStyle": {"color": "#10b981"},
                            "label": {"fontSize": 9},
                        },
                    ],
                }

                if self.view_mode in ("differential", "combo"):
                    diff_name = f"Consumption ({unit_label})"
                    legend_data.append(diff_name)
                    series.append(
                        {
                            "name": diff_name,
                            "type": self.chart_style,
                            "yAxisIndex": 0,
                            "data": diff_data,
                            "smooth": True,
                            "markLine": mark_line_diff,
                            "markPoint": mark_point_diff,
                            "itemStyle": {
                                "color": {
                                    "type": "linear",
                                    "x": 0,
                                    "y": 0,
                                    "x2": 0,
                                    "y2": 1,
                                    "colorStops": [
                                        {"offset": 0, "color": "#06b6d4"},
                                        {"offset": 1, "color": "#2563eb"},
                                    ],
                                },
                                "borderRadius": (
                                    [6, 6, 0, 0] if self.chart_style == "bar" else 0
                                ),
                            },
                            "areaStyle": (
                                {
                                    "color": {
                                        "type": "linear",
                                        "x": 0,
                                        "y": 0,
                                        "x2": 0,
                                        "y2": 1,
                                        "colorStops": [
                                            {
                                                "offset": 0,
                                                "color": "rgba(6, 182, 212, 0.35)",
                                            },
                                            {
                                                "offset": 1,
                                                "color": "rgba(37, 99, 235, 0.02)",
                                            },
                                        ],
                                    }
                                }
                                if self.chart_style == "line"
                                else None
                            ),
                        }
                    )
                    y_axis.append(
                        {
                            "type": "value",
                            "name": f"Volume ({unit_label})",
                            "nameTextStyle": {"color": "#06b6d4"},
                            "axisLine": {
                                "show": True,
                                "lineStyle": {"color": "rgba(6, 182, 212, 0.4)"},
                            },
                            "splitLine": {
                                "lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}
                            },
                            "axisLabel": {"color": "#9ca3af"},
                        }
                    )

                if self.view_mode in ("cumulative", "combo"):
                    cum_name = f"Cumulative Reading ({cum_unit_label})"
                    legend_data.append(cum_name)
                    y_idx = 1 if self.view_mode == "combo" else 0
                    series.append(
                        {
                            "name": cum_name,
                            "type": "line",
                            "yAxisIndex": y_idx,
                            "data": cum_data,
                            "smooth": True,
                            "symbol": "circle",
                            "symbolSize": 5,
                            "itemStyle": {"color": "#10b981"},
                            "lineStyle": {
                                "color": "#10b981",
                                "width": 2.5,
                                "shadowColor": "rgba(16, 185, 129, 0.5)",
                                "shadowBlur": 8,
                            },
                            "areaStyle": (
                                {
                                    "color": {
                                        "type": "linear",
                                        "x": 0,
                                        "y": 0,
                                        "x2": 0,
                                        "y2": 1,
                                        "colorStops": [
                                            {
                                                "offset": 0,
                                                "color": "rgba(16, 185, 129, 0.3)",
                                            },
                                            {
                                                "offset": 1,
                                                "color": "rgba(16, 185, 129, 0.01)",
                                            },
                                        ],
                                    }
                                }
                                if self.view_mode == "cumulative"
                                else None
                            ),
                        }
                    )
                    if self.view_mode == "combo":
                        y_axis.append(
                            {
                                "type": "value",
                                "name": f"Index ({cum_unit_label})",
                                "nameTextStyle": {"color": "#10b981"},
                                "min": "dataMin",
                                "axisLine": {
                                    "show": True,
                                    "lineStyle": {"color": "rgba(16, 185, 129, 0.4)"},
                                },
                                "splitLine": {"show": False},
                                "axisLabel": {"color": "#9ca3af"},
                            }
                        )
                    else:
                        y_axis = [
                            {
                                "type": "value",
                                "name": f"Reading Index ({cum_unit_label})",
                                "min": "dataMin",
                                "axisLine": {
                                    "show": True,
                                    "lineStyle": {"color": "rgba(16, 185, 129, 0.4)"},
                                },
                                "splitLine": {
                                    "lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}
                                },
                                "axisLabel": {"color": "#9ca3af"},
                            }
                        ]

                echart_options = {
                    "tooltip": {
                        "trigger": "axis",
                        "backgroundColor": "rgba(15, 23, 42, 0.95)",
                        "borderColor": "rgba(255, 255, 255, 0.15)",
                        "textStyle": {"color": "#f8fafc"},
                    },
                    "legend": {
                        "data": legend_data,
                        "textStyle": {"color": "#9ca3af"},
                        "top": "0%",
                    },
                    "grid": {
                        "left": "3%",
                        "right": "4%",
                        "bottom": "14%",
                        "top": "12%",
                        "containLabel": True,
                    },
                    "xAxis": {
                        "type": "category",
                        "data": buckets,
                        "axisLine": {
                            "lineStyle": {"color": "rgba(255, 255, 255, 0.2)"}
                        },
                        "axisLabel": {
                            "color": "#9ca3af",
                            "rotate": 30 if len(buckets) > 10 else 0,
                        },
                    },
                    "yAxis": y_axis,
                    "dataZoom": [
                        {"type": "inside"},
                        {
                            "type": "slider",
                            "bottom": "0%",
                            "height": 18,
                            "borderColor": "transparent",
                            "textStyle": {"color": "#9ca3af"},
                            "fillerColor": "rgba(6, 182, 212, 0.2)",
                        },
                    ],
                    "series": series,
                }

                with ui.element("div").classes(
                    "w-full rounded-2xl border border-white/10 bg-slate-900/60 p-4 "
                    "h-[460px] shadow-xl"
                ):
                    ui.echart(echart_options).classes("w-full h-full")

        render_consumption()
