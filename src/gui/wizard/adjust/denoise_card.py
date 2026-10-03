"""Noise reduction and image denoising card."""

from typing import Any

from .constants import BADGE_CLASSES


def build_denoise_card(step: Any, ui: Any) -> None:
    """Build the Noise Reduction & Denoising expansion card."""
    with (
        ui.expansion(
            "Noise Reduction & Denoising",
            icon="waves",
            value=False,
        ).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-2.5 p-2.5"),
    ):
        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
            step.denoise_enabled = (
                ui.checkbox(
                    "Enable Denoising",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Enable edge-preserving noise reduction filter")
            )
            step.denoise_apply_to_cut_images = (
                ui.checkbox(
                    "Apply to Cut Images (ROIs)",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Apply denoising filter to cropped digit and dial images")
            )
            step.denoise_method = (
                ui.select(
                    {
                        "bilateral": "Bilateral (Fast, Edge-Preserving)",
                        "nlmeans": "Non-Local Means (Best Quality)",
                        "median": "Median (Salt & Pepper)",
                        "median_bilateral": "Hybrid Median + Bilateral",
                    },
                    label="Method",
                    value="bilateral",
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-64")
                .tooltip("Denoising algorithm to use")
            )

        with ui.column().classes("w-full gap-2.5"):
            # Diameter / Kernel Size (for bilateral, median, median_bilateral)
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v in ("bilateral", "median", "median_bilateral"),
                )
            ):
                ui.label("Kernel / Diameter").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_diameter = (
                    ui.slider(
                        min=1,
                        max=15,
                        step=2,
                        value=5,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_diameter,
                    "value",
                    lambda v: f"{int(float(v or 5))}px",
                )

            # Color Sigma (for bilateral, median_bilateral)
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v in ("bilateral", "median_bilateral"),
                )
            ):
                ui.label("Color Sigma").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_sigma_color = (
                    ui.slider(
                        min=5.0,
                        max=150.0,
                        step=5.0,
                        value=50.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_sigma_color,
                    "value",
                    lambda v: f"{float(v or 50.0):.0f}",
                )

            # Spatial Sigma (for bilateral, median_bilateral)
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v in ("bilateral", "median_bilateral"),
                )
            ):
                ui.label("Spatial Sigma").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_sigma_space = (
                    ui.slider(
                        min=5.0,
                        max=150.0,
                        step=5.0,
                        value=50.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_sigma_space,
                    "value",
                    lambda v: f"{float(v or 50.0):.0f}",
                )

            # NL-Means Filter Strength 'h'
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v == "nlmeans",
                )
            ):
                ui.label("Filter Strength (h)").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_strength = (
                    ui.slider(
                        min=1.0,
                        max=30.0,
                        step=0.5,
                        value=3.0,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_strength,
                    "value",
                    lambda v: f"{float(v or 3.0):.1f}",
                )

            # NL-Means Template Window
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v == "nlmeans",
                )
            ):
                ui.label("Template Window").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_template_window = (
                    ui.slider(
                        min=3,
                        max=11,
                        step=2,
                        value=7,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_template_window,
                    "value",
                    lambda v: f"{int(float(v or 7))}px",
                )

            # NL-Means Search Window
            with (
                ui.row()
                .classes("w-full items-center gap-3 py-0.5")
                .bind_visibility_from(
                    step.denoise_method,
                    "value",
                    lambda v: v == "nlmeans",
                )
            ):
                ui.label("Search Window").classes(
                    "w-28 text-xs font-semibold text-slate-300"
                )
                step.denoise_search_window = (
                    ui.slider(
                        min=7,
                        max=35,
                        step=2,
                        value=21,
                        on_change=step._on_param_change,
                    )
                    .classes("flex-1")
                    .props("label dense")
                )
                ui.label().classes(BADGE_CLASSES).bind_text_from(
                    step.denoise_search_window,
                    "value",
                    lambda v: f"{int(float(v or 21))}px",
                )
