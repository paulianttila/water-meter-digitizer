"""Luminance histogram and autocontrast expansion card."""

from typing import Any

from .constants import BADGE_CLASSES


def generate_histogram_svg(hist_data: dict) -> str:
    """Generate lightweight inline SVG area chart for 256-bin luminance histogram."""
    luma = hist_data.get("luminance", [0] * 256)
    if not luma or len(luma) < 256:
        luma = [0] * 256
    max_val = max(1, max(luma[1:255] if len(luma) > 2 else luma))

    points = []
    for i, val in enumerate(luma):
        h = min(60, int((val / max_val) * 54))
        y = 60 - h
        points.append(f"{i},{y}")

    polyline = " ".join(points)
    polygon = f"0,60 {polyline} 255,60"

    return f"""
    <div style="width:100%; height:75px; background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:6px; position:relative; overflow:hidden;">
        <svg viewBox="0 0 256 60" preserveAspectRatio="none" style="width:100%; height:100%;">
            <defs>
                <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85"/>
                    <stop offset="100%" stop-color="#0284c7" stop-opacity="0.10"/>
                </linearGradient>
            </defs>
            <polygon points="{polygon}" fill="url(#histGrad)" />
            <polyline points="{polyline}" fill="none" stroke="#38bdf8" stroke-width="1.2" />
        </svg>
    </div>
    """


def build_histogram_card(step: Any, ui: Any) -> None:
    """Build the Histogram & AutoContrast expansion card."""
    with (
        ui.expansion(
            "Histogram & AutoContrast", icon="auto_fix_high", value=False
        ).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-2.5 p-2.5"),
    ):
        # Live Histogram Area
        with ui.column().classes(
            "w-full gap-1 p-2 rounded-lg bg-slate-950/60 border border-white/5"
        ):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Luminance Distribution (Rec.709)").classes(
                    "text-xs font-semibold text-slate-400"
                )
                with ui.row().classes("gap-2 items-center"):
                    step.shadow_clip_badge = ui.label("Shadows: 0.0%").classes(
                        "text-[11px] font-mono text-cyan-400"
                    )
                    step.highlight_clip_badge = ui.label("Highlights: 0.0%").classes(
                        "text-[11px] font-mono text-amber-400"
                    )

            step.histogram_container = ui.html(generate_histogram_svg({})).classes(
                "w-full"
            )

        step.autocontrast_enabled = (
            ui.checkbox(
                "Full Frame AutoContrast",
                value=False,
                on_change=step._on_param_change,
            )
            .props("dense")
            .tooltip("Automatically optimize contrast histogram for full frame")
        )

        with ui.column().classes("w-full gap-2.5"):
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Cutoff Low").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.autocontrast_cutoff_low = (
                    ui.slider(
                        min=0,
                        max=50,
                        step=1,
                        value=2,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.autocontrast_cutoff_low,
                    "value",
                    lambda v: f"{int(float(v or 0))}%",
                )

            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Cutoff High").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.autocontrast_cutoff_high = (
                    ui.slider(
                        min=0,
                        max=50,
                        step=1,
                        value=45,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.autocontrast_cutoff_high,
                    "value",
                    lambda v: f"{int(float(v or 0))}%",
                )

        ui.separator().classes("bg-white/10 my-0.5")

        step.autocontrast_cut_images_enabled = (
            ui.checkbox(
                "Cut Images (ROIs) AutoContrast",
                value=False,
                on_change=step._on_param_change,
            )
            .props("dense")
            .tooltip(
                "Apply automatic contrast stretching individually on "
                "cropped digit/pointer ROI images"
            )
        )

        with ui.column().classes("w-full gap-2.5"):
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("ROI Cutoff Low").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.autocontrast_cut_images_cutoff_low = (
                    ui.slider(
                        min=0,
                        max=50,
                        step=1,
                        value=2,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.autocontrast_cut_images_cutoff_low,
                    "value",
                    lambda v: f"{int(float(v or 0))}%",
                )

            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("ROI Cutoff High").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.autocontrast_cut_images_cutoff_high = (
                    ui.slider(
                        min=0,
                        max=50,
                        step=1,
                        value=45,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.autocontrast_cut_images_cutoff_high,
                    "value",
                    lambda v: f"{int(float(v or 0))}%",
                )
