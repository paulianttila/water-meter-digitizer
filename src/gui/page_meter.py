import asyncio
import dataclasses
import json

from nicegui import ui

from callbacks import Callbacks


class MeterPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks

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

        # Top Bar
        with ui.row().classes("w-full justify-between items-center mb-2"):
            with ui.row().classes("items-center gap-3"):
                ui.label("Meter Values").classes("text-h4")
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
            raw = ui.tab("Raw Data", icon="code")

        with ui.tab_panels(tabs, value=values).classes(
            "w-full h-full bg-transparent p-0 pt-4"
        ):
            with ui.tab_panel(values).classes("p-0"):
                value_container = ui.column().classes("w-full")
            with ui.tab_panel(raw).classes("p-0"):
                raw_container = ui.column().classes("w-full")

        await do_fetch()
