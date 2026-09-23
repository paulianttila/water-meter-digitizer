"""Detailed reading record inspection modal dialog."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from nicegui import ui

from gui.components.page_header import card_header
from gui.theme import (
    DIALOG_CARD,
    DIALOG_HEADER_ROW,
    HEADING_SECTION,
    HEADING_SUBSECTION,
    ROW_HEADER,
)

if TYPE_CHECKING:
    from callbacks import Callbacks
    from storage.base import ReadingRecord


def open_reading_dialog(callbacks: Callbacks, record: ReadingRecord) -> None:
    """Open a detailed inspection modal for a specific reading record."""
    rec_id = record.id or 0
    ts_str = record.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    frame_data_uri = callbacks.get_frame_data_uri(rec_id) if rec_id else None

    with (
        ui.dialog() as dialog,
        ui.card().classes(f"{DIALOG_CARD} min-w-[340px] md:min-w-[680px] max-w-4xl"),
    ):
        with card_header(
            title=f"Reading Record #{rec_id}",
            icon="manage_search",
            color="cyan",
            classes=DIALOG_HEADER_ROW,
            title_classes=f"{HEADING_SECTION} text-lg text-white",
        ):
            if record.flow_detected:
                ui.badge("💧 Flow Detected", color="blue").classes("text-xs font-bold")
            if record.error:
                ui.badge("⚠️ Error", color="negative").classes("text-xs font-bold")
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
                                        c_val = conf_scores.get(f"digital_{k}", 98.0)
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
