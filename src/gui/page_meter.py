import asyncio
import dataclasses
from datetime import datetime, timedelta, timezone
import json

from nicegui import ui

from callbacks import Callbacks
from storage.seed import seed_demo_history


class MeterPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.current_meter = "total"
        self.current_interval = "daily"
        self.current_days = 14
        self.chart_style = "bar"
        self.cumulative = False

    async def show(self) -> None:
        async def do_fetch() -> None:
            self.spinner.visible = True
            value_container.clear()
            try:
                await fetch_data()
            except Exception as e:
                ui.notify(
                    f"Error occurred: {e}",
                    position="bottom",
                    close_button="OK",
                    type="negative",
                    multi_line=True,
                    icon="error",
                    timeout=0,
                )
            self.spinner.visible = False
            render_consumption()

        async def fetch_data() -> None:
            result = await asyncio.to_thread(
                self.callbacks.get_meter_data, saveimages=True
            )

            with value_container:
                # 1. Metric Summary Cards
                with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
                    for meter in result.meters:
                        is_total = meter.name == "total"
                        bg_grad = (
                            "bg-gradient-to-tr from-blue-900/30 to-cyan-900/20 "
                            "border-blue-500/40 shadow-lg shadow-blue-500/10"
                            if is_total
                            else "bg-slate-900/60 border-white/10"
                        )
                        card_classes = (
                            "p-4 rounded-xl border flex-1 min-w-[200px] " f"{bg_grad}"
                        )
                        with ui.element("div").classes(card_classes):
                            with ui.row().classes(
                                "w-full justify-between items-center mb-1"
                            ):
                                ui.label(meter.name.upper()).classes(
                                    "text-xs font-semibold text-gray-400 tracking-wider"
                                )
                                if is_total:
                                    ui.label("PRIMARY").classes(
                                        "text-[10px] font-bold text-emerald-400 "
                                        "bg-emerald-500/10 px-2 py-0.5 rounded-full "
                                        "border border-emerald-500/30"
                                    )
                            with ui.row().classes("items-baseline gap-2"):
                                text_grad = (
                                    "text-transparent bg-clip-text "
                                    "bg-gradient-to-r from-white to-cyan-200"
                                    if is_total
                                    else "text-white"
                                )
                                val_classes = (
                                    f"font-['Outfit'] text-3xl font-extrabold "
                                    f"tracking-tight {text_grad}"
                                )
                                ui.label(str(meter.value)).classes(val_classes)
                                if meter.unit:
                                    ui.label(meter.unit).classes(
                                        "text-sm text-gray-400 font-semibold"
                                    )

                # 2. Main Processed Image & Crop Grids
                with ui.row().classes("w-full gap-6 items-start"):
                    # Processed image
                    with ui.column().classes("flex-1 min-w-[320px]"):
                        ui.label("Processed Capture").classes(
                            "font-['Outfit'] font-bold text-sm text-gray-300 mb-2"
                        )
                        with ui.element("div").classes(
                            "w-full rounded-xl bg-slate-950 p-2 border border-white/10 "
                            "flex items-center justify-center overflow-hidden"
                        ):
                            base64img = self.callbacks.get_image_as_base64_str("final")
                            ui.image(f"data:image/jpeg;base64,{base64img}").classes(
                                "w-full rounded-lg"
                            )

                    # Deductions Breakdown
                    with ui.column().classes("flex-1 min-w-[320px] gap-4"):
                        if result.digital_results:
                            ui.label("Digital Counters").classes(
                                "font-['Outfit'] font-bold text-sm text-gray-300"
                            )
                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                for image, value in result.digital_results.items():
                                    with ui.element("div").classes(
                                        "p-2.5 rounded-lg bg-slate-900/80 border "
                                        "border-white/10 flex flex-col items-center "
                                        "gap-1.5 min-w-[70px]"
                                    ):
                                        ui.label(image).classes(
                                            "text-[11px] text-gray-400 "
                                            "uppercase tracking-wider"
                                        )
                                        base64img = (
                                            self.callbacks.get_image_as_base64_str(
                                                image
                                            )
                                        )
                                        ui.image(
                                            f"data:image/jpeg;base64,{base64img}"
                                        ).props("fit=contain").classes(
                                            "w-14 h-24 rounded bg-slate-950 p-0.5"
                                        )
                                        ui.label(str(value)).classes(
                                            "font-['Outfit'] font-bold "
                                            "text-cyan-400 text-sm"
                                        )

                        if result.analog_results:
                            ui.label("Analog Dials").classes(
                                "font-['Outfit'] font-bold text-sm text-gray-300 mt-2"
                            )
                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                for image, value in result.analog_results.items():
                                    with ui.element("div").classes(
                                        "p-2.5 rounded-lg bg-slate-900/80 border "
                                        "border-white/10 flex flex-col items-center "
                                        "gap-1.5 min-w-[70px]"
                                    ):
                                        ui.label(image).classes(
                                            "text-[11px] text-gray-400 "
                                            "uppercase tracking-wider"
                                        )
                                        base64img = (
                                            self.callbacks.get_image_as_base64_str(
                                                image
                                            )
                                        )
                                        ui.image(
                                            f"data:image/jpeg;base64,{base64img}"
                                        ).props("fit=contain").classes(
                                            "w-16 h-16 rounded bg-slate-950 p-0.5"
                                        )
                                        ui.label(str(value)).classes(
                                            "font-['Outfit'] font-bold "
                                            "text-cyan-400 text-sm"
                                        )

            raw_container.clear()
            with raw_container:
                ui.code(
                    json.dumps(dataclasses.asdict(result), indent=4), language="json"
                ).classes(
                    "w-full rounded-lg bg-slate-950/80 border border-white/10 p-4"
                )

        def render_consumption() -> None:
            consumption_container.clear()
            storage = self.callbacks.get_storage()
            if storage is None:
                with consumption_container:
                    ui.label("History storage backend is disabled.").classes(
                        "text-gray-400 italic"
                    )
                return

            summary = storage.get_summary()
            tracked_meters = summary.meters_tracked or ["total"]
            if self.current_meter not in tracked_meters:
                self.current_meter = tracked_meters[0]

            start_time = (
                datetime.now(timezone.utc) - timedelta(days=self.current_days)
                if self.current_days > 0
                else None
            )
            records = storage.get_consumption(
                meter_name=self.current_meter,
                interval=self.current_interval,  # type: ignore
                start=start_time,
            )

            with consumption_container:
                # Top Controls
                with ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap "
                    "bg-slate-900/60 p-3 rounded-xl border border-white/10"
                ):
                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.label("Meter:").classes(
                            "text-xs font-semibold text-gray-400"
                        )
                        ui.select(
                            options=tracked_meters,
                            value=self.current_meter,
                            on_change=lambda e: (
                                setattr(self, "current_meter", e.value),
                                render_consumption(),
                            ),
                        ).props("dense outlined").classes("w-36")

                        ui.label("Interval:").classes(
                            "text-xs font-semibold text-gray-400 ml-2"
                        )
                        ui.toggle(
                            {"hourly": "Hourly", "daily": "Daily", "weekly": "Weekly"},
                            value=self.current_interval,
                            on_change=lambda e: (
                                setattr(self, "current_interval", e.value),
                                render_consumption(),
                            ),
                        ).props("dense toggle-color=cyan")

                        ui.label("Range:").classes(
                            "text-xs font-semibold text-gray-400 ml-2"
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
                            on_change=lambda e: (
                                setattr(self, "current_days", int(e.value)),
                                render_consumption(),
                            ),
                        ).props("dense outlined").classes("w-32")

                        ui.label("Style:").classes(
                            "text-xs font-semibold text-gray-400 ml-2"
                        )
                        ui.toggle(
                            {
                                "bar": "Bar",
                                "line": "Line",
                                "area": "Area",
                                "combined": "Combined",
                            },
                            value=self.chart_style,
                            on_change=lambda e: (
                                setattr(self, "chart_style", e.value),
                                render_consumption(),
                            ),
                        ).props("dense toggle-color=cyan")

                        ui.label("Mode:").classes(
                            "text-xs font-semibold text-gray-400 ml-2"
                        )
                        ui.toggle(
                            {"interval": "Interval", "cumulative": "Cumulative"},
                            value="cumulative" if self.cumulative else "interval",
                            on_change=lambda e: (
                                setattr(self, "cumulative", e.value == "cumulative"),
                                render_consumption(),
                            ),
                        ).props("dense toggle-color=cyan")

                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            "Seed Demo Data",
                            icon="sym_s_science",
                            on_click=lambda: (
                                seed_demo_history(storage, self.current_meter, 14),
                                ui.notify(
                                    "Seeded 14 days of demo readings",
                                    type="positive",
                                ),
                                render_consumption(),
                            ),
                        ).props("flat dense color=cyan text-color=cyan").classes(
                            "text-xs"
                        )
                        if summary.total_records > 0:
                            ui.button(
                                "Clear",
                                icon="delete_outline",
                                on_click=lambda: (
                                    storage.clear(),
                                    ui.notify("History cleared", type="info"),
                                    render_consumption(),
                                ),
                            ).props("flat dense color=grey text-color=grey-4").classes(
                                "text-xs"
                            )

                        mem_kb = round(summary.memory_usage_bytes / 1024, 1)
                        ui.label(
                            f"{summary.total_records} records ({mem_kb} KB in RAM)"
                        ).classes("text-xs text-gray-400")

                if not records:
                    with ui.element("div").classes(
                        "w-full p-8 rounded-xl border border-white/10 bg-slate-900/40 "
                        "flex flex-col items-center justify-center gap-3 text-center"
                    ):
                        ui.icon("bar_chart", color="gray").classes("text-5xl")
                        ui.label("No consumption records in selected range").classes(
                            "font-['Outfit'] font-bold text-lg text-gray-300"
                        )
                        ui.label(
                            "Trigger meter readouts or click 'Seed Demo Data' "
                            "to visualize consumption charts."
                        ).classes("text-xs text-gray-400 max-w-md")
                        ui.button(
                            "Generate Demo Data",
                            icon="auto_awesome",
                            on_click=lambda: (
                                seed_demo_history(storage, self.current_meter, 14),
                                ui.notify(
                                    "Seeded 14 days of demo readings",
                                    type="positive",
                                ),
                                render_consumption(),
                            ),
                        ).props("unelevated color=primary").classes(
                            "shadow-md shadow-blue-500/20 mt-2"
                        )
                    return

                # KPI Metrics Header
                total_cons = sum(r.consumption for r in records)
                unit = records[0].unit or "m³"
                avg_cons = total_cons / len(records) if len(records) > 0 else 0.0
                max_cons = max(r.consumption for r in records) if records else 0.0

                with ui.row().classes("w-full gap-4 flex-wrap my-2"):
                    with ui.element("div").classes(
                        "p-4 rounded-xl border border-blue-500/30 bg-blue-950/20 "
                        "flex-1 min-w-[160px]"
                    ):
                        ui.label("TOTAL CONSUMPTION").classes(
                            "text-[10px] font-bold text-blue-400 tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{total_cons:.3f}").classes(
                                "font-['Outfit'] text-2xl font-extrabold text-white"
                            )
                            ui.label(unit).classes(
                                "text-xs text-gray-400 font-semibold"
                            )

                    with ui.element("div").classes(
                        "p-4 rounded-xl border border-cyan-500/30 bg-cyan-950/20 "
                        "flex-1 min-w-[160px]"
                    ):
                        ui.label("AVERAGE PER BUCKET").classes(
                            "text-[10px] font-bold text-cyan-400 tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{avg_cons:.3f}").classes(
                                "font-['Outfit'] text-2xl font-extrabold text-white"
                            )
                            ui.label(unit).classes(
                                "text-xs text-gray-400 font-semibold"
                            )

                    with ui.element("div").classes(
                        "p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 "
                        "flex-1 min-w-[160px]"
                    ):
                        ui.label("PEAK BUCKET USAGE").classes(
                            "text-[10px] font-bold text-emerald-400 tracking-wider"
                        )
                        with ui.row().classes("items-baseline gap-1 mt-1"):
                            ui.label(f"{max_cons:.3f}").classes(
                                "font-['Outfit'] text-2xl font-extrabold text-white"
                            )
                            ui.label(unit).classes(
                                "text-xs text-gray-400 font-semibold"
                            )

                # Apache ECharts Interactive Graph
                buckets = [r.bucket for r in records]
                interval_consumptions = [r.consumption for r in records]
                indices = [r.end_value for r in records]

                cum_val = 0.0
                cumulative_consumptions = []
                for c in interval_consumptions:
                    cum_val += c
                    cumulative_consumptions.append(round(cum_val, 3))

                active_consumptions = (
                    cumulative_consumptions
                    if self.cumulative
                    else interval_consumptions
                )
                metric_label = (
                    "Cumulative Consumption" if self.cumulative else "Consumption"
                )
                y_axis_name = (
                    f"Cumulative ({unit})" if self.cumulative else f"Usage ({unit})"
                )

                single_y_axis = [
                    {
                        "type": "value",
                        "name": y_axis_name,
                        "nameTextStyle": {"color": "#9ca3af"},
                        "splitLine": {
                            "lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}
                        },
                        "axisLabel": {"color": "#9ca3af"},
                    }
                ]

                if self.chart_style == "line":
                    series = [
                        {
                            "name": metric_label,
                            "type": "line",
                            "smooth": True,
                            "symbol": "circle",
                            "symbolSize": 8,
                            "data": active_consumptions,
                            "itemStyle": {"color": "#38bdf8"},
                            "lineStyle": {"width": 3, "color": "#38bdf8"},
                        }
                    ]
                    legend_data = [metric_label]
                    y_axis = single_y_axis
                elif self.chart_style == "area":
                    series = [
                        {
                            "name": metric_label,
                            "type": "line",
                            "smooth": True,
                            "symbol": "circle",
                            "symbolSize": 6,
                            "data": active_consumptions,
                            "itemStyle": {"color": "#06b6d4"},
                            "lineStyle": {"width": 2.5, "color": "#06b6d4"},
                            "areaStyle": {
                                "color": {
                                    "type": "linear",
                                    "x": 0,
                                    "y": 0,
                                    "x2": 0,
                                    "y2": 1,
                                    "colorStops": [
                                        {
                                            "offset": 0,
                                            "color": "rgba(6, 182, 212, 0.45)",
                                        },
                                        {
                                            "offset": 1,
                                            "color": "rgba(59, 130, 246, 0.02)",
                                        },
                                    ],
                                }
                            },
                        }
                    ]
                    legend_data = [metric_label]
                    y_axis = single_y_axis
                elif self.chart_style == "combined":
                    if self.cumulative:
                        series = [
                            {
                                "name": "Interval Consumption",
                                "type": "bar",
                                "yAxisIndex": 0,
                                "data": interval_consumptions,
                                "itemStyle": {
                                    "borderRadius": [6, 6, 0, 0],
                                    "color": {
                                        "type": "linear",
                                        "x": 0,
                                        "y": 0,
                                        "x2": 0,
                                        "y2": 1,
                                        "colorStops": [
                                            {"offset": 0, "color": "#06b6d4"},
                                            {"offset": 1, "color": "#3b82f6"},
                                        ],
                                    },
                                },
                                "emphasis": {"itemStyle": {"color": "#38bdf8"}},
                            },
                            {
                                "name": "Cumulative Consumption",
                                "type": "line",
                                "yAxisIndex": 1,
                                "smooth": True,
                                "data": cumulative_consumptions,
                                "itemStyle": {"color": "#a855f7"},
                                "lineStyle": {"width": 3, "color": "#a855f7"},
                            },
                        ]
                        legend_data = [
                            "Interval Consumption",
                            "Cumulative Consumption",
                        ]
                        y_axis = [
                            {
                                "type": "value",
                                "name": f"Interval ({unit})",
                                "nameTextStyle": {"color": "#9ca3af"},
                                "splitLine": {
                                    "lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}
                                },
                                "axisLabel": {"color": "#9ca3af"},
                            },
                            {
                                "type": "value",
                                "name": f"Cumulative ({unit})",
                                "nameTextStyle": {"color": "#9ca3af"},
                                "splitLine": {"show": False},
                                "axisLabel": {"color": "#9ca3af"},
                            },
                        ]
                    else:
                        series = [
                            {
                                "name": "Consumption",
                                "type": "bar",
                                "yAxisIndex": 0,
                                "data": interval_consumptions,
                                "itemStyle": {
                                    "borderRadius": [6, 6, 0, 0],
                                    "color": {
                                        "type": "linear",
                                        "x": 0,
                                        "y": 0,
                                        "x2": 0,
                                        "y2": 1,
                                        "colorStops": [
                                            {"offset": 0, "color": "#06b6d4"},
                                            {"offset": 1, "color": "#3b82f6"},
                                        ],
                                    },
                                },
                                "emphasis": {"itemStyle": {"color": "#38bdf8"}},
                            },
                            {
                                "name": "Reading Index",
                                "type": "line",
                                "yAxisIndex": 1,
                                "smooth": True,
                                "data": indices,
                                "itemStyle": {"color": "#10b981"},
                                "lineStyle": {"width": 2, "color": "#10b981"},
                            },
                        ]
                        legend_data = ["Consumption", "Reading Index"]
                        y_axis = [
                            {
                                "type": "value",
                                "name": f"Usage ({unit})",
                                "nameTextStyle": {"color": "#9ca3af"},
                                "splitLine": {
                                    "lineStyle": {"color": "rgba(255, 255, 255, 0.06)"}
                                },
                                "axisLabel": {"color": "#9ca3af"},
                            },
                            {
                                "type": "value",
                                "name": f"Index ({unit})",
                                "nameTextStyle": {"color": "#9ca3af"},
                                "splitLine": {"show": False},
                                "axisLabel": {"color": "#9ca3af"},
                            },
                        ]
                else:  # "bar"
                    series = [
                        {
                            "name": metric_label,
                            "type": "bar",
                            "data": active_consumptions,
                            "itemStyle": {
                                "borderRadius": [6, 6, 0, 0],
                                "color": {
                                    "type": "linear",
                                    "x": 0,
                                    "y": 0,
                                    "x2": 0,
                                    "y2": 1,
                                    "colorStops": [
                                        {"offset": 0, "color": "#06b6d4"},
                                        {"offset": 1, "color": "#3b82f6"},
                                    ],
                                },
                            },
                            "emphasis": {"itemStyle": {"color": "#38bdf8"}},
                        }
                    ]
                    legend_data = [metric_label]
                    y_axis = single_y_axis

                echart_options = {
                    "backgroundColor": "transparent",
                    "tooltip": {
                        "trigger": "axis",
                        "axisPointer": {
                            "type": (
                                "line"
                                if self.chart_style in ("line", "area")
                                else "shadow"
                            )
                        },
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
                    "h-[400px]"
                ):
                    ui.echart(echart_options).classes("w-full h-full")

        # Top Bar
        with ui.row().classes("w-full justify-between items-center mb-2"):
            with ui.row().classes("items-center gap-3"):
                ui.label("Meter Dashboard").classes("text-h4")
                self.spinner = ui.spinner("dots", size="md", color="cyan")
                self.spinner.visible = False

            ui.button("Refresh", icon="refresh", on_click=do_fetch).props(
                "unelevated color=primary"
            ).classes("shadow-md shadow-blue-500/20")

        with (
            ui.tabs()
            .classes("w-full border-b border-white/10")
            .props("align=left active-color=cyan") as tabs
        ):
            values = ui.tab("Values", icon="speed")
            consumption = ui.tab("Consumption", icon="bar_chart")
            raw = ui.tab("Raw Data", icon="code")

        with ui.tab_panels(tabs, value=values).classes(
            "w-full h-full bg-transparent p-0 pt-4"
        ):
            with ui.tab_panel(values).classes("p-0"):
                value_container = ui.column().classes("w-full")
            with ui.tab_panel(consumption).classes("p-0"):
                consumption_container = ui.column().classes("w-full")
            with ui.tab_panel(raw).classes("p-0"):
                raw_container = ui.column().classes("w-full")

        await do_fetch()
