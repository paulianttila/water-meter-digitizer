"""Historical Consumption Analytics Component for NiceGUI."""

from datetime import UTC, datetime, timedelta

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
        self.cumulative = False

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

            start_time = (
                datetime.now(UTC) - timedelta(days=self.current_days)
                if self.current_days > 0
                else None
            )
            records = storage.get_consumption(
                meter_name=self.current_meter,
                interval=self.current_interval,  # type: ignore
                start=start_time,
            )

            with container:
                # Top Controls
                with ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap "
                    "bg-slate-900/60 p-3 rounded-xl border border-white/10"
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

                    def on_style_change(e) -> None:
                        self.chart_style = e.value
                        render_consumption()

                    def on_mode_change(e) -> None:
                        self.cumulative = e.value == "cumulative"
                        render_consumption()

                    def on_seed_demo() -> None:
                        seed_demo_history(storage, self.current_meter, 14)
                        ui.notify("Seeded 14 days of demo readings", type="positive")
                        render_consumption()

                    def on_clear_history() -> None:
                        storage.clear()
                        ui.notify("History cleared", type="info")
                        render_consumption()

                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.label("Meter:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options=tracked_meters,
                            value=self.current_meter,
                            on_change=on_meter_change,
                        ).props("dense outlined options-dense").classes(
                            "w-28 text-xs bg-slate-950"
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
                            "w-28 text-xs bg-slate-950"
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
                            "w-28 text-xs bg-slate-950"
                        )

                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.toggle(
                            options={
                                "differential": "Differential",
                                "cumulative": "Cumulative",
                            },
                            value=("cumulative" if self.cumulative else "differential"),
                            on_change=on_mode_change,
                        ).props("dense rounded unelevated toggle-color=cyan").classes(
                            "text-xs"
                        )

                        ui.toggle(
                            options={"bar": "Bar", "line": "Line"},
                            value=self.chart_style,
                            on_change=on_style_change,
                        ).props(
                            "dense rounded unelevated toggle-color=primary"
                        ).classes(
                            "text-xs"
                        )

                        with (
                            ui.button(icon="more_vert").props(
                                "flat round dense color=gray"
                            ),
                            ui.menu().classes("bg-slate-900 border border-white/10"),
                        ):
                            ui.menu_item(
                                "Seed 14d Demo Data", on_click=on_seed_demo
                            ).classes("text-xs text-gray-200")
                            ui.menu_item(
                                "Clear History", on_click=on_clear_history
                            ).classes("text-xs text-rose-400")

                # Metrics Summary Bar
                total_delta = sum(
                    r.consumption for r in records if r.consumption is not None
                )
                avg_delta = total_delta / len(records) if records else 0.0
                peak_record = (
                    max(records, key=lambda r: r.consumption or 0.0)
                    if records
                    else None
                )
                peak_val = peak_record.consumption if peak_record else 0.0

                with ui.row().classes("w-full gap-4 flex-wrap my-1"):
                    # 1. Total in Range
                    with ui.element("div").classes(
                        "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex-1 min-w-[160px]"
                    ):
                        ui.label("TOTAL CONSUMPTION").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{total_delta:.3f}").classes(
                                "font-['Outfit'] text-2xl font-bold text-cyan-300"
                            )
                            ui.label("m³").classes("text-xs text-gray-400")

                    # 2. Average Consumption
                    with ui.element("div").classes(
                        "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex-1 min-w-[160px]"
                    ):
                        ui.label(f"AVG PER {self.current_interval.upper()}").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{avg_delta:.3f}").classes(
                                "font-['Outfit'] text-2xl font-bold text-white"
                            )
                            ui.label("m³").classes("text-xs text-gray-400")

                    # 3. Peak Record
                    with ui.element("div").classes(
                        "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex-1 min-w-[160px]"
                    ):
                        ui.label("PEAK IN PERIOD").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{peak_val:.3f}").classes(
                                "font-['Outfit'] text-2xl font-bold text-emerald-300"
                            )
                            ui.label("m³").classes("text-xs text-gray-400")

                    # 4. Storage Info
                    with ui.element("div").classes(
                        "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex-1 min-w-[160px]"
                    ):
                        ui.label("TOTAL READINGS STORED").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{summary.total_records}").classes(
                                "font-['Outfit'] text-2xl font-bold text-purple-300"
                            )
                            ui.label("records").classes("text-xs text-gray-400")

                if not records:
                    with ui.element("div").classes(
                        "w-full rounded-xl border border-white/10 bg-slate-900/40 p-8 flex flex-col items-center justify-center gap-3"
                    ):
                        ui.icon("bar_chart", color="gray").classes("text-4xl")
                        ui.label("No consumption records in selected range.").classes(
                            "text-sm text-gray-400"
                        )
                        ui.button(
                            "Seed Demo Data",
                            icon="auto_fix_high",
                            on_click=on_seed_demo,
                        ).props("unelevated color=primary size=sm")
                    return

                # Build ECharts JSON options
                buckets = [r.bucket for r in records]
                if self.cumulative:
                    running_total = 0.0
                    chart_values = []
                    for r in records:
                        running_total += r.consumption or 0.0
                        chart_values.append(round(running_total, 3))
                else:
                    chart_values = [round(r.consumption or 0.0, 3) for r in records]

                series = [
                    {
                        "name": (
                            "Cumulative (m³)" if self.cumulative else "Consumption (m³)"
                        ),
                        "type": self.chart_style,
                        "data": chart_values,
                        "smooth": True,
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
                                [4, 4, 0, 0] if self.chart_style == "bar" else 0
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
                                            "color": "rgba(6, 182, 212, 0.4)",
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
                ]

                legend_data = [
                    "Cumulative (m³)" if self.cumulative else "Consumption (m³)"
                ]
                y_axis = {
                    "type": "value",
                    "name": "Volume (m³)",
                    "axisLine": {
                        "show": True,
                        "lineStyle": {"color": "rgba(255, 255, 255, 0.2)"},
                    },
                    "splitLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}},
                    "axisLabel": {"color": "#9ca3af"},
                }

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
                    "w-full rounded-xl border border-white/10 bg-slate-900/60 p-4 "
                    "h-[440px]"
                ):
                    ui.echart(echart_options).classes("w-full h-full")

        render_consumption()
