"""Meter Dashboard Page for NiceGUI (Live Readouts, Cropped Dials, Analytics, and History Table)."""

import asyncio

from nicegui import ui

from callbacks import Callbacks
from gui.components.consumption_card import ConsumptionCard
from gui.components.history_table_card import HistoryTableCard
from gui.components.time_machine_card import TimeMachineCard
from gui.theme import BADGE_ERROR, BADGE_SUCCESS, BADGE_WARNING


class MeterPage:
    """Page rendering live water meter deductions, processed captures, digit crops, statistics, and history table."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.consumption_card = ConsumptionCard(self.callbacks)
        self.history_card = HistoryTableCard(self.callbacks)
        self.time_machine_card = TimeMachineCard(self.callbacks)
        self.spinner: ui.spinner | None = None

    async def show(self) -> None:
        """Render the Meter Dashboard page."""

        async def do_fetch() -> None:
            if self.spinner:
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
            if self.spinner:
                self.spinner.visible = False

        async def fetch_data() -> None:
            result = await asyncio.to_thread(
                self.callbacks.get_meter_data, saveimages=True
            )

            with value_container:
                # 0. Optional Recognition Error/Warning Banner
                if result.error:
                    with ui.element("div").classes(
                        "w-full p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/30 "
                        "text-amber-200 text-xs flex items-center gap-2 mb-4"
                    ):
                        ui.icon("warning", color="amber").classes("text-lg")
                        ui.label(f"Recognition Status: {result.error}").classes(
                            "font-semibold"
                        )

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
                                with ui.row().classes("items-center gap-1.5"):
                                    if is_total:
                                        ui.label("PRIMARY").classes(
                                            "text-[10px] font-bold text-emerald-400 "
                                            "bg-emerald-500/10 px-2 py-0.5 rounded-full "
                                            "border border-emerald-500/30"
                                        )
                                    conf_val = getattr(meter, "confidence", 100.0)
                                    qual = getattr(meter, "quality", "good").lower()
                                    badge_cls = (
                                        BADGE_SUCCESS
                                        if qual == "good"
                                        else (
                                            BADGE_WARNING
                                            if qual == "warning"
                                            else BADGE_ERROR
                                        )
                                    )
                                    with ui.element("span").classes(badge_cls):
                                        ui.label(
                                            f"{conf_val:.1f}% • {qual.capitalize()}"
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
                def open_roi_dialog() -> None:
                    roi_img = ""
                    try:
                        roi_img = self.callbacks.get_image_as_base64_str("roi")
                    except Exception:
                        try:
                            roi_img = self.callbacks.get_image_as_base64_str("final")
                        except Exception:
                            roi_img = ""

                    cfg = self.callbacks.get_config()
                    n_refs = (
                        len(getattr(cfg.alignment, "ref_images", []))
                        if cfg and getattr(cfg, "alignment", None)
                        else 0
                    )
                    n_dig = (
                        len(getattr(cfg.digital_readout, "cut_images", []))
                        if cfg and getattr(cfg, "digital_readout", None)
                        else 0
                    )
                    n_ana = (
                        len(getattr(cfg.analog_readout, "cut_images", []))
                        if cfg and getattr(cfg, "analog_readout", None)
                        else 0
                    )

                    with (
                        ui.dialog() as roi_modal,
                        ui.card().classes(
                            "w-full max-w-4xl p-5 bg-slate-900 border border-white/10 rounded-2xl gap-4"
                        ),
                    ):
                        with ui.row().classes(
                            "w-full justify-between items-center pb-2 border-b border-white/10"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("crop_free", color="cyan").classes("text-xl")
                                with ui.column().classes("gap-0"):
                                    ui.label("ROI & Reference Marks Inspector").classes(
                                        "font-['Outfit'] font-bold text-base text-gray-100"
                                    )
                                    ui.label(
                                        "Visual alignment markers and digitization region bounding boxes"
                                    ).classes("text-xs text-gray-400")
                            ui.button(icon="close", on_click=roi_modal.close).props(
                                "flat round dense text-xs"
                            )

                        # Color-Coded Legend Row
                        with ui.row().classes(
                            "w-full items-center justify-between gap-3 text-xs flex-wrap p-2 rounded-xl bg-slate-950/60 border border-white/5"
                        ):
                            with ui.row().classes("items-center gap-4 flex-wrap"):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.element("span").classes(
                                        "w-3 h-3 rounded bg-emerald-500 shadow-sm shadow-emerald-500/50"
                                    )
                                    ui.label("Alignment References").classes(
                                        "font-medium text-emerald-300"
                                    )
                                    ui.label(f"({n_refs})").classes(
                                        "text-xs text-gray-400 font-mono"
                                    )
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.element("span").classes(
                                        "w-3 h-3 rounded bg-blue-500 shadow-sm shadow-blue-500/50"
                                    )
                                    ui.label("Digital Counters").classes(
                                        "font-medium text-blue-300"
                                    )
                                    ui.label(f"({n_dig})").classes(
                                        "text-xs text-gray-400 font-mono"
                                    )
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.element("span").classes(
                                        "w-3 h-3 rounded bg-amber-500 shadow-sm shadow-amber-500/50"
                                    )
                                    ui.label("Analog Dials").classes(
                                        "font-medium text-amber-300"
                                    )
                                    ui.label(f"({n_ana})").classes(
                                        "text-xs text-gray-400 font-mono"
                                    )

                            ui.label("Thickness: 2px | Pill Badges").classes(
                                "text-[11px] text-gray-400 font-mono"
                            )

                        # Image Container
                        with ui.element("div").classes(
                            "w-full rounded-xl bg-slate-950 p-2 border border-white/10 flex items-center justify-center overflow-hidden max-h-[70vh]"
                        ):
                            if roi_img:
                                ui.image(f"data:image/jpeg;base64,{roi_img}").classes(
                                    "max-h-[65vh] object-contain rounded-lg"
                                )
                            else:
                                ui.label("No ROI overlay image available").classes(
                                    "text-xs text-gray-400 p-4"
                                )

                        with ui.row().classes(
                            "w-full justify-between items-center pt-2 border-t border-white/10"
                        ):
                            ui.button("Open Raw /roi", icon="open_in_new").props(
                                'flat dense color=cyan text-xs href="/roi" target="_blank"'
                            )
                            ui.button("Close", on_click=roi_modal.close).props(
                                "flat dense color=primary text-xs"
                            )

                    roi_modal.open()

                with ui.row().classes("w-full gap-6 items-start"):
                    # Processed image
                    with ui.column().classes("flex-1 min-w-[320px]"):
                        with ui.row().classes(
                            "w-full justify-between items-center mb-2"
                        ):
                            ui.label("Processed Capture").classes(
                                "font-['Outfit'] font-bold text-sm text-gray-300"
                            )
                            ui.button(
                                "Inspect ROIs",
                                icon="crop_free",
                                on_click=open_roi_dialog,
                            ).props("flat dense color=cyan size=sm").classes(
                                "text-xs font-semibold"
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
                                for (
                                    image,
                                    value,
                                ) in result.digital_results.items():
                                    with ui.element("div").classes(
                                        "p-2.5 rounded-lg bg-slate-900/80 border "
                                        "border-white/10 flex flex-col items-center "
                                        "gap-1 min-w-[75px]"
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
                                        if (
                                            result.confidence_scores
                                            and image in result.confidence_scores
                                        ):
                                            c_score = result.confidence_scores[image]
                                            c_col = (
                                                "text-emerald-400"
                                                if c_score >= 80
                                                else (
                                                    "text-amber-400"
                                                    if c_score >= 60
                                                    else "text-rose-400"
                                                )
                                            )
                                            ui.label(f"{c_score:.0f}% conf").classes(
                                                f"text-[10px] font-mono {c_col}"
                                            )

                        if result.analog_results:
                            ui.label("Analog Dials").classes(
                                "font-['Outfit'] font-bold text-sm text-gray-300"
                            )
                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                for (
                                    image,
                                    value,
                                ) in result.analog_results.items():
                                    with ui.element("div").classes(
                                        "p-2.5 rounded-lg bg-slate-900/80 border "
                                        "border-white/10 flex flex-col items-center "
                                        "gap-1 min-w-[75px]"
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
                                        if (
                                            result.confidence_scores
                                            and image in result.confidence_scores
                                        ):
                                            c_score = result.confidence_scores[image]
                                            c_col = (
                                                "text-emerald-400"
                                                if c_score >= 80
                                                else (
                                                    "text-amber-400"
                                                    if c_score >= 60
                                                    else "text-rose-400"
                                                )
                                            )
                                            ui.label(f"{c_score:.0f}% conf").classes(
                                                f"text-[10px] font-mono {c_col}"
                                            )

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
            time_machine = ui.tab("Time Machine", icon="history_toggle_off")
            statistics = ui.tab("Statistics", icon="bar_chart")
            history = ui.tab("History", icon="table_view")

        with ui.tab_panels(tabs, value=values).classes(
            "w-full h-full bg-transparent p-0 pt-4"
        ):
            with ui.tab_panel(values).classes("p-0"):
                value_container = ui.column().classes("w-full")
            with ui.tab_panel(time_machine).classes("p-0"):
                tm_container = ui.column().classes("w-full")
                self.time_machine_card.render(tm_container)
            with ui.tab_panel(statistics).classes("p-0"):
                stats_container = ui.column().classes("w-full")
                self.consumption_card.render(stats_container)
            with ui.tab_panel(history).classes("p-0"):
                history_container = ui.column().classes("w-full")
                self.history_card.render(history_container)

        await do_fetch()
