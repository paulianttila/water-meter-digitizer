"""Meter Dashboard Page for NiceGUI (Live Readouts, Cropped Dials, Analytics, and History Table)."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.components.consumption_card import ConsumptionCard
from gui.components.history_table_card import HistoryTableCard
from gui.components.time_machine_card import TimeMachineCard
from gui.theme import BADGE_ERROR, BADGE_SUCCESS, BADGE_WARNING

logger = logging.getLogger(__name__)


class MeterPage:
    """Page rendering live water meter deductions, multi-stage pipeline captures, digit crops, and analytics."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.consumption_card = ConsumptionCard(self.callbacks)
        self.history_card = HistoryTableCard(self.callbacks)
        self.time_machine_card = TimeMachineCard(self.callbacks)
        self.spinner: ui.spinner | None = None
        self.active_image_stage: str = "final"
        self.auto_refresh_seconds: int = 0
        self._auto_timer: ui.timer | None = None
        self.last_fetch_time: datetime | None = None
        self.last_pipeline_ms: float = 0.0
        self._fetch_task: asyncio.Task | None = None

    async def show(self) -> None:
        """Render the Meter Dashboard page."""
        freshness_container: ui.row | None = None
        freshness_ts_label: ui.label | None = None
        freshness_badge: ui.badge | None = None

        async def do_fetch() -> None:
            if self.spinner:
                self.spinner.visible = True
            value_container.clear()
            t0 = time.perf_counter()
            try:
                await fetch_data()
                self.last_fetch_time = datetime.now()
                self.last_pipeline_ms = (time.perf_counter() - t0) * 1000.0
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
            update_freshness_header()

        def update_freshness_header() -> None:
            if freshness_container and freshness_ts_label and freshness_badge:
                if self.last_fetch_time:
                    ts_str = self.last_fetch_time.strftime("%H:%M:%S")
                    freshness_ts_label.text = f"Updated: {ts_str}"
                    if self.last_pipeline_ms > 0:
                        freshness_badge.text = f"⚡ {self.last_pipeline_ms:.0f}ms"
                        freshness_badge.visible = True
                    else:
                        freshness_badge.visible = False
                    freshness_container.visible = True
                else:
                    freshness_container.visible = False

        def on_auto_refresh_change(e: Any) -> None:
            self.auto_refresh_seconds = int(e.value)
            if self._auto_timer:
                self._auto_timer.cancel()
                self._auto_timer = None
            if self.auto_refresh_seconds > 0:

                def trigger_periodic_fetch() -> None:
                    self._fetch_task = asyncio.create_task(do_fetch())

                self._auto_timer = ui.timer(
                    float(self.auto_refresh_seconds),
                    trigger_periodic_fetch,
                )
                ui.notify(
                    f"Auto-refresh set to {self.auto_refresh_seconds}s",
                    type="info",
                )

        def trigger_background_poll() -> None:
            try:
                self.callbacks.trigger_poller()
                ui.notify("Triggered background poller run", type="positive")
                self._fetch_task = asyncio.create_task(do_fetch())
            except Exception as err:
                ui.notify(f"Poller trigger failed: {err}", type="negative")

        def open_crop_modal(
            name: str, value: Any, conf: float, is_digital: bool
        ) -> None:
            crop_base64 = ""
            try:
                crop_base64 = self.callbacks.get_image_as_base64_str(name)
            except Exception:
                logger.debug("Failed to load crop image for %s", name, exc_info=True)
                crop_base64 = ""

            with (
                ui.dialog() as crop_modal,
                ui.card().classes(
                    "bg-slate-900 border border-white/10 rounded-2xl p-6 gap-4 min-w-[320px] max-w-md shadow-2xl text-white"
                ),
            ):
                with ui.row().classes(
                    "w-full justify-between items-center pb-2 border-b border-white/10"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("pin" if is_digital else "speed", color="cyan").classes(
                            "text-lg"
                        )
                        ui.label(
                            f"{'Digital Counter' if is_digital else 'Analog Dial'} - {name}"
                        ).classes("font-['Outfit'] font-bold text-sm text-gray-100")
                    ui.button(icon="close", on_click=crop_modal.close).props(
                        "flat round dense size=sm aria-label='Close dialog'"
                    )

                with ui.column().classes("w-full items-center gap-3"):
                    with ui.element("div").classes(
                        "w-48 h-48 rounded-2xl bg-black/60 p-2 border border-white/10 flex items-center justify-center overflow-hidden"
                    ):
                        if crop_base64:
                            ui.image(f"data:image/jpeg;base64,{crop_base64}").props(
                                "fit=contain no-spinner"
                            ).classes("max-w-full max-h-full rounded-xl")
                        else:
                            ui.icon("image_not_supported", color="gray").classes(
                                "text-4xl"
                            )

                    with ui.row().classes("items-baseline gap-2 mt-1"):
                        ui.label(str(value)).classes(
                            "font-['Outfit'] text-4xl font-extrabold text-cyan-300"
                        )
                        ui.label(f"#{name}").classes("text-xs font-mono text-slate-400")

                    conf_color = (
                        "text-emerald-400"
                        if conf >= 85.0
                        else ("text-amber-400" if conf >= 70.0 else "text-rose-400")
                    )
                    with ui.row().classes("items-center gap-1.5 text-xs font-mono"):
                        ui.label("Neural Confidence:").classes("text-slate-400")
                        ui.label(f"{conf:.1f}%").classes(f"font-bold {conf_color}")

                with ui.row().classes(
                    "w-full justify-end pt-2 border-t border-white/10"
                ):
                    ui.button("Close", on_click=crop_modal.close).props(
                        "unelevated color=primary size=sm"
                    ).classes("rounded-xl px-4")

            crop_modal.open()

        async def fetch_data() -> None:
            result = await asyncio.to_thread(
                self.callbacks.get_meter_data, saveimages=True
            )

            # Check leak / flow telemetry
            leak_status: dict[str, Any] = {}
            try:
                leak_status = self.callbacks.get_leak_status() or {}
            except Exception:
                logger.debug("Leak status unavailable", exc_info=True)
                leak_status = {}

            with value_container:
                # 0. Optional Recognition Error/Warning Banner
                if result.error:
                    with ui.element("div").classes(
                        "w-full p-3.5 rounded-2xl bg-amber-950/50 border border-amber-500/40 "
                        "text-amber-200 text-xs flex items-center justify-between gap-2 mb-3 shadow-lg"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("warning", color="amber").classes("text-lg")
                            ui.label(f"Recognition Warning: {result.error}").classes(
                                "font-semibold"
                            )
                        ui.button("Open Setup Wizard", icon="settings").props(
                            'unelevated size=xs color=amber text-color=dark href="/#setup"'
                        ).classes("rounded-lg font-bold")

                # 1. Metric Summary Cards & Flow Badges
                with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
                    for meter in result.meters:
                        is_total = meter.name == "total"
                        bg_grad = (
                            "bg-gradient-to-br from-blue-950/60 via-slate-900/80 to-cyan-950/40 "
                            "border-cyan-500/40 shadow-xl shadow-cyan-500/5"
                            if is_total
                            else "bg-slate-900/70 border-white/10 shadow-lg"
                        )
                        card_classes = f"p-4 rounded-2xl border flex-1 min-w-[220px] backdrop-blur-md {bg_grad}"
                        with ui.element("div").classes(card_classes):
                            with ui.row().classes(
                                "w-full justify-between items-center mb-1.5"
                            ):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.label(meter.name.upper()).classes(
                                        "text-xs font-bold text-gray-300 tracking-wider font-mono"
                                    )
                                    if is_total:
                                        ui.label("PRIMARY").classes(
                                            "text-[10px] font-bold text-cyan-400 bg-cyan-500/10 "
                                            "px-2 py-0.5 rounded-full border border-cyan-500/30"
                                        )

                                with ui.row().classes("items-center gap-1.5"):
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

                            with ui.row().classes(
                                "w-full justify-between items-baseline gap-2"
                            ):
                                with ui.row().classes("items-baseline gap-1.5"):
                                    text_grad = (
                                        "text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-cyan-300"
                                        if is_total
                                        else "text-white"
                                    )
                                    val_classes = f"font-['Outfit'] text-3xl font-extrabold tracking-tight {text_grad}"
                                    ui.label(str(meter.value)).classes(val_classes)
                                    if meter.unit:
                                        ui.label(meter.unit).classes(
                                            "text-sm text-gray-400 font-semibold"
                                        )

                                def copy_value(val: str = meter.value) -> None:
                                    ui.run_javascript(
                                        f"navigator.clipboard.writeText('{val}')"
                                    )
                                    ui.notify(
                                        f"Copied '{val}' to clipboard", type="info"
                                    )

                                ui.button(
                                    icon="content_copy", on_click=copy_value
                                ).props("flat round dense size=xs color=gray").tooltip(
                                    "Copy reading to clipboard"
                                )

                    # Flow & Leak Telemetry Card
                    is_flowing = leak_status.get("flow_active", False)
                    leak_state = leak_status.get("state", "OK")
                    flow_dur = leak_status.get("continuous_flow_seconds", 0)
                    with ui.element("div").classes(
                        "p-4 rounded-2xl border border-white/10 bg-slate-900/70 shadow-lg min-w-[200px] flex-1 backdrop-blur-md"
                    ):
                        with ui.row().classes(
                            "w-full justify-between items-center mb-1.5"
                        ):
                            ui.label("FLOW MONITOR").classes(
                                "text-xs font-bold text-gray-400 tracking-wider font-mono"
                            )
                            if leak_state in ("LEAK_ALERT", "SUSPECTED_LEAK"):
                                ui.badge(leak_state, color="negative").classes(
                                    "text-[10px] font-bold"
                                )
                            else:
                                ui.badge("NORMAL", color="emerald").classes(
                                    "text-[10px] font-bold"
                                )

                        with ui.row().classes("items-baseline gap-2"):
                            if is_flowing:
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.icon("water_drop", color="blue").classes(
                                        "text-2xl animate-bounce"
                                    )
                                    ui.label("Active Flow").classes(
                                        "font-['Outfit'] text-2xl font-bold text-blue-300"
                                    )
                            else:
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.icon("pause_circle", color="gray").classes(
                                        "text-2xl"
                                    )
                                    ui.label("Zero-Flow").classes(
                                        "font-['Outfit'] text-2xl font-bold text-slate-400"
                                    )

                        if flow_dur > 0:
                            ui.label(f"Continuous flow: {flow_dur}s").classes(
                                "text-[11px] text-blue-300/80 font-mono mt-0.5"
                            )

                # 2. Main Multi-Stage Image & Crop Grids
                def open_roi_dialog() -> None:
                    roi_img = ""
                    try:
                        roi_img = self.callbacks.get_image_as_base64_str("roi")
                    except Exception:
                        logger.debug(
                            "Failed to get 'roi' image, falling back to 'final'",
                            exc_info=True,
                        )
                        try:
                            roi_img = self.callbacks.get_image_as_base64_str("final")
                        except Exception:
                            logger.debug(
                                "Failed to get 'final' fallback image for ROI dialog",
                                exc_info=True,
                            )
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
                            "w-full max-w-4xl p-5 bg-slate-900 border border-white/10 rounded-2xl gap-4 shadow-2xl text-white"
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
                                "flat round dense text-xs aria-label='Close dialog'"
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
                    # Processed image with multi-stage switcher
                    with ui.column().classes("flex-1 min-w-[340px] gap-2"):
                        with ui.row().classes(
                            "w-full justify-between items-center gap-2 flex-wrap"
                        ):
                            with ui.row().classes("items-center gap-1.5"):
                                ui.icon("photo_camera", color="cyan").classes(
                                    "text-base"
                                )
                                ui.label("Processed Capture").classes(
                                    "font-['Outfit'] font-bold text-sm text-gray-200"
                                )

                            with ui.row().classes("items-center gap-1.5"):
                                ui.button(
                                    "Inspect ROIs",
                                    icon="crop_free",
                                    on_click=open_roi_dialog,
                                ).props("flat dense color=cyan size=sm").classes(
                                    "text-xs font-semibold"
                                )

                        # In-place stage switcher toggle
                        def on_stage_toggle(e: Any) -> None:
                            self.active_image_stage = e.value
                            render_stage_image()

                        def render_stage_image() -> None:
                            if stage_image_container:
                                stage_image_container.clear()
                                with stage_image_container:
                                    img_data = ""
                                    try:
                                        img_data = (
                                            self.callbacks.get_image_as_base64_str(
                                                self.active_image_stage
                                            )
                                        )
                                    except Exception:
                                        logger.debug(
                                            "Stage '%s' image not available, trying 'final'",
                                            self.active_image_stage,
                                            exc_info=True,
                                        )
                                        try:
                                            img_data = (
                                                self.callbacks.get_image_as_base64_str(
                                                    "final"
                                                )
                                            )
                                        except Exception:
                                            logger.debug(
                                                "Final fallback stage image not available",
                                                exc_info=True,
                                            )
                                            img_data = ""

                                    if img_data:
                                        ui.image(
                                            f"data:image/jpeg;base64,{img_data}"
                                        ).props("fit=contain no-spinner").classes(
                                            "w-full rounded-xl max-h-[460px]"
                                        )
                                    else:
                                        with ui.column().classes(
                                            "p-12 items-center justify-center gap-2"
                                        ):
                                            ui.icon(
                                                "image_not_supported", color="gray"
                                            ).classes("text-4xl")
                                            ui.label(
                                                f"Stage '{self.active_image_stage}' not available"
                                            ).classes("text-xs text-gray-400 font-mono")

                        with ui.row().classes(
                            "w-full justify-between items-center gap-2 flex-wrap"
                        ):
                            ui.toggle(
                                options={
                                    "final": "Final",
                                    "roi": "ROIs",
                                    "cropped": "Cropped",
                                    "aligned": "Aligned",
                                    "rotated": "Rotated",
                                    "original": "Original",
                                },
                                value=self.active_image_stage,
                                on_change=on_stage_toggle,
                            ).props(
                                "dense rounded unelevated toggle-color=cyan text-color=grey-4"
                            ).classes(
                                "text-xs font-medium bg-slate-950/80 p-0.5"
                            )

                        stage_image_container = ui.element("div").classes(
                            "w-full rounded-2xl bg-slate-950/80 p-2.5 border border-white/10 "
                            "flex items-center justify-center overflow-hidden shadow-xl"
                        )
                        render_stage_image()

                    # Deductions Breakdown (Interactive Zoom Cards)
                    with ui.column().classes("flex-1 min-w-[320px] gap-4"):
                        if result.digital_results:
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.icon("pin", color="cyan").classes("text-base")
                                    ui.label("Digital Counters").classes(
                                        "font-['Outfit'] font-bold text-sm text-gray-200"
                                    )
                                ui.label("Click to Zoom").classes(
                                    "text-[10px] text-slate-500 font-mono"
                                )

                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                for image, value in result.digital_results.items():
                                    c_score = (
                                        result.confidence_scores.get(image, 100.0)
                                        if result.confidence_scores
                                        else 100.0
                                    )
                                    c_col = (
                                        "text-emerald-400"
                                        if c_score >= 80
                                        else (
                                            "text-amber-400"
                                            if c_score >= 60
                                            else "text-rose-400"
                                        )
                                    )

                                    with (
                                        ui.element("div")
                                        .classes(
                                            "p-2.5 rounded-xl bg-slate-900/90 border border-white/10 "
                                            "flex flex-col items-center gap-1 min-w-[80px] shadow-lg "
                                            "cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/90 transition-all"
                                        )
                                        .on(
                                            "click",
                                            lambda _, im=image, val=value, sc=c_score: open_crop_modal(
                                                im, val, sc, True
                                            ),
                                        )
                                    ):
                                        ui.label(image).classes(
                                            "text-[10px] text-gray-400 uppercase tracking-wider font-mono"
                                        )
                                        base64img = ""
                                        try:
                                            base64img = (
                                                self.callbacks.get_image_as_base64_str(
                                                    image
                                                )
                                            )
                                        except Exception:
                                            logger.debug(
                                                "Crop image not available for digital readout %s",
                                                image,
                                                exc_info=True,
                                            )
                                            base64img = ""
                                        if base64img:
                                            ui.image(
                                                f"data:image/jpeg;base64,{base64img}"
                                            ).props("fit=contain no-spinner").classes(
                                                "w-16 h-16 rounded-lg bg-slate-950 p-0.5 border border-white/5"
                                            )
                                        ui.label(str(value)).classes(
                                            "font-['Outfit'] font-bold text-cyan-300 text-base"
                                        )
                                        ui.label(f"{c_score:.0f}% conf").classes(
                                            f"text-[10px] font-mono {c_col}"
                                        )

                        if result.analog_results:
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.icon("speed", color="amber").classes("text-base")
                                    ui.label("Analog Dials").classes(
                                        "font-['Outfit'] font-bold text-sm text-gray-200"
                                    )
                                ui.label("Click to Zoom").classes(
                                    "text-[10px] text-slate-500 font-mono"
                                )

                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                for image, value in result.analog_results.items():
                                    c_score = (
                                        result.confidence_scores.get(image, 100.0)
                                        if result.confidence_scores
                                        else 100.0
                                    )
                                    c_col = (
                                        "text-emerald-400"
                                        if c_score >= 80
                                        else (
                                            "text-amber-400"
                                            if c_score >= 60
                                            else "text-rose-400"
                                        )
                                    )

                                    with (
                                        ui.element("div")
                                        .classes(
                                            "p-2.5 rounded-xl bg-slate-900/90 border border-white/10 "
                                            "flex flex-col items-center gap-1 min-w-[80px] shadow-lg "
                                            "cursor-pointer hover:border-amber-500/50 hover:bg-slate-800/90 transition-all"
                                        )
                                        .on(
                                            "click",
                                            lambda _, im=image, val=value, sc=c_score: open_crop_modal(
                                                im, val, sc, False
                                            ),
                                        )
                                    ):
                                        ui.label(image).classes(
                                            "text-[10px] text-gray-400 uppercase tracking-wider font-mono"
                                        )
                                        base64img = ""
                                        try:
                                            base64img = (
                                                self.callbacks.get_image_as_base64_str(
                                                    image
                                                )
                                            )
                                        except Exception:
                                            logger.debug(
                                                "Crop image not available for analog dial %s",
                                                image,
                                                exc_info=True,
                                            )
                                            base64img = ""
                                        if base64img:
                                            ui.image(
                                                f"data:image/jpeg;base64,{base64img}"
                                            ).props("fit=contain no-spinner").classes(
                                                "w-16 h-16 rounded-lg bg-slate-950 p-0.5 border border-white/5"
                                            )
                                        ui.label(str(value)).classes(
                                            "font-['Outfit'] font-bold text-amber-300 text-base"
                                        )
                                        ui.label(f"{c_score:.0f}% conf").classes(
                                            f"text-[10px] font-mono {c_col}"
                                        )

        # Top Bar
        with ui.row().classes(
            "w-full justify-between items-center gap-4 flex-wrap mb-3"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.label("Meter Dashboard").classes("text-h4")
                self.spinner = ui.spinner("dots", size="md", color="cyan")
                self.spinner.visible = False

            with ui.row().classes(
                "items-center gap-1.5 text-xs font-mono"
            ) as freshness_container:
                freshness_container.visible = False
                ui.icon("fiber_manual_record", size="10px").classes(
                    "text-emerald-400 animate-pulse"
                )
                freshness_ts_label = ui.label("").classes("text-slate-300")
                freshness_badge = ui.badge("", color="dark").classes(
                    "text-[10px] font-mono border border-white/10 text-cyan-300"
                )
                freshness_badge.visible = False

            with ui.row().classes("items-center gap-2.5 flex-wrap"):
                ui.label("Auto:").classes("text-xs font-semibold text-gray-400")
                ui.select(
                    options={
                        0: "Manual Only",
                        5: "Every 5s",
                        10: "Every 10s",
                        30: "Every 30s",
                        60: "Every 60s",
                    },
                    value=self.auto_refresh_seconds,
                    on_change=on_auto_refresh_change,
                ).props("dense outlined options-dense").classes(
                    "w-32 text-xs bg-slate-950 rounded-lg"
                )

                def on_manual_refresh() -> None:
                    self._fetch_task = asyncio.create_task(do_fetch())

                ui.button(
                    "Refresh",
                    icon="refresh",
                    on_click=on_manual_refresh,
                ).props(
                    "unelevated color=primary size=sm"
                ).classes("shadow-md shadow-blue-500/20 rounded-xl")

                ui.button(
                    icon="bolt",
                    on_click=trigger_background_poll,
                ).props(
                    "flat round dense color=amber size=sm"
                ).tooltip("Trigger Poller Execution")

                ui.button(
                    icon="open_in_new",
                ).props(
                    'flat round dense color=cyan size=sm href="/meter" target="_blank"'
                ).tooltip("Open /meter REST API")

        with (
            ui.tabs()
            .classes("w-full border-b border-white/10")
            .props("align=left active-color=cyan") as tabs
        ):
            live_readout = ui.tab("Live Readout", icon="speed")
            time_machine = ui.tab("Time Machine", icon="history_toggle_off")
            consumption = ui.tab("Consumption", icon="bar_chart")
            readings_log = ui.tab("Readings Log", icon="table_view")

        with ui.tab_panels(tabs, value=live_readout).classes(
            "w-full h-full bg-transparent p-0 pt-4"
        ):
            with ui.tab_panel(live_readout).classes("p-0"):
                value_container = ui.column().classes("w-full")
            with ui.tab_panel(time_machine).classes("p-0"):
                tm_container = ui.column().classes("w-full")
                self.time_machine_card.render(tm_container)
            with ui.tab_panel(consumption).classes("p-0"):
                stats_container = ui.column().classes("w-full")
                self.consumption_card.render(stats_container)
            with ui.tab_panel(readings_log).classes("p-0"):
                history_container = ui.column().classes("w-full")
                self.history_card.render(history_container)

        await do_fetch()
