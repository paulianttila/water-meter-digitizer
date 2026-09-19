"""Unsharp mask, spatial sharpness, and focus scoring card."""

from typing import Any

from .constants import BADGE_CLASSES


def build_unsharp_mask_card(step: Any, ui: Any) -> None:
    """Build the Sharpness & Edge Enhancement expansion card."""
    with (
        ui.expansion(
            "Sharpness & Edge Enhancement", icon="details", value=False
        ).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-2.5 p-2.5"),
    ):
        with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
            step.sharpness_mode = (
                ui.select(
                    {
                        "unsharp_mask": "Luminance Unsharp Mask (Pro)",
                        "auto": "Adaptive Auto-Sharpness",
                        "standard": "Standard Sharpness Filter",
                    },
                    label="Sharpness Algorithm",
                    value="unsharp_mask",
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-64")
                .tooltip("Algorithm used for spatial digit edge enhancement")
            )

            with ui.row().classes("items-center gap-2"):
                ui.label("Focus Metric:").classes("text-xs text-slate-400 font-medium")
                step.focus_score_badge = ui.label("Calculating...").classes(
                    "text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800 border border-white/10 text-emerald-400"
                )

        with ui.column().classes("w-full gap-2.5"):
            # Standard Sharpness (visible when standard is selected)
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.sharpness_mode, "value", lambda v: v == "standard"
                )
            ):
                ui.label("Sharpness").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.adjust_sharpness = (
                    ui.slider(
                        min=0.0,
                        max=3.0,
                        step=0.1,
                        value=1.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.adjust_sharpness,
                    "value",
                    lambda v: f"{float(v or 1.0):.2f}x",
                )

            # Unsharp Mask Amount
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.sharpness_mode,
                    "value",
                    lambda v: v in ("unsharp_mask", "auto"),
                )
            ):
                ui.label("Amount (Strength)").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.unsharp_amount = (
                    ui.slider(
                        min=0.0,
                        max=4.0,
                        step=0.1,
                        value=1.5,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.unsharp_amount,
                    "value",
                    lambda v: f"{float(v or 1.5):.2f}x",
                )

            # Unsharp Mask Radius
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.sharpness_mode,
                    "value",
                    lambda v: v in ("unsharp_mask", "auto"),
                )
            ):
                ui.label("Radius (px)").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.unsharp_radius = (
                    ui.slider(
                        min=0.5,
                        max=5.0,
                        step=0.1,
                        value=1.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.unsharp_radius,
                    "value",
                    lambda v: f"{float(v or 1.0):.1f}px",
                )

            # Unsharp Mask Threshold
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.sharpness_mode,
                    "value",
                    lambda v: v in ("unsharp_mask", "auto"),
                )
            ):
                ui.label("Noise Threshold").classes(
                    "w-24 text-xs font-semibold text-slate-300"
                )
                step.unsharp_threshold = (
                    ui.slider(
                        min=0,
                        max=20,
                        step=1,
                        value=3,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.unsharp_threshold,
                    "value",
                    lambda v: f"{int(float(v or 3))}",
                )

        step.auto_sharpen_cut_images = (
            ui.checkbox(
                "Sharpen Cut Images (ROIs) Individually",
                value=False,
                on_change=step._on_param_change,
            )
            .props("dense")
            .tooltip(
                "Apply luminance unsharp masking to cropped digit and pointer images before neural inference"
            )
        )
