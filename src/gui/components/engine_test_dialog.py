"""Harmonized configuration testing and recognition result dialog component.

Provides a unified test runner and diagnostic modal for validating digitizer
configurations across Configuration Editor, Setup Wizard, and Mock Camera Studio.
"""

import asyncio
import base64
import io
import logging
import time
from typing import Any

import PIL.Image
from nicegui import ui

from callbacks import Callbacks
from configuration import Config
from gui.components.page_header import card_header
from gui.theme import (
    DIALOG_CARD,
    DIALOG_FOOTER_ROW,
    DIALOG_HEADER_ROW,
    FONT_MONO_VALUE,
    PANEL_INNER,
    ROW_ACTIONS,
    ROW_HEADER,
    ROW_ITEMS_CENTER,
)
from processor.digitizer import MeterResult
from processor.image import ImageProcessor
from utils.diagnostics import get_allowed_asset_directories

logger = logging.getLogger(__name__)


def extract_meter_readouts(
    result: MeterResult,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract all configured meter readouts and individual digital/analog readout cards."""
    meters = getattr(result, "meters", []) or []
    meters_list: list[dict[str, Any]] = []

    for m in meters:
        m_name = getattr(m, "name", "meter")
        m_val = getattr(m, "value", "N/A")
        m_unit = getattr(m, "unit", "")
        m_qual = getattr(m, "quality", "good")
        m_conf = getattr(m, "confidence", 100.0)
        meters_list.append(
            {
                "name": m_name,
                "value": m_val,
                "unit": m_unit,
                "quality": m_qual,
                "confidence": m_conf,
            }
        )

    # Fallback if result.meters is empty
    if not meters_list:
        m_val = getattr(result, "value", "N/A")
        meters_list.append(
            {
                "name": "total",
                "value": m_val,
                "unit": "",
                "quality": "good",
                "confidence": 100.0,
            }
        )

    dig_results = getattr(result, "digital_results", {}) or {}
    ana_results = getattr(result, "analog_results", {}) or {}
    conf_scores = getattr(result, "confidence_scores", {}) or {}

    readout_items: list[dict[str, Any]] = []
    for name, val in dig_results.items():
        readout_items.append(
            {
                "name": name,
                "value": val,
                "confidence": conf_scores.get(name, 100.0),
                "is_digit": True,
            }
        )
    for name, val in ana_results.items():
        readout_items.append(
            {
                "name": name,
                "value": val,
                "confidence": conf_scores.get(name, 100.0),
                "is_digit": False,
            }
        )

    # Fallback if digital/analog results empty but readouts list present
    if not readout_items and hasattr(result, "readouts"):
        for r in getattr(result, "readouts", []) or []:
            r_name = getattr(r, "name", "roi")
            readout_items.append(
                {
                    "name": r_name,
                    "value": getattr(r, "value", "—"),
                    "confidence": getattr(r, "confidence", 0.0),
                    "is_digit": "digit" in r_name.lower(),
                }
            )

    return meters_list, readout_items


def render_roi_overlay(
    config: Config,
    image_bytes: bytes | None = None,
    url: str = "",
) -> str:
    """Render the composite visual ROI extraction overlay as a base64 JPEG data URI."""
    try:
        if image_bytes:
            pil_img = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
            roi_pil = (
                ImageProcessor().set_image(pil_img).draw_meter_rois(config).get_image()
            )
        else:
            target_url = url or config.image_source.url
            if not target_url:
                return ""
            roi_proc = (
                ImageProcessor()
                .download_image(
                    target_url,
                    config.image_source.timeout,
                    config.image_source.min_size,
                    allowed_directories=get_allowed_asset_directories(config),
                )
                .rotate_image(config.alignment.rotate_angle)
                .align_image(config.alignment.ref_images)
                .draw_meter_rois(config)
            )
            roi_pil = roi_proc.get_image()

        buf = io.BytesIO()
        roi_pil.save(buf, format="JPEG", quality=85)
        return (
            f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        )
    except Exception as e:
        logger.debug("Could not generate ROI overlay: %s", e)
        return ""


def show_engine_test_modal(
    result: MeterResult,
    config: Config,
    dur_ms: float,
    roi_overlay_b64: str = "",
    title_tag: str = "Active config.ini",
) -> ui.dialog:
    """Construct and display the test result diagnosis modal dialog."""
    meters_list, readout_items = extract_meter_readouts(result)

    with (
        ui.dialog() as dialog,
        ui.card()
        .classes(
            f"column no-wrap w-full max-w-4xl {DIALOG_CARD} max-h-[92vh] overflow-y-auto"
        )
        .style("max-width: 95vw; width: 900px;"),
    ):
        # Header Row
        with card_header(
            title="Digitizer Recognition Test Result",
            icon="analytics",
            color="cyan",
            classes=DIALOG_HEADER_ROW,
        ):
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense aria-label='Close dialog'"
            )

        # Configured Meters Section Header & Metadata Badges
        with ui.row().classes(f"{ROW_HEADER} px-0.5 pt-1"):
            with ui.row().classes(ROW_ACTIONS):
                ui.icon("speed", color="cyan", size="xs")
                ui.label("Configured Meters").classes(
                    "text-xs font-bold text-slate-300 uppercase tracking-wider"
                )
            with ui.row().classes(ROW_ITEMS_CENTER):
                ui.badge(title_tag, color="indigo").props("dense")
                ui.badge(f"⚡ {dur_ms} ms", color="teal").props("dense")
                meter_cnt = len(meters_list)
                ui.badge(
                    f"{meter_cnt} Meter{'s' if meter_cnt != 1 else ''}",
                    color="blue-grey",
                ).props("dense")

        # Configured Meters Grid Cards
        grid_cols = (
            "grid-cols-1"
            if len(meters_list) == 1
            else "grid-cols-1 sm:grid-cols-2 md:grid-cols-3"
        )
        with ui.grid().classes(f"w-full {grid_cols} gap-2.5"):
            for m in meters_list:
                m_name = m["name"]
                m_val = m["value"]
                m_unit = m["unit"]
                m_qual = m["quality"]
                m_conf = m["confidence"]
                q_color = (
                    "emerald"
                    if m_qual == "good"
                    else "amber" if m_qual == "warning" else "rose"
                )

                with ui.card().classes(
                    f"{PANEL_INNER} p-3.5 bg-slate-950/80 border-white/10 shadow-md"
                ):
                    with ui.row().classes(ROW_HEADER):
                        with ui.row().classes(ROW_ITEMS_CENTER):
                            ui.icon("water_drop", color="cyan", size="xs")
                            ui.label(m_name).classes(
                                "text-xs font-bold text-cyan-300 uppercase tracking-wide"
                            )
                        with ui.row().classes("items-center gap-1"):
                            ui.badge(f"{m_qual}", color=q_color).props("dense")
                            ui.badge(f"{m_conf:.1f}%", color="cyan").props("dense")

                    with ui.row().classes("items-baseline gap-1.5 py-0.5"):
                        ui.label(str(m_val)).classes(
                            f"{FONT_MONO_VALUE} text-white tracking-tight"
                        )
                        if m_unit:
                            ui.label(m_unit).classes(
                                "text-xs font-semibold text-slate-400"
                            )

        # Visual ROI Bounding Box Overlay Card
        if roi_overlay_b64:
            with ui.card().classes(
                "w-full p-3 bg-slate-950/70 border border-white/5 rounded-xl flex flex-col gap-2"
            ):
                with ui.row().classes(ROW_HEADER):
                    with ui.row().classes(ROW_ACTIONS):
                        ui.icon("crop", color="cyan", size="xs")
                        ui.label("ROI Extraction Overlay").classes(
                            "text-xs font-bold text-slate-200 uppercase tracking-wide"
                        )
                    with ui.row().classes(ROW_ACTIONS):
                        ui.badge("🟦 Digital ROIs", color="cyan").props("dense")
                        ui.badge("🟧 Analog ROIs", color="amber").props("dense")
                with ui.element("div").classes(
                    "w-full flex items-center justify-center bg-slate-950 rounded-lg p-2 overflow-hidden border border-white/10"
                ):
                    ui.image(roi_overlay_b64).props('fit="contain"').classes(
                        "w-full max-h-[460px] object-contain rounded-lg shadow"
                    ).style("max-width: 100%; height: auto;")

        # Breakdown of readouts
        with ui.column().classes("w-full gap-2 pt-1"):
            ui.label("Individual ROI Classifications").classes(
                "text-xs font-semibold text-slate-300 uppercase tracking-wider"
            )
            if not readout_items:
                ui.label("No individual readout items returned.").classes(
                    "text-xs text-slate-400 italic"
                )
            else:
                with ui.grid().classes(
                    "w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2"
                ):
                    for item in readout_items:
                        r_name = item["name"]
                        r_val = item["value"]
                        r_conf = item["confidence"]
                        is_dig = item["is_digit"]
                        tag_c = (
                            "border-cyan-500/30 text-cyan-300"
                            if is_dig
                            else "border-amber-500/30 text-amber-300"
                        )

                        with ui.card().classes(
                            f"p-2 bg-slate-950/60 border {tag_c} rounded-lg flex flex-col gap-1 text-xs"
                        ):
                            with ui.row().classes(ROW_HEADER):
                                ui.label(r_name).classes(
                                    "font-semibold text-slate-200 uppercase"
                                )
                                ui.label(f"{r_conf:.1f}%").classes(
                                    "text-[10px] text-slate-400"
                                )
                            ui.label(str(r_val)).classes(
                                "font-mono font-bold text-sm text-white"
                            )

        # Dialog Footer Actions
        with ui.row().classes(DIALOG_FOOTER_ROW):
            ui.button("Close", on_click=dialog.close).props("flat dense").classes(
                "text-slate-300 px-3"
            )

    dialog.open()
    return dialog


async def run_engine_test_dialog(
    config: Config,
    callbacks: Callbacks | None,
    image_bytes: bytes | None = None,
    url: str = "",
    title_tag: str = "Test Config",
    parent_spinner: Any = None,
) -> None:
    """Execute digitizer recognition pipeline and open result diagnosis dialog."""
    if not callbacks:
        ui.notify("Callbacks unavailable in standalone testing mode", type="warning")
        return

    if parent_spinner:
        parent_spinner.visible = True

    ui.notify("Running digitizer engine test...", type="info")

    target_url = url or config.image_source.url

    try:
        start_t = time.perf_counter()

        # Run inference in worker thread
        def _execute_test() -> tuple[MeterResult, str]:
            res = callbacks.get_meter_data(
                url=target_url,
                saveimages=False,
                config=config,
            )
            roi_overlay = render_roi_overlay(
                config=config,
                image_bytes=image_bytes,
                url=target_url,
            )
            return res, roi_overlay

        result, roi_b64 = await asyncio.to_thread(_execute_test)
        dur_ms = round((time.perf_counter() - start_t) * 1000, 1)

        show_engine_test_modal(
            result=result,
            config=config,
            dur_ms=dur_ms,
            roi_overlay_b64=roi_b64,
            title_tag=title_tag,
        )
    except Exception as ex:
        logger.exception("Digitizer engine test failed: %s", ex)
        ui.notify(f"Engine test failed: {ex}", type="negative")
    finally:
        if parent_spinner:
            parent_spinner.visible = False
