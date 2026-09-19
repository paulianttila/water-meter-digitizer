"""Glare and specular reflection suppression card."""

from typing import Any

from .constants import BADGE_CLASSES


def build_glare_suppression_card(step: Any, ui: Any) -> None:
    """Build the Glare & Specular Reflection Suppression expansion card."""
    with (
        ui.expansion(
            "Glare & Specular Reflection Suppression",
            icon="flare",
            value=False,
        ).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-3 p-3"),
    ):
        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
            step.glare_enabled = ui.checkbox(
                "Enable Glare Suppression",
                value=False,
                on_change=step._on_param_change,
            ).tooltip("Suppress specular highlights on glossy meter glass")
            step.glare_apply_to_cut_images = ui.checkbox(
                "Apply to Cut Images (ROIs)",
                value=False,
                on_change=step._on_param_change,
            ).tooltip("Apply glare suppression to cropped digit/pointer images")
            step.glare_mode = (
                ui.select(
                    [
                        "clahe",
                        "inpaint",
                        "illumination_normalize",
                        "combined",
                    ],
                    label="Mode",
                    value="clahe",
                    on_change=step._on_param_change,
                )
                .classes("w-44")
                .tooltip(
                    "Filter mode: clahe, inpaint, "
                    "illumination_normalize, or combined"
                )
            )

        with ui.column().classes("w-full gap-4"):
            # CLAHE Clip Limit
            with ui.row().classes("w-full items-center gap-3 py-1"):
                ui.label("CLAHE Clip").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.glare_clahe_clip_limit = (
                    ui.slider(
                        min=0.1,
                        max=10.0,
                        step=0.2,
                        value=2.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.glare_clahe_clip_limit,
                    "value",
                    lambda v: f"{float(v or 2.0):.1f}",
                )

            # CLAHE Grid Size
            with ui.row().classes("w-full items-center gap-3 py-1"):
                ui.label("CLAHE Grid").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.glare_clahe_grid_size = (
                    ui.slider(
                        min=2,
                        max=32,
                        step=1,
                        value=8,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.glare_clahe_grid_size,
                    "value",
                    lambda v: f"{int(float(v or 8))}x{int(float(v or 8))}",
                )

            # Inpaint Threshold
            with ui.row().classes("w-full items-center gap-3 py-1"):
                ui.label("Inpaint Thresh").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.glare_inpaint_threshold = (
                    ui.slider(
                        min=100,
                        max=255,
                        step=1,
                        value=230,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.glare_inpaint_threshold,
                    "value",
                    lambda v: f"{int(float(v or 230))}",
                )

            # Inpaint Radius
            with ui.row().classes("w-full items-center gap-3 py-1"):
                ui.label("Inpaint Radius").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.glare_inpaint_radius = (
                    ui.slider(
                        min=1,
                        max=20,
                        step=1,
                        value=3,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.glare_inpaint_radius,
                    "value",
                    lambda v: f"{int(float(v or 3))}px",
                )
