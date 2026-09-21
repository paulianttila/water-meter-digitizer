"""Filter curves, tonal, and color adjustments card."""

from typing import Any

from .constants import BADGE_CLASSES


def build_filter_curves_card(step: Any, ui: Any) -> None:
    """Build the Tonal & Color Adjustments expansion card."""
    with (
        ui.expansion("Tonal & Color Adjustments", icon="palette", value=False).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-2.5 p-2.5"),
    ):
        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
            step.grayscale_enabled = (
                ui.checkbox(
                    "Grayscale",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Convert the full image to grayscale")
            )

        # Live Visual Sliders for Tonal Settings
        with ui.column().classes("w-full gap-2.5"):
            # Gamma Slider
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Gamma").classes("w-20 text-xs font-semibold text-slate-300")
                step.adjust_gamma = (
                    ui.slider(
                        min=0.2,
                        max=3.0,
                        step=0.05,
                        value=1.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.adjust_gamma,
                    "value",
                    lambda v: f"{float(v or 1.0):.2f}",
                )

            # Contrast
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Contrast").classes(
                    "w-20 text-xs font-semibold text-slate-300"
                )
                step.adjust_contrast = (
                    ui.slider(
                        min=0.0,
                        max=3.0,
                        step=0.05,
                        value=1.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.adjust_contrast,
                    "value",
                    lambda v: f"{float(v or 1.0):.2f}x",
                )

            # Brightness
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Brightness").classes(
                    "w-20 text-xs font-semibold text-slate-300"
                )
                step.adjust_brightness = (
                    ui.slider(
                        min=0.0,
                        max=3.0,
                        step=0.05,
                        value=1.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.adjust_brightness,
                    "value",
                    lambda v: f"{float(v or 1.0):.2f}x",
                )

            # Color Saturation
            with ui.row().classes("w-full items-center gap-3 py-0.5"):
                ui.label("Color / Sat").classes(
                    "w-20 text-xs font-semibold text-slate-300"
                )
                step.adjust_color = (
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
                    step.adjust_color,
                    "value",
                    lambda v: f"{float(v or 1.0):.2f}x",
                )
