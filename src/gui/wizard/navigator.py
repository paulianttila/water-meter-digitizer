"""Wizard navigation state machine, step ordering, and transition coordination."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from data_classes import RefImage

if TYPE_CHECKING:
    from nicegui import ui

    from callbacks import Callbacks
    from configuration import Config
    from gui.wizard.steps import (
        AdjustStep,
        DownloadImageStep,
        DrawAnalogRoisStep,
        DrawDigitalRoisStep,
        DrawRefsStep,
        InitialRotateStep,
        MeterStep,
        ServicesStep,
    )

logger = logging.getLogger(__name__)

NAME_DOWNLOAD_IMAGE = "Download image"
NAME_INITIAL_ROTATE = "Initial rotate"
NAME_DRAW_REFS = "Draw reference points"
NAME_ADJUST = "Adjust image"
NAME_DRAW_DIGITAL_ROIS = "Draw digital region of interest"
NAME_DRAW_ANALOG_ROIS = "Draw analog region of interest"
NAME_METERS = "Meters"
NAME_SERVICES = "Services & Integrations"
NAME_FINAL = "Final"

steps_order = [
    NAME_DOWNLOAD_IMAGE,
    NAME_INITIAL_ROTATE,
    NAME_DRAW_REFS,
    NAME_ADJUST,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_ANALOG_ROIS,
    NAME_METERS,
    NAME_SERVICES,
    NAME_FINAL,
]


class WizardNavigator:
    """Coordinates step transitions, predecessor image propagation, and nav button states."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.previous_step: str = NAME_DOWNLOAD_IMAGE
        self.refs_enabled_in_image: bool = False
        self.digital_rois_enabled_in_image: bool = False
        self.analog_rois_enabled_in_image: bool = False

    @staticmethod
    def is_step_forward(new_step: str, previous_step: str) -> bool:
        """Return True if new_step occurs after previous_step in the wizard order."""
        if previous_step == "" or previous_step not in steps_order:
            return True
        if new_step not in steps_order:
            return False
        return steps_order.index(new_step) > steps_order.index(previous_step)

    @staticmethod
    def get_source_image_for_step(
        step_name: str,
        download_step: DownloadImageStep,
        initial_rotate_step: InitialRotateStep,
        adjust_step: AdjustStep,
        fallback_image: str = "",
    ) -> str:
        """Select the appropriate predecessor output image for a given step."""
        raw_img = download_step.get_image() or fallback_image
        if step_name in (NAME_DOWNLOAD_IMAGE, NAME_INITIAL_ROTATE):
            return raw_img

        rotated_img = initial_rotate_step.get_image() or raw_img
        if step_name in (NAME_DRAW_REFS, NAME_ADJUST):
            return rotated_img

        adjusted_img = adjust_step.get_image() or rotated_img
        return adjusted_img

    @staticmethod
    def get_image_by_step_name(
        name: str,
        download_image_step: DownloadImageStep,
        initial_rotate_step: InitialRotateStep,
        draw_refs_step: DrawRefsStep,
        adjust_step: AdjustStep,
        draw_digital_rois_step: DrawDigitalRoisStep,
        draw_analog_rois_step: DrawAnalogRoisStep,
        meters_step: MeterStep,
        services_step: ServicesStep,
        final_step: Any,
    ) -> str:
        """Fetch step-rendered output image by step name."""
        if name == NAME_DOWNLOAD_IMAGE:
            return download_image_step.get_image()
        if name == NAME_INITIAL_ROTATE:
            return initial_rotate_step.get_image()
        if name == NAME_DRAW_REFS:
            return draw_refs_step.get_image()
        if name == NAME_ADJUST:
            return adjust_step.get_image()
        if name == NAME_DRAW_DIGITAL_ROIS:
            return draw_digital_rois_step.get_image()
        if name == NAME_DRAW_ANALOG_ROIS:
            return draw_analog_rois_step.get_image()
        if name == NAME_METERS:
            return meters_step.get_image()
        if name == NAME_SERVICES:
            return services_step.get_image()
        if name == NAME_FINAL:
            return final_step.get_image()
        return ""

    @staticmethod
    def set_image_by_step_name(
        name: str,
        image: str,
        initial_rotate_step: InitialRotateStep,
        draw_refs_step: DrawRefsStep,
        adjust_step: AdjustStep,
        draw_digital_rois_step: DrawDigitalRoisStep,
        draw_analog_rois_step: DrawAnalogRoisStep,
        meters_step: MeterStep,
        services_step: ServicesStep,
        final_step: Any,
    ) -> None:
        """Update step input image and configured preprocessing parameters."""
        if not image:
            return
        if name == NAME_INITIAL_ROTATE:
            initial_rotate_step.update_image(image)
        elif name == NAME_DRAW_REFS:
            draw_refs_step.update_image(image)
        elif name == NAME_ADJUST:
            adjust_step.update_image(image)
        elif name == NAME_DRAW_DIGITAL_ROIS:
            draw_digital_rois_step.update_image(
                image,
                adjust_step.autocontrast_cut_images_enabled.value,
                adjust_step.autocontrast_cut_images_cutoff_low.value,
                adjust_step.autocontrast_cut_images_cutoff_high.value,
                glare_suppression=(
                    adjust_step.glare_enabled.value
                    and adjust_step.glare_apply_to_cut_images.value
                ),
                glare_mode=adjust_step.glare_mode.value or "clahe",
                glare_inpaint_threshold=int(
                    adjust_step.glare_inpaint_threshold.value or 230
                ),
                glare_inpaint_radius=int(adjust_step.glare_inpaint_radius.value or 3),
                glare_clahe_clip_limit=float(
                    adjust_step.glare_clahe_clip_limit.value or 2.0
                ),
                glare_clahe_grid_size=int(adjust_step.glare_clahe_grid_size.value or 8),
                unsharp=(
                    adjust_step.adjust_enabled.value
                    and adjust_step.auto_sharpen_cut_images.value
                ),
                unsharp_radius=float(adjust_step.unsharp_radius.value or 1.0),
                unsharp_amount=float(adjust_step.unsharp_amount.value or 1.5),
                unsharp_threshold=int(adjust_step.unsharp_threshold.value or 3),
            )
        elif name == NAME_DRAW_ANALOG_ROIS:
            draw_analog_rois_step.update_image(
                image,
                adjust_step.autocontrast_cut_images_enabled.value,
                adjust_step.autocontrast_cut_images_cutoff_low.value,
                adjust_step.autocontrast_cut_images_cutoff_high.value,
                glare_suppression=(
                    adjust_step.glare_enabled.value
                    and adjust_step.glare_apply_to_cut_images.value
                ),
                glare_mode=adjust_step.glare_mode.value or "clahe",
                glare_inpaint_threshold=int(
                    adjust_step.glare_inpaint_threshold.value or 230
                ),
                glare_inpaint_radius=int(adjust_step.glare_inpaint_radius.value or 3),
                glare_clahe_clip_limit=float(
                    adjust_step.glare_clahe_clip_limit.value or 2.0
                ),
                glare_clahe_grid_size=int(adjust_step.glare_clahe_grid_size.value or 8),
                unsharp=(
                    adjust_step.adjust_enabled.value
                    and adjust_step.auto_sharpen_cut_images.value
                ),
                unsharp_radius=float(adjust_step.unsharp_radius.value or 1.0),
                unsharp_amount=float(adjust_step.unsharp_amount.value or 1.5),
                unsharp_threshold=int(adjust_step.unsharp_threshold.value or 3),
            )
        elif name == NAME_METERS:
            meters_step.update_image(image)
        elif name == NAME_SERVICES:
            services_step.update_image(image)
        elif name == NAME_FINAL:
            final_step.update_image(image)

    @staticmethod
    def update_wizard_nav(
        current_step: str,
        wizard_prev_btn: ui.button | None,
        wizard_step_badge: ui.label | None,
        wizard_next_btn: ui.button | None,
    ) -> None:
        """Update navigation button visibility, badges, and styles."""
        if wizard_prev_btn is None:
            return
        idx = steps_order.index(current_step) if current_step in steps_order else 0
        total = len(steps_order)

        # Update Back button visibility
        wizard_prev_btn.set_visibility(idx > 0)

        # Update Step Badge
        if wizard_step_badge is not None:
            wizard_step_badge.text = f"Step {idx + 1} of {total}: {current_step}"

        # Update Next button visibility & styling
        if wizard_next_btn is not None:
            if idx == total - 1:
                wizard_next_btn.set_visibility(False)
            else:
                wizard_next_btn.set_visibility(True)
                wizard_next_btn.text = "Continue"
                wizard_next_btn.props("unelevated no-caps icon-right=arrow_forward")
                wizard_next_btn.classes(
                    "px-4 py-1.5 rounded-lg text-sm font-semibold "
                    "bg-blue-600 hover:bg-blue-500 text-white shadow-md "
                    "shadow-blue-950/40 transition-colors",
                    remove="from-emerald-600 to-teal-600 hover:from-emerald-500 "
                    "hover:to-teal-500 shadow-emerald-950/40 transition-all "
                    "bg-gradient-to-r from-blue-600 to-cyan-600 "
                    "hover:from-blue-500 hover:to-cyan-500 shadow-cyan-950/40",
                )

    def handle_stepper_change(
        self,
        step: str,
        download_image_step: DownloadImageStep,
        initial_rotate_step: InitialRotateStep,
        draw_refs_step: DrawRefsStep,
        adjust_step: AdjustStep,
        draw_digital_rois_step: DrawDigitalRoisStep,
        draw_analog_rois_step: DrawAnalogRoisStep,
        meters_step: MeterStep,
        services_step: ServicesStep,
        final_step: Any,
        set_image_fn: Callable[[str], None],
        set_comparison_image_fn: Callable[[str], None],
        update_svg_fn: Callable[..., None],
        gather_config_fn: Callable[[], Config],
        wizard_prev_btn: ui.button | None,
        wizard_step_badge: ui.label | None,
        wizard_next_btn: ui.button | None,
        fallback_image: str = "",
    ) -> None:
        """Coordinate step transitions, propagate predecessor images, and sync ROIs."""
        logger.debug(f"Step: {self.previous_step} -> {step}")

        # Update ROI overlay visibility flags
        self.refs_enabled_in_image = step == NAME_DRAW_REFS
        self.digital_rois_enabled_in_image = step == NAME_DRAW_DIGITAL_ROIS
        self.analog_rois_enabled_in_image = step == NAME_DRAW_ANALOG_ROIS
        if step in (NAME_METERS, NAME_SERVICES, NAME_FINAL):
            self.digital_rois_enabled_in_image = True
            self.analog_rois_enabled_in_image = True
        if step == NAME_FINAL:
            self.refs_enabled_in_image = True

        # Sync reference rois to adjust step
        if step == NAME_ADJUST:
            config_dir = self.callbacks.get_config().config_dir
            ref_images = []
            for roi in draw_refs_step.rois:
                ref_path = f"{config_dir}/ref_{roi.name}_x{roi.x}_y{roi.y}.jpg"
                ref_images.append(
                    RefImage(
                        name=roi.name,
                        x=roi.x,
                        y=roi.y,
                        w=roi.w,
                        h=roi.h,
                        file_name=ref_path if os.path.exists(ref_path) else "",
                    )
                )
            adjust_step.ref_images = ref_images

        # Update step's image from its pipeline predecessor
        src_img = self.get_source_image_for_step(
            step,
            download_image_step,
            initial_rotate_step,
            adjust_step,
            fallback_image=fallback_image,
        )
        self.set_image_by_step_name(
            step,
            src_img,
            initial_rotate_step,
            draw_refs_step,
            adjust_step,
            draw_digital_rois_step,
            draw_analog_rois_step,
            meters_step,
            services_step,
            final_step,
        )

        if step == NAME_ADJUST:
            adjust_step._update_preview_canvas()
        else:
            current_img = (
                self.get_image_by_step_name(
                    step,
                    download_image_step,
                    initial_rotate_step,
                    draw_refs_step,
                    adjust_step,
                    draw_digital_rois_step,
                    draw_analog_rois_step,
                    meters_step,
                    services_step,
                    final_step,
                )
                or src_img
            )
            set_image_fn(current_img)
            set_comparison_image_fn("")

            # Ensure active step ROIs are freshly synced and SVG canvas is updated
            if step == NAME_DRAW_REFS:
                draw_refs_step._show_rois()
            elif step == NAME_DRAW_DIGITAL_ROIS:
                draw_digital_rois_step._show_rois()
            elif step == NAME_DRAW_ANALOG_ROIS:
                draw_analog_rois_step._show_rois()
            elif step in (NAME_METERS, NAME_SERVICES, NAME_FINAL):
                draw_digital_rois_step._show_rois()
                draw_analog_rois_step._show_rois()
                if step == NAME_FINAL:
                    draw_refs_step._show_rois()
            else:
                update_svg_fn()

        if step == NAME_METERS:
            meters_step.refresh_digit_names()

        if step == NAME_FINAL:
            cfg = gather_config_fn()
            final_step.set_config(cfg)

        self.previous_step = step
        self.update_wizard_nav(
            step,
            wizard_prev_btn,
            wizard_step_badge,
            wizard_next_btn,
        )
