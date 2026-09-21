"""Rotation, cropping, and resizing card for image adjustments."""

from typing import Any


def build_rotation_crop_card(step: Any, ui: Any) -> None:
    """Build the Geometry & Cropping expansion card."""
    with (
        ui.expansion("Geometry & Cropping", icon="crop", value=True).classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "shadow-md overflow-hidden"
        ),
        ui.column().classes("w-full gap-2 p-2.5"),
    ):
        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            step.rotate_enabled = (
                ui.checkbox(
                    "Enable Fine Rotation",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Enable fine rotation angle correction")
            )
            step.rotate_angle = (
                ui.number(
                    "Angle (°)",
                    min=-359,
                    max=359,
                    step=0.5,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-28")
                .tooltip("Fine rotation angle in degrees (-359° to 359°)")
            )

        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            step.crop_enabled = (
                ui.checkbox(
                    "Enable Crop",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Enable rectangular cropping before alignment")
            )
            step.crop_x = (
                ui.number(
                    "X",
                    min=0,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-20")
                .tooltip("Crop starting X position in pixels")
            )
            step.crop_y = (
                ui.number(
                    "Y",
                    min=0,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-20")
                .tooltip("Crop starting Y position in pixels")
            )
            step.crop_w = (
                ui.number(
                    "Width",
                    min=640,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-24")
                .tooltip("Crop area width in pixels")
            )
            step.crop_h = (
                ui.number(
                    "Height",
                    min=480,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-24")
                .tooltip("Crop area height in pixels")
            )

        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            step.resize_enabled = (
                ui.checkbox(
                    "Enable Resize",
                    value=False,
                    on_change=step._on_param_change,
                )
                .props("dense")
                .tooltip("Enable image resizing")
            )
            step.resize_w = (
                ui.number(
                    "Width",
                    min=0,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-24")
                .tooltip("Resized image width in pixels")
            )
            step.resize_h = (
                ui.number(
                    "Height",
                    min=0,
                    max=10000,
                    step=1,
                    value=0,
                    on_change=step._on_param_change,
                )
                .props("dense outlined")
                .classes("w-24")
                .tooltip("Resized image height in pixels")
            )
