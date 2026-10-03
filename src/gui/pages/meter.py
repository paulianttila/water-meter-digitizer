"""Meter Dashboard Page for NiceGUI (Live Readouts, Cropped Dials, Analytics, and History Table)."""

import asyncio
import base64
import contextlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import ui

import utils.image as ImageUtils
from callbacks import Callbacks
from gui.components import (
    ConsumptionCard,
    HistoryTableCard,
    TimeMachineCard,
    async_fetch_and_render,
    card_header,
    page_header,
)
from gui.pages.base import BasePage
from gui.theme import (
    BADGE_ERROR,
    BADGE_FILLED,
    BADGE_SUCCESS,
    BADGE_WARNING,
    BANNER_WARNING,
    CARD_DIGIT_CROP,
    CARD_HERO_SUBMETER,
    CARD_HERO_TOTAL,
    CARD_TELEMETRY,
    CLICKABLE_CARD,
    DIALOG_CARD,
    DIALOG_FOOTER_ROW,
    DIALOG_HEADER_ROW,
    FONT_MONO_VALUE,
    HEADING_SECTION,
    HEADING_SUBSECTION,
    HEX_ROI_ANALOG,
    HEX_ROI_DIGITAL,
    HEX_ROI_REFS,
    PANEL_STAGE_IMAGE,
    ROW_HEADER,
    ROW_ITEMS_CENTER,
    STAT_VALUE_LARGE,
    TABS_BAR_HORIZONTAL,
    TABS_PROPS_HORIZONTAL,
    TEXT_MONO_MUTED,
    copy_to_clipboard,
)

logger = logging.getLogger(__name__)


class MeterPage(BasePage):
    """Page rendering live water meter deductions, multi-stage pipeline captures, digit crops, and analytics."""

    def __init__(self, callbacks: Callbacks) -> None:
        super().__init__(callbacks)
        self.consumption_card = ConsumptionCard(self.callbacks)
        self.history_card = HistoryTableCard(self.callbacks)
        self.time_machine_card = TimeMachineCard(self.callbacks)
        self.spinner: ui.spinner | None = None
        self.refresh_btn: ui.button | None = None
        self.active_image_stage: str = "final"
        self.auto_refresh_seconds: int = 0
        self._auto_timer: ui.timer | None = None
        self.last_fetch_time: datetime | None = None
        self.last_pipeline_ms: float = 0.0
        self._fetch_task: asyncio.Task | None = None
        self._is_fetching: bool = False
        self._rendered_tabs: set[str] = set()

    def dispose(self) -> None:
        """Dispose page, timers, tasks, and child components."""
        super().dispose()
        if self._auto_timer is not None:
            with contextlib.suppress(Exception):
                self._auto_timer.cancel()
            self._auto_timer = None
        if self._fetch_task is not None and not self._fetch_task.done():
            self._fetch_task.cancel()
            self._fetch_task = None
        self.consumption_card.dispose()
        self.history_card.dispose()
        self.time_machine_card.dispose()
        self._rendered_tabs.clear()

    async def show(self) -> None:
        """Render the Meter Dashboard page."""
        freshness_container: ui.row | None = None
        freshness_ts_label: ui.label | None = None
        freshness_badge: ui.badge | None = None

        async def do_fetch() -> None:
            if self._is_fetching:
                return
            self._is_fetching = True
            if self.refresh_btn is not None:
                with contextlib.suppress(Exception):
                    self.refresh_btn.props("loading")
            try:
                t0 = time.perf_counter()
                data = await async_fetch_and_render(
                    fetch_fn=lambda: self.callbacks.get_meter_data(saveimages=True),
                    render_fn=render_meter_data,
                    container=value_container,
                    spinner=self.spinner,
                    error_message="Error occurred",
                    suppress_errors=True,
                )
                if data is not None:
                    self.last_fetch_time = datetime.now()
                    self.last_pipeline_ms = (time.perf_counter() - t0) * 1000.0
                update_freshness_header()
            finally:
                self._is_fetching = False
                if self.refresh_btn is not None:
                    with contextlib.suppress(Exception):
                        self.refresh_btn.props(remove="loading")

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

            model_type = "digital" if is_digital else "analog"
            active_cfg = self.callbacks.get_config()
            current_model_file = ""
            if active_cfg:
                current_model_file = (
                    getattr(active_cfg.digital_readout, "model_file", "")
                    if is_digital
                    else getattr(active_cfg.analog_readout, "model_file", "")
                )

            candidate_models = []
            try:
                candidate_models = self.callbacks.list_cnn_models(model_type)
            except Exception:
                logger.debug(
                    "Failed to list CNN models for %s", model_type, exc_info=True
                )

            with (
                ui.dialog() as crop_modal,
                ui.card().classes(
                    f"{DIALOG_CARD} min-w-[340px] max-w-xl max-h-[90vh] overflow-y-auto p-5"
                ),
            ):
                with card_header(
                    title=f"{'Digital Counter' if is_digital else 'Analog Dial'} - {name}",
                    icon="pin" if is_digital else "speed",
                    color="cyan",
                    classes=DIALOG_HEADER_ROW,
                    title_classes=f"{HEADING_SECTION} text-sm",
                ):
                    ui.button(icon="close", on_click=crop_modal.close).props(
                        "flat round dense size=sm aria-label='Close dialog'"
                    )

                # Upper preview section: ROI image and current readout info
                with ui.row().classes(
                    "w-full items-center gap-4 bg-slate-950/60 p-3 rounded-xl border border-white/5"
                ):
                    with ui.element("div").classes(
                        "w-24 h-24 sm:w-28 sm:h-28 rounded-xl bg-black/70 p-1.5 border border-white/10 flex items-center justify-center overflow-hidden shrink-0"
                    ):
                        if crop_base64:
                            ui.image(f"data:image/jpeg;base64,{crop_base64}").props(
                                "fit=contain no-spinner"
                            ).classes("max-w-full max-h-full rounded-lg")
                        else:
                            ui.icon("image_not_supported", color="gray").classes(
                                "text-3xl"
                            )

                    with ui.column().classes("flex-1 min-w-0 gap-1"):
                        with ui.row().classes("items-baseline gap-2"):
                            ui.label("Current Readout:").classes(
                                "text-xs text-slate-400 font-mono"
                            )
                            ui.label(str(value)).classes(
                                "font-['Outfit'] text-2xl font-bold text-cyan-300"
                            )
                            ui.label(f"#{name}").classes(
                                "text-[11px] font-mono text-slate-500"
                            )

                        conf_color = (
                            "text-emerald-400"
                            if conf >= 85.0
                            else ("text-amber-400" if conf >= 70.0 else "text-rose-400")
                        )
                        with ui.row().classes(f"{ROW_ITEMS_CENTER} text-xs font-mono"):
                            ui.label("Confidence:").classes("text-slate-400")
                            ui.label(f"{conf:.1f}%").classes(f"font-bold {conf_color}")

                        active_name = (
                            Path(current_model_file).name
                            if current_model_file
                            else "None"
                        )
                        with ui.row().classes(
                            f"{ROW_ITEMS_CENTER} text-xs font-mono text-slate-400 truncate"
                        ):
                            ui.label("Active Model:").classes("text-slate-500")
                            ui.label(active_name).classes(
                                "text-cyan-400/80 truncate text-[11px]"
                            ).tooltip(current_model_file)

                # Middle section: Single Model Tester & Apply to Config
                with ui.column().classes("w-full gap-2 mt-2"):
                    with ui.row().classes(f"{ROW_HEADER} items-center"):
                        with ui.row().classes(ROW_ITEMS_CENTER):
                            ui.icon("science", color="cyan").classes("text-base")
                            ui.label("Model Tester").classes(
                                f"{HEADING_SUBSECTION} text-xs text-slate-300"
                            )
                        if candidate_models:
                            ui.label(f"{len(candidate_models)} models found").classes(
                                f"{TEXT_MONO_MUTED} text-[10px]"
                            )

                    model_options = {m["file"]: m["name"] for m in candidate_models}
                    selected_model_file = (
                        current_model_file
                        if current_model_file in model_options
                        else (next(iter(model_options.keys())) if model_options else "")
                    )

                    model_select = (
                        ui.select(
                            options=model_options,
                            value=selected_model_file,
                            label="Select CNN Model to Test",
                        )
                        .props("dense outlined options-dense dark")
                        .classes("w-full text-xs font-mono")
                    )
                    model_select.value = selected_model_file

                    test_result_container = ui.column().classes(
                        "w-full p-3 rounded-xl bg-slate-950/80 border border-white/10 gap-2 min-h-[60px] justify-center"
                    )

                    def update_test_result(chosen_model: str | None = None) -> None:
                        target_model = (
                            chosen_model
                            if chosen_model is not None
                            else model_select.value
                        )
                        test_result_container.clear()
                        with test_result_container:
                            if not target_model:
                                ui.label("Select a model above to evaluate").classes(
                                    "text-xs text-slate-400 font-mono italic"
                                )
                                return
                            if not crop_base64:
                                ui.label("No crop image available to evaluate").classes(
                                    "text-xs text-slate-400 font-mono italic"
                                )
                                return
                            res = self.callbacks.evaluate_crop_model(
                                crop_base64, target_model, is_digital
                            )
                            if res.get("error"):
                                with ui.row().classes(
                                    "items-center gap-2 text-rose-400 text-xs font-mono"
                                ):
                                    ui.icon("error_outline", color="rose").classes(
                                        "text-sm"
                                    )
                                    ui.label(f"Error: {res['error']}")
                                return

                            pred_val = res.get("value")
                            res_conf = float(res.get("confidence", 0.0))
                            latency = float(res.get("latency_ms", 0.0))
                            res_badge = (
                                BADGE_SUCCESS
                                if res_conf >= 85.0
                                else (
                                    BADGE_WARNING if res_conf >= 70.0 else BADGE_ERROR
                                )
                            )

                            with ui.row().classes(
                                f"{ROW_HEADER} items-center flex-wrap gap-2"
                            ):
                                with ui.row().classes("items-center gap-3"):
                                    with ui.column().classes("gap-0"):
                                        ui.label("Prediction").classes(
                                            "text-[10px] text-slate-400 uppercase font-mono"
                                        )
                                        ui.label(
                                            str(
                                                pred_val
                                                if pred_val is not None
                                                else "-"
                                            )
                                        ).classes(
                                            "font-['Outfit'] text-2xl font-bold text-cyan-300"
                                        )
                                    with ui.column().classes("gap-0.5"):
                                        ui.label("Confidence").classes(
                                            "text-[10px] text-slate-400 uppercase font-mono"
                                        )
                                        ui.label(f"{res_conf:.1f}%").classes(
                                            f"{res_badge} text-xs font-bold"
                                        )
                                    with ui.column().classes("gap-0.5"):
                                        ui.label("Latency").classes(
                                            "text-[10px] text-slate-400 uppercase font-mono"
                                        )
                                        ui.label(f"⚡ {latency:.1f}ms").classes(
                                            "text-xs font-mono text-slate-300 font-bold"
                                        )

                                def apply_current() -> None:
                                    try:
                                        self.callbacks.apply_model_to_config(
                                            target_model, is_digital
                                        )
                                        ui.notify(
                                            f"Applied {Path(target_model).name} to config",
                                            type="positive",
                                        )
                                    except Exception as ex:
                                        ui.notify(
                                            f"Failed to apply model: {ex}",
                                            type="negative",
                                        )

                                ui.button(
                                    "Apply to Config",
                                    icon="save_as",
                                    on_click=apply_current,
                                ).props("unelevated color=primary size=sm").classes(
                                    "rounded-xl px-3 font-semibold text-xs ml-auto"
                                )

                    model_select.on_value_change(
                        lambda e: update_test_result(getattr(e, "value", None))
                    )
                    if selected_model_file and crop_base64:
                        update_test_result()

                # Expandable Leaderboard / Benchmark All Models
                with ui.expansion("Benchmark All Models", icon="leaderboard").classes(
                    "w-full bg-slate-950/40 border border-white/10 rounded-xl overflow-hidden mt-1 text-xs p-2.5 gap-2"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Compare all candidate models on this crop").classes(
                            "text-[11px] text-slate-400 font-mono"
                        )
                        ui.button(
                            "Run Benchmark",
                            icon="play_arrow",
                            on_click=lambda: run_benchmark(),
                        ).props("unelevated dense color=cyan size=xs").classes(
                            "rounded-lg px-2"
                        )

                    bench_container = ui.column().classes("w-full gap-1")

                    async def run_benchmark() -> None:
                        if not crop_base64:
                            ui.notify(
                                "No crop image available for benchmarking",
                                type="warning",
                            )
                            return
                        bench_container.clear()
                        with (
                            bench_container,
                            ui.row().classes(
                                "w-full justify-center items-center py-4 gap-2"
                            ),
                        ):
                            ui.spinner("dots", size="sm", color="cyan")
                            ui.label("Benchmarking candidate models...").classes(
                                "text-xs text-slate-400 font-mono"
                            )

                        benchmark_results = await asyncio.to_thread(
                            self.callbacks.benchmark_crop_models,
                            crop_base64,
                            is_digital,
                        )
                        bench_container.clear()
                        if not benchmark_results:
                            with bench_container:
                                ui.label(
                                    "No models found or benchmark returned empty results."
                                ).classes("text-xs text-slate-500 font-mono italic p-2")
                            return

                        with bench_container:
                            for idx, item in enumerate(benchmark_results, start=1):
                                with ui.row().classes(
                                    "w-full items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-white/5 hover:border-white/20 transition-all text-xs"
                                ):
                                    with ui.column().classes("gap-0.5 min-w-0 flex-1"):
                                        with ui.row().classes(
                                            "items-center gap-1.5 flex-wrap"
                                        ):
                                            ui.label(f"#{idx}").classes(
                                                "font-mono text-cyan-400 font-bold text-[11px]"
                                            )
                                            ui.label(item["name"]).classes(
                                                "font-mono font-semibold text-gray-200 text-xs truncate max-w-[200px]"
                                            ).tooltip(item["file"])
                                            if item.get("quantized"):
                                                ui.label("INT8").classes(
                                                    "bg-cyan-950/80 text-cyan-300 text-[10px] px-1 py-0.2 rounded border border-cyan-500/30 font-mono"
                                                )
                                        with ui.row().classes(
                                            "items-center gap-2 text-[10px] text-slate-400 font-mono"
                                        ):
                                            ui.label(
                                                f"⚡ {item.get('latency_ms', 0):.1f}ms"
                                            )
                                            if item.get("size_kb"):
                                                ui.label(f"💾 {item['size_kb']} KB")

                                    with ui.row().classes(
                                        "items-center gap-2 shrink-0"
                                    ):
                                        if item.get("error"):
                                            ui.label("ERR").classes(
                                                "text-rose-400 font-mono text-xs font-bold"
                                            ).tooltip(str(item["error"]))
                                        else:
                                            b_val = item.get("value")
                                            ui.label(
                                                str(b_val if b_val is not None else "-")
                                            ).classes(
                                                "font-mono text-sm font-bold text-cyan-300 min-w-[28px] text-right"
                                            )
                                            b_conf = float(item.get("confidence", 0.0))
                                            b_badge = (
                                                BADGE_SUCCESS
                                                if b_conf >= 85.0
                                                else (
                                                    BADGE_WARNING
                                                    if b_conf >= 70.0
                                                    else BADGE_ERROR
                                                )
                                            )
                                            ui.label(f"{b_conf:.1f}%").classes(
                                                f"{b_badge} text-[10px] px-1.5 py-0.5 font-mono"
                                            )

                                        def make_apply(m_file: str, m_name: str):
                                            def _do_apply() -> None:
                                                try:
                                                    self.callbacks.apply_model_to_config(
                                                        m_file, is_digital
                                                    )
                                                    ui.notify(
                                                        f"Applied model {m_name} to config",
                                                        type="positive",
                                                    )
                                                except Exception as ex:
                                                    ui.notify(
                                                        f"Failed to apply model: {ex}",
                                                        type="negative",
                                                    )

                                            return _do_apply

                                        ui.button(
                                            "Apply",
                                            icon="check",
                                            on_click=make_apply(
                                                item["file"],
                                                item["filename"],
                                            ),
                                        ).props(
                                            "flat dense color=cyan size=xs"
                                        ).classes(
                                            "text-xs font-semibold rounded-lg"
                                        )

                with ui.row().classes(f"{DIALOG_FOOTER_ROW}"):
                    ui.button("Close", on_click=crop_modal.close).props(
                        "unelevated color=primary size=sm"
                    ).classes("rounded-xl px-4")

            crop_modal.open()

        def render_meter_data(result: Any) -> None:
            # Check leak / flow telemetry
            leak_status: dict[str, Any] = {}
            try:
                raw_leak = self.callbacks.get_leak_status()
                if hasattr(raw_leak, "to_dict"):
                    leak_status = raw_leak.to_dict()
                elif hasattr(raw_leak, "model_dump"):
                    leak_status = raw_leak.model_dump()
                elif isinstance(raw_leak, dict):
                    leak_status = raw_leak
            except Exception:
                logger.debug("Leak status unavailable", exc_info=True)
                leak_status = {}

            with value_container:
                # 0. Optional Recognition Error/Warning Banner
                if result.error:
                    with ui.element("div").classes(BANNER_WARNING):
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
                        card_classes = (
                            CARD_HERO_TOTAL if is_total else CARD_HERO_SUBMETER
                        )
                        with ui.element("div").classes(card_classes):
                            with ui.row().classes(f"{ROW_HEADER} mb-1.5"):
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.label(meter.name.upper()).classes(
                                        "text-xs font-bold text-gray-300 tracking-wider font-mono"
                                    )
                                    if is_total:
                                        ui.label("PRIMARY").classes(
                                            "text-[10px] font-bold text-cyan-400 bg-cyan-500/10 "
                                            "px-2 py-0.5 rounded-full border border-cyan-500/30"
                                        )

                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    conf_val = (
                                        getattr(meter, "confidence", 100.0) or 100.0
                                    )
                                    min_conf_val = getattr(
                                        meter, "min_confidence", None
                                    )
                                    if min_conf_val is None:
                                        min_conf_val = conf_val
                                    filled_cnt = getattr(meter, "filled_digits", 0) or 0
                                    qual = getattr(meter, "quality", "good").lower()
                                    warn_msg = getattr(meter, "warning", "")
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
                                            f"{min_conf_val:.1f}% • {qual.capitalize()}"
                                        )
                                        tooltip_parts = [
                                            f"Min: {min_conf_val:.1f}%",
                                            f"Avg: {conf_val:.1f}%",
                                        ]
                                        if filled_cnt > 0:
                                            tooltip_parts.append(
                                                f"{filled_cnt} digit{'s' if filled_cnt > 1 else ''} filled from previous reading"
                                            )
                                        if warn_msg:
                                            tooltip_parts.append(warn_msg)
                                        ui.tooltip(" • ".join(tooltip_parts))

                                    if filled_cnt > 0:
                                        with ui.element("span").classes(BADGE_FILLED):
                                            ui.label(f"🔁 {filled_cnt} filled")
                                            ui.tooltip(
                                                f"{filled_cnt} low-confidence digit{'s' if filled_cnt > 1 else ''} filled from previous reading"
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
                                    val_classes = f"{STAT_VALUE_LARGE} {text_grad}"
                                    ui.label(str(meter.value)).classes(val_classes)
                                    if meter.unit:
                                        ui.label(meter.unit).classes(
                                            "text-sm text-gray-400 font-semibold"
                                        )

                                def copy_value(val: str = meter.value) -> None:
                                    copy_to_clipboard(
                                        val, f"Copied '{val}' to clipboard"
                                    )

                                ui.button(
                                    icon="content_copy", on_click=copy_value
                                ).props(
                                    "flat round dense size=xs color=gray aria-label='Copy reading to clipboard'"
                                ).tooltip(
                                    "Copy reading to clipboard"
                                )

                            if getattr(meter, "warning", ""):
                                with ui.row().classes(
                                    "items-center gap-1 mt-1 text-amber-400 text-xs font-medium"
                                ):
                                    ui.icon("warning", size="xs")
                                    ui.label(meter.warning)

                    # Flow & Leak Telemetry Card
                    leak_enabled = bool(leak_status.get("enabled", True))
                    is_flowing = bool(leak_status.get("flow_active", False))
                    leak_state = str(leak_status.get("state", "OK"))
                    flow_dur = float(
                        leak_status.get("continuous_flow_seconds")
                        or leak_status.get("current_flow_duration_seconds", 0.0)
                        or 0.0
                    )
                    with ui.element("div").classes(CARD_TELEMETRY):
                        with ui.row().classes(f"{ROW_HEADER} mb-1.5"):
                            ui.label("FLOW MONITOR").classes(
                                "text-xs font-bold text-gray-400 tracking-wider font-mono"
                            )
                            if not leak_enabled:
                                ui.badge("DISABLED", color="grey").classes(
                                    "text-[10px] font-bold"
                                )
                            elif leak_state == "LEAK_DETECTED" or "LEAK" in leak_state:
                                ui.badge("LEAK DETECTED", color="negative").classes(
                                    "text-[10px] font-bold"
                                )
                            elif is_flowing:
                                ui.badge("FLOW ACTIVE", color="amber").classes(
                                    "text-[10px] font-bold"
                                )
                            else:
                                ui.badge("NORMAL", color="emerald").classes(
                                    "text-[10px] font-bold"
                                )

                        with ui.row().classes("items-baseline gap-2"):
                            if not leak_enabled:
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.icon("do_not_disturb_on", color="gray").classes(
                                        "text-2xl"
                                    )
                                    ui.label("Inactive").classes(
                                        f"{FONT_MONO_VALUE} text-slate-500"
                                    )
                            elif is_flowing:
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.icon("water_drop", color="blue").classes(
                                        "text-2xl animate-bounce"
                                    )
                                    ui.label("Active Flow").classes(
                                        f"{FONT_MONO_VALUE} text-blue-300"
                                    )
                            else:
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.icon("pause_circle", color="gray").classes(
                                        "text-2xl"
                                    )
                                    ui.label("Zero-Flow").classes(
                                        f"{FONT_MONO_VALUE} text-slate-400"
                                    )

                        if not leak_enabled:
                            ui.label("Leak monitor service disabled").classes(
                                "text-[11px] text-slate-500 font-mono mt-0.5"
                            )
                        elif flow_dur > 0:
                            ui.label(f"Continuous flow: {flow_dur:.0f}s").classes(
                                "text-[11px] text-blue-300/80 font-mono mt-0.5"
                            )

                # 2. Main Multi-Stage Image & Crop Grids
                def open_roi_dialog() -> None:
                    clean_img_b64 = ""
                    for stage in ("final", "aligned", "processed", "original"):
                        with contextlib.suppress(Exception):
                            clean_img_b64 = self.callbacks.get_image_as_base64_str(
                                stage
                            )
                        if clean_img_b64:
                            break

                    if not clean_img_b64:
                        try:
                            clean_img_b64 = self.callbacks.get_image_as_base64_str(
                                "roi"
                            )
                        except Exception:
                            logger.debug(
                                "Failed to get fallback image for ROI dialog",
                                exc_info=True,
                            )
                            clean_img_b64 = ""

                    cfg = self.callbacks.get_config()
                    ref_pos = (
                        getattr(cfg.alignment, "ref_images", [])
                        if cfg and getattr(cfg, "alignment", None)
                        else []
                    )
                    dig_pos = (
                        getattr(cfg.digital_readout, "cut_images", [])
                        if cfg and getattr(cfg, "digital_readout", None)
                        else []
                    )
                    ana_pos = (
                        getattr(cfg.analog_readout, "cut_images", [])
                        if cfg and getattr(cfg, "analog_readout", None)
                        else []
                    )

                    cam_w = 640
                    cam_h = 480
                    if clean_img_b64:
                        try:
                            pil_img = ImageUtils.convert_base64_str_to_image(
                                clean_img_b64
                            )
                            cam_w, cam_h = ImageUtils.image_size(pil_img)
                        except Exception:
                            if cfg and getattr(cfg, "alignment", None):
                                cam_w = (
                                    getattr(cfg.alignment, "target_width", 640) or 640
                                )
                                cam_h = (
                                    getattr(cfg.alignment, "target_height", 480) or 480
                                )

                    hidden_rois: set[str] = set()

                    def build_svg_content() -> str:
                        svg_parts = [
                            f'<svg width="{cam_w}" height="{cam_h}" viewBox="0 0 {cam_w} {cam_h}" '
                            'xmlns="http://www.w3.org/2000/svg" style="display:block;user-select:none;">',
                            '<rect width="100%" height="100%" fill="#020617"/>',
                        ]
                        if clean_img_b64:
                            svg_parts.append(
                                f'<image href="data:image/jpeg;base64,{clean_img_b64}" '
                                f'x="0" y="0" width="{cam_w}" height="{cam_h}" '
                                'preserveAspectRatio="none" style="pointer-events:none;"/>'
                            )
                        else:
                            svg_parts.append(
                                f'<text x="{cam_w/2}" y="{cam_h/2}" fill="#64748b" text-anchor="middle" '
                                'font-family="monospace" font-size="14">No capture image available</text>'
                            )

                        svg_parts.append('<g opacity="0.9">')

                        # Draw reference markers
                        for r in ref_pos:
                            if r.name in hidden_rois:
                                continue
                            rx, ry = r.x, r.y
                            rw = r.w or 32
                            rh = r.h or 32
                            rcx = rx + rw / 2.0
                            rcy = ry + rh / 2.0
                            y_lbl = ry - 5 if ry >= 14 else ry + 13
                            svg_parts.append(
                                f'<text x="{rx}" y="{y_lbl}" fill="{HEX_ROI_REFS}" font-size="10" font-family="monospace" font-weight="bold" '
                                f'paint-order="stroke fill" stroke="#020617" stroke-width="2.5">{r.name}</text>'
                                f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" '
                                f'stroke="{HEX_ROI_REFS}" stroke-width="2" stroke-dasharray="3 3" '
                                f'fill="{HEX_ROI_REFS}" fill-opacity="0.18"/>'
                                f'<line x1="{rx}" y1="{rcy:.1f}" x2="{rx + rw}" y2="{rcy:.1f}" stroke="{HEX_ROI_REFS}" stroke-width="1.5"/>'
                                f'<line x1="{rcx:.1f}" y1="{ry}" x2="{rcx:.1f}" y2="{ry + rh}" stroke="{HEX_ROI_REFS}" stroke-width="1.5"/>'
                            )

                        # Draw digital ROIs: outer box, inner box (0.2 inset), and horizontal center dividing line
                        for d in dig_pos:
                            if d.name in hidden_rois:
                                continue
                            dx, dy, dw, dh = d.x, d.y, d.w, d.h
                            y_lbl = dy - 5 if dy >= 14 else dy + 13
                            inner_x = dx + dw * 0.2
                            inner_y = dy + dh * 0.2
                            inner_w = dw - dw * 0.4
                            inner_h = dh - dh * 0.4
                            line_y = dy + dh / 2.0
                            svg_parts.append(
                                f'<text x="{dx}" y="{y_lbl}" fill="{HEX_ROI_DIGITAL}" font-size="10" font-family="monospace" font-weight="bold" '
                                f'paint-order="stroke fill" stroke="#020617" stroke-width="2.5">{d.name}</text>'
                                f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" '
                                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="2" '
                                f'fill="{HEX_ROI_DIGITAL}" fill-opacity="0.12" rx="1"/>'
                                f'<rect x="{inner_x:.1f}" y="{inner_y:.1f}" width="{inner_w:.1f}" height="{inner_h:.1f}" '
                                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="1.2" fill-opacity="0"/>'
                                f'<line x1="{inner_x:.1f}" y1="{line_y:.1f}" x2="{inner_x + inner_w:.1f}" y2="{line_y:.1f}" '
                                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="1.2"/>'
                            )

                        # Draw analog ROIs: outer box, inscribed ellipse/circle, and crosshairs
                        for a in ana_pos:
                            if a.name in hidden_rois:
                                continue
                            ax, ay, aw, ah = a.x, a.y, a.w, a.h
                            acx = ax + aw / 2.0
                            acy = ay + ah / 2.0
                            y_lbl = ay - 5 if ay >= 14 else ay + 13
                            svg_parts.append(
                                f'<text x="{ax}" y="{y_lbl}" fill="{HEX_ROI_ANALOG}" font-size="10" font-family="monospace" font-weight="bold" '
                                f'paint-order="stroke fill" stroke="#020617" stroke-width="2.5">{a.name}</text>'
                                f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" '
                                f'stroke="{HEX_ROI_ANALOG}" stroke-width="2" '
                                f'fill="{HEX_ROI_ANALOG}" fill-opacity="0.10"/>'
                                f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="{aw/2.0:.1f}" ry="{ah/2.0:.1f}" '
                                f'stroke="{HEX_ROI_ANALOG}" stroke-width="1.5" fill-opacity="0"/>'
                                f'<line x1="{acx:.1f}" y1="{ay}" x2="{acx:.1f}" y2="{ay + ah}" stroke="{HEX_ROI_ANALOG}" stroke-width="1.2"/>'
                                f'<line x1="{ax}" y1="{acy:.1f}" x2="{ax + aw}" y2="{acy:.1f}" stroke="{HEX_ROI_ANALOG}" stroke-width="1.2"/>'
                            )

                        svg_parts.append("</g></svg>")
                        return "".join(svg_parts)

                    with (
                        ui.dialog() as roi_modal,
                        ui.card().classes(
                            f"{DIALOG_CARD} min-w-[340px] max-w-5xl max-h-[92vh] overflow-y-auto p-4 flex flex-col gap-3"
                        ),
                    ):
                        with card_header(
                            title="ROI & Reference Marks Inspector",
                            subtitle="Visual alignment markers and digitization region bounding boxes",
                            icon="crop_free",
                            color="cyan",
                            classes=DIALOG_HEADER_ROW,
                        ):
                            ui.button(icon="close", on_click=roi_modal.close).props(
                                "flat round dense text-xs aria-label='Close dialog'"
                            )

                        # ROI Overlays Selection Panel
                        with ui.column().classes(
                            "w-full bg-slate-950/60 p-2.5 rounded-xl border border-white/5 gap-2"
                        ):
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.icon("layers", size="xs").classes(
                                        "text-slate-300"
                                    )
                                    ui.label("ROI Overlays").classes(
                                        "font-bold text-slate-200 text-xs"
                                    )
                                with ui.row().classes("gap-1 items-center"):

                                    def show_all_rois() -> None:
                                        hidden_rois.clear()
                                        render_visibility_chips()
                                        update_canvas_view()

                                    def hide_all_rois() -> None:
                                        for d in dig_pos:
                                            hidden_rois.add(d.name)
                                        for a in ana_pos:
                                            hidden_rois.add(a.name)
                                        for r in ref_pos:
                                            hidden_rois.add(r.name)
                                        render_visibility_chips()
                                        update_canvas_view()

                                    ui.button("All", on_click=show_all_rois).props(
                                        "flat dense"
                                    ).classes(
                                        "text-[10px] text-cyan-400 hover:text-cyan-300 px-1.5 py-0.5"
                                    )
                                    ui.label("|").classes("text-slate-600 text-[10px]")
                                    ui.button("None", on_click=hide_all_rois).props(
                                        "flat dense"
                                    ).classes(
                                        "text-[10px] text-slate-400 hover:text-slate-300 px-1.5 py-0.5"
                                    )

                            visibility_container = ui.column().classes("w-full gap-2")

                            def toggle_roi_visibility(name: str) -> None:
                                if name in hidden_rois:
                                    hidden_rois.remove(name)
                                else:
                                    hidden_rois.add(name)
                                render_visibility_chips()
                                update_canvas_view()

                            def render_visibility_chips() -> None:
                                visibility_container.clear()
                                with visibility_container:
                                    if not dig_pos and not ana_pos and not ref_pos:
                                        ui.label("No ROIs configured").classes(
                                            "text-xs text-slate-500 italic"
                                        )
                                        return

                                    if dig_pos:
                                        with ui.column().classes("w-full gap-1"):
                                            n_vis_dig = len(dig_pos) - sum(
                                                1
                                                for d in dig_pos
                                                if d.name in hidden_rois
                                            )
                                            with ui.row().classes(
                                                "items-center gap-1.5"
                                            ):
                                                ui.element("span").classes(
                                                    "w-2 h-2 rounded bg-blue-500 shadow-sm shadow-blue-500/50"
                                                )
                                                ui.label(
                                                    f"Digital Counters ({n_vis_dig}/{len(dig_pos)})"
                                                ).classes(
                                                    "text-[10px] font-semibold text-blue-400 uppercase tracking-wider"
                                                )
                                            with ui.row().classes(
                                                "w-full flex-wrap gap-1"
                                            ):
                                                for d in dig_pos:
                                                    is_hidden = d.name in hidden_rois
                                                    btn_classes = (
                                                        "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                        "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                        if is_hidden
                                                        else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950/80 "
                                                        "text-blue-300 border border-blue-500/40 hover:bg-blue-900/80"
                                                    )
                                                    icon_name = (
                                                        "visibility_off"
                                                        if is_hidden
                                                        else "visibility"
                                                    )
                                                    ui.button(
                                                        d.name,
                                                        icon=icon_name,
                                                        on_click=lambda name=d.name: toggle_roi_visibility(
                                                            name
                                                        ),
                                                    ).props(
                                                        "dense flat"
                                                        if is_hidden
                                                        else "dense unelevated"
                                                    ).classes(
                                                        btn_classes
                                                    )

                                    if ana_pos:
                                        with ui.column().classes("w-full gap-1"):
                                            n_vis_ana = len(ana_pos) - sum(
                                                1
                                                for a in ana_pos
                                                if a.name in hidden_rois
                                            )
                                            with ui.row().classes(
                                                "items-center gap-1.5"
                                            ):
                                                ui.element("span").classes(
                                                    "w-2 h-2 rounded bg-amber-500 shadow-sm shadow-amber-500/50"
                                                )
                                                ui.label(
                                                    f"Analog Dials ({n_vis_ana}/{len(ana_pos)})"
                                                ).classes(
                                                    "text-[10px] font-semibold text-amber-400 uppercase tracking-wider"
                                                )
                                            with ui.row().classes(
                                                "w-full flex-wrap gap-1"
                                            ):
                                                for a in ana_pos:
                                                    is_hidden = a.name in hidden_rois
                                                    btn_classes = (
                                                        "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                        "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                        if is_hidden
                                                        else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 "
                                                        "text-amber-300 border border-amber-500/40 hover:bg-amber-900/80"
                                                    )
                                                    icon_name = (
                                                        "visibility_off"
                                                        if is_hidden
                                                        else "visibility"
                                                    )
                                                    ui.button(
                                                        a.name,
                                                        icon=icon_name,
                                                        on_click=lambda name=a.name: toggle_roi_visibility(
                                                            name
                                                        ),
                                                    ).props(
                                                        "dense flat"
                                                        if is_hidden
                                                        else "dense unelevated"
                                                    ).classes(
                                                        btn_classes
                                                    )

                                    if ref_pos:
                                        with ui.column().classes("w-full gap-1"):
                                            n_vis_ref = len(ref_pos) - sum(
                                                1
                                                for r in ref_pos
                                                if r.name in hidden_rois
                                            )
                                            with ui.row().classes(
                                                "items-center gap-1.5"
                                            ):
                                                ui.element("span").classes(
                                                    "w-2 h-2 rounded bg-emerald-500 shadow-sm shadow-emerald-500/50"
                                                )
                                                ui.label(
                                                    f"Alignment References ({n_vis_ref}/{len(ref_pos)})"
                                                ).classes(
                                                    "text-[10px] font-semibold text-emerald-400 uppercase tracking-wider"
                                                )
                                            with ui.row().classes(
                                                "w-full flex-wrap gap-1"
                                            ):
                                                for r in ref_pos:
                                                    is_hidden = r.name in hidden_rois
                                                    btn_classes = (
                                                        "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                        "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                        if is_hidden
                                                        else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 "
                                                        "text-emerald-300 border border-emerald-500/40 hover:bg-emerald-900/80"
                                                    )
                                                    icon_name = (
                                                        "visibility_off"
                                                        if is_hidden
                                                        else "visibility"
                                                    )
                                                    ui.button(
                                                        r.name,
                                                        icon=icon_name,
                                                        on_click=lambda name=r.name: toggle_roi_visibility(
                                                            name
                                                        ),
                                                    ).props(
                                                        "dense flat"
                                                        if is_hidden
                                                        else "dense unelevated"
                                                    ).classes(
                                                        btn_classes
                                                    )

                        # Image Container with SVG Overlay
                        with ui.element("div").classes(
                            "w-full rounded-xl bg-slate-950 p-2 border border-white/10 flex items-center justify-center overflow-hidden max-h-[65vh]"
                        ):
                            init_svg = build_svg_content()
                            init_b64_svg = base64.b64encode(
                                init_svg.encode("utf-8")
                            ).decode("utf-8")
                            viewport_image = (
                                ui.interactive_image(
                                    f"data:image/svg+xml;base64,{init_b64_svg}"
                                )
                                .props("no-spinner")
                                .classes("max-h-[60vh] object-contain rounded-lg")
                            )

                        def update_canvas_view() -> None:
                            svg_data = build_svg_content()
                            b64_svg = base64.b64encode(svg_data.encode("utf-8")).decode(
                                "utf-8"
                            )
                            viewport_image.set_source(
                                f"data:image/svg+xml;base64,{b64_svg}"
                            )

                        render_visibility_chips()

                        with ui.row().classes(
                            "w-full justify-between items-center pt-2 border-t border-white/10"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.button("Open Raw /roi", icon="open_in_new").props(
                                    'flat dense color=cyan text-xs href="/roi" target="_blank"'
                                )
                                ui.label(f"{cam_w}x{cam_h} px").classes(
                                    "text-[10px] text-slate-500 font-mono"
                                )
                            ui.button("Close", on_click=roi_modal.close).props(
                                "flat dense color=primary text-xs"
                            )

                    roi_modal.open()

                with ui.row().classes("w-full gap-6 items-start"):
                    # Processed image with multi-stage switcher
                    with ui.column().classes("flex-1 min-w-[340px] gap-2"):
                        with ui.row().classes(f"{ROW_HEADER} gap-2 flex-wrap"):
                            with ui.row().classes(ROW_ITEMS_CENTER):
                                ui.icon("photo_camera", color="cyan").classes(
                                    "text-base"
                                )
                                ui.label("Processed Capture").classes(
                                    f"{HEADING_SECTION} text-sm text-gray-200"
                                )

                            with ui.row().classes(ROW_ITEMS_CENTER):
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
                                    "original": "Original",
                                    "rotated": "Rotated",
                                    "aligned": "Aligned",
                                    "cropped": "Cropped",
                                    "denoised": "Denoised",
                                    "roi": "ROIs",
                                    "final": "Final",
                                },
                                value=self.active_image_stage,
                                on_change=on_stage_toggle,
                            ).props(
                                "dense rounded unelevated toggle-color=cyan text-color=grey-4"
                            ).classes(
                                "text-xs font-medium bg-slate-950/80 p-0.5"
                            )

                        stage_image_container = ui.element("div").classes(
                            PANEL_STAGE_IMAGE
                        )
                        render_stage_image()

                    # Deductions Breakdown (Interactive Zoom Cards)
                    with ui.column().classes("flex-1 min-w-[320px] gap-4"):
                        if result.digital_results:
                            with ui.row().classes(ROW_HEADER):
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.icon("pin", color="cyan").classes("text-base")
                                    ui.label("Digital Counters").classes(
                                        f"{HEADING_SECTION} text-sm text-gray-200"
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
                                        .classes(f"{CARD_DIGIT_CROP} {CLICKABLE_CARD}")
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
                            with ui.row().classes(ROW_HEADER):
                                with ui.row().classes(ROW_ITEMS_CENTER):
                                    ui.icon("speed", color="amber").classes("text-base")
                                    ui.label("Analog Dials").classes(
                                        f"{HEADING_SECTION} text-sm text-gray-200"
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
                                        .classes(f"{CARD_DIGIT_CROP} {CLICKABLE_CARD}")
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

        # Standard Page Header & Actions
        with page_header(
            title="Meter Dashboard",
            subtitle="Live readouts, multi-stage captures, and telemetry",
            icon="speed",
            color="cyan",
            classes="w-full justify-between items-center mb-2 flex-wrap gap-2",
        ):
            self.spinner = ui.spinner("dots", size="md", color="cyan")
            self.spinner.visible = False

            with ui.row().classes(
                f"{ROW_ITEMS_CENTER} text-xs font-mono"
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

                self.refresh_btn = (
                    ui.button(
                        "Refresh",
                        icon="refresh",
                        on_click=on_manual_refresh,
                    )
                    .props("unelevated color=primary size=sm")
                    .classes("shadow-md shadow-blue-500/20 rounded-xl")
                )

                ui.button(
                    icon="bolt",
                    on_click=trigger_background_poll,
                ).props(
                    "flat round dense color=amber size=sm aria-label='Trigger background poll'"
                ).tooltip("Trigger Poller Execution")

                ui.button(
                    icon="open_in_new",
                ).props(
                    'flat round dense color=cyan size=sm href="/meter" target="_blank" aria-label="Open /meter REST API"'
                ).tooltip("Open /meter REST API")

        with (
            ui.tabs().classes(TABS_BAR_HORIZONTAL).props(TABS_PROPS_HORIZONTAL) as tabs
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
            with ui.tab_panel(consumption).classes("p-0"):
                stats_container = ui.column().classes("w-full")
            with ui.tab_panel(readings_log).classes("p-0"):
                history_container = ui.column().classes("w-full")

        def on_subtab_change(e: Any) -> None:
            val = getattr(e, "value", e)
            if (
                val is consumption
                or val == "Consumption"
                or getattr(val, "name", "") == "Consumption"
            ) and "consumption" not in self._rendered_tabs:
                self._rendered_tabs.add("consumption")
                self.consumption_card.render(stats_container)
            elif (
                val is time_machine
                or val == "Time Machine"
                or getattr(val, "name", "") == "Time Machine"
            ) and "time_machine" not in self._rendered_tabs:
                self._rendered_tabs.add("time_machine")
                self.time_machine_card.render(tm_container)
            elif (
                val is readings_log
                or val == "Readings Log"
                or getattr(val, "name", "") == "Readings Log"
            ) and "history" not in self._rendered_tabs:
                self._rendered_tabs.add("history")
                self.history_card.render(history_container)

        tabs.on_value_change(on_subtab_change)

        await do_fetch()
