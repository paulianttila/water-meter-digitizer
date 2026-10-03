import base64
import logging
import time
from hashlib import sha256
from typing import Any

from nicegui import events, ui

import utils.image as ImageUtils
from callbacks import Callbacks
from config.meter_presets import MeterTypePreset
from configuration import Config
from data_classes import ImagePosition
from gui.components import open_config_history_dialog, open_confirm_dialog
from gui.dialogs import open_model_alignment_dialog
from gui.pages.base import BasePage
from gui.theme import TEXT_ZOOM_LABEL, TOOLBAR_ZOOM_CONTAINER
from gui.wizard.config_manager import WizardConfigManager, resolve_model_path
from gui.wizard.navigator import (
    NAME_ADJUST,
    NAME_DOWNLOAD_IMAGE,
    NAME_DRAW_ANALOG_ROIS,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_REFS,
    NAME_FINAL,
    NAME_INITIAL_ROTATE,
    NAME_METER_TYPE,
    NAME_METERS,
    NAME_SERVICES,
    WizardNavigator,
    steps_order,
)
from gui.wizard.steps import (
    AdjustStep,
    DownloadImageStep,
    DrawAnalogRoisStep,
    DrawDigitalRoisStep,
    DrawRefsStep,
    FinalStep,
    InitialRotateStep,
    MeterStep,
    MeterTypeStep,
    ServicesStep,
    select_best_model,
)

logger = logging.getLogger(__name__)

# Re-export constants for backward compatibility
__all__ = [
    "NAME_ADJUST",
    "NAME_DOWNLOAD_IMAGE",
    "NAME_DRAW_ANALOG_ROIS",
    "NAME_DRAW_DIGITAL_ROIS",
    "NAME_DRAW_REFS",
    "NAME_FINAL",
    "NAME_INITIAL_ROTATE",
    "NAME_METERS",
    "NAME_METER_TYPE",
    "NAME_SERVICES",
    "SetupPage",
    "resolve_model_path",
    "steps_order",
]

svg_grid = """
<defs>
    <pattern id="smallGrid" width="8" height="8" patternUnits="userSpaceOnUse">
        <path d="M 8 0 L 0 0 0 8" fill="none" stroke="gray" stroke-width="0.5"/>
    </pattern>
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
        <rect width="80" height="80" fill="url(#smallGrid)"/>
        <path d="M 80 0 L 0 0 0 80" fill="none" stroke="gray" stroke-width="1"/>
    </pattern>
</defs>
"""


class SetupPage(BasePage):
    def __init__(self, callbacks: Callbacks) -> None:
        super().__init__(callbacks)

        self.config_manager = WizardConfigManager(self.callbacks)
        self.navigator = WizardNavigator(self.callbacks)

        self.interactive_image: ui.interactive_image
        self.image_details: ui.label
        self.mouse_position: ui.label
        self.selected_position: ui.label
        self.spinner: ui.spinner

        self.download_image_step: DownloadImageStep
        self.meter_type_step: MeterTypeStep
        self.initial_rotate_step: InitialRotateStep
        self.draw_refs_step: DrawRefsStep
        self.adjust_step: AdjustStep
        self.draw_digital_rois_step: DrawDigitalRoisStep
        self.draw_analog_rois_step: DrawAnalogRoisStep
        self.meters_step: MeterStep
        self.services_step: ServicesStep
        self.final_step: FinalStep
        self.stepper: ui.stepper
        self.wizard_prev_btn: ui.button
        self.wizard_step_badge: ui.label
        self.wizard_next_btn: ui.button
        self.comparison_container: ui.element
        self.comparison_image: ui.image

        self.config: Config
        self.image: str = ""  # base64 str
        self.processed_image: str = ""
        self.refs = ""
        self.digital_rois = ""
        self.analog_rois = ""
        self.is_dirty: bool = False

        # Image size caching & interactive canvas zoom
        self.image_dimensions: tuple[int, int] = (0, 0)
        self._image_size_cache: dict[int, tuple[int, int]] = {}
        self.canvas_zoom: float = 1.0
        self.canvas_is_fit: bool = True
        self.zoom_label: ui.label | None = None
        self.canvas_wrapper: ui.element | None = None

        # Preset management state
        self._preset_pending: bool = False
        self._applied_preset_id: str | None = None
        self._applied_preset_dims: tuple[int, int] | None = None
        self._confirm_dialog_open: bool = False

    @property
    def previous_step(self) -> str:
        return self.navigator.previous_step

    @previous_step.setter
    def previous_step(self, value: str) -> None:
        self.navigator.previous_step = value

    @property
    def refs_enabled_in_image(self) -> bool:
        return self.navigator.refs_enabled_in_image

    @refs_enabled_in_image.setter
    def refs_enabled_in_image(self, value: bool) -> None:
        self.navigator.refs_enabled_in_image = value

    @property
    def digital_rois_enabled_in_image(self) -> bool:
        return self.navigator.digital_rois_enabled_in_image

    @digital_rois_enabled_in_image.setter
    def digital_rois_enabled_in_image(self, value: bool) -> None:
        self.navigator.digital_rois_enabled_in_image = value

    @property
    def analog_rois_enabled_in_image(self) -> bool:
        return self.navigator.analog_rois_enabled_in_image

    @analog_rois_enabled_in_image.setter
    def analog_rois_enabled_in_image(self, value: bool) -> None:
        self.navigator.analog_rois_enabled_in_image = value

    def get_image_dimensions(self) -> tuple[int, int]:
        """Get width and height of the current loaded image using dimensions cache."""
        if not self.image:
            return (640, 480)
        h_key = hash(self.image)
        if h_key in self._image_size_cache:
            self.image_dimensions = self._image_size_cache[h_key]
            return self.image_dimensions
        try:
            w, h = ImageUtils.image_size(
                ImageUtils.convert_base64_str_to_image(self.image)
            )
            if w > 0 and h > 0:
                self.image_dimensions = (w, h)
                self._image_size_cache[h_key] = (w, h)
                return (w, h)
        except Exception:
            pass
        return (640, 480)

    def _get_current_zoom_text(self) -> str:
        return "Fit" if self.canvas_is_fit else f"{int(self.canvas_zoom * 100)}%"

    def _sync_steps_zoom_label(self, text: str) -> None:
        for step in (
            getattr(self, "draw_refs_step", None),
            getattr(self, "draw_digital_rois_step", None),
            getattr(self, "draw_analog_rois_step", None),
        ):
            if step and hasattr(step, "update_zoom_display"):
                step.update_zoom_display(text)

    def apply_canvas_zoom(
        self,
        zoom: float | None = None,
        fit: bool = False,
        delta: float | None = None,
    ) -> None:
        """Apply zoom scale or fit mode to the interactive image canvas."""
        if not hasattr(self, "interactive_image") or self.interactive_image is None:
            return
        if fit:
            self.canvas_is_fit = True
            self.canvas_zoom = 1.0
            self.interactive_image.style("width: 100%; max-width: 100%; height: auto;")
            if self.zoom_label is not None:
                self.zoom_label.text = "Fit"
            self._sync_steps_zoom_label("Fit")
            return

        self.canvas_is_fit = False
        if delta is not None:
            self.canvas_zoom = max(0.25, min(3.0, round(self.canvas_zoom + delta, 2)))
        elif zoom is not None:
            self.canvas_zoom = max(0.25, min(3.0, round(zoom, 2)))
        pct = int(self.canvas_zoom * 100)
        label_text = f"{pct}%"
        w, _ = self.get_image_dimensions()
        if w > 0:
            target_w = int(w * self.canvas_zoom)
            self.interactive_image.style(
                f"width: {target_w}px; max-width: none; height: auto;"
            )
        else:
            self.interactive_image.style(
                f"width: {pct}%; max-width: none; height: auto;"
            )
        if self.zoom_label is not None:
            self.zoom_label.text = label_text
        self._sync_steps_zoom_label(label_text)

    def update_svg(self, draw: str = "") -> None:
        if not hasattr(self, "interactive_image") or self.interactive_image is None:
            return
        self.interactive_image.content = f"""
            {svg_grid}
            <rect width="100%" height="100%" fill="url(#grid)" />
            {self.refs if self.refs_enabled_in_image else ""}
            {self.digital_rois if self.digital_rois_enabled_in_image else ""}
            {self.analog_rois if self.analog_rois_enabled_in_image else ""}
            {draw if draw is not None else ""}
            """

    def set_image(self, base64_str: str) -> None:
        if not base64_str or base64_str == self.image:
            return
        self.image = base64_str
        self.print_image_hash("set_image", base64_str)
        w, h = self.get_image_dimensions()
        if hasattr(self, "image_details") and self.image_details is not None:
            self.image_details.text = f"Size: {w}x{h}"
        if hasattr(self, "interactive_image") and self.interactive_image is not None:
            self.interactive_image.set_source(f"data:image/png;base64,{base64_str}")
            self.interactive_image.update()
        if not self.canvas_is_fit:
            self.apply_canvas_zoom(self.canvas_zoom)
        self.update_svg()

    def set_comparison_image(self, base64_str: str = "") -> None:
        if (
            not hasattr(self, "comparison_container")
            or self.comparison_container is None
        ):
            return
        if base64_str:
            if hasattr(self, "comparison_image") and self.comparison_image is not None:
                self.comparison_image.set_source(f"data:image/jpeg;base64,{base64_str}")
            self.comparison_container.set_visibility(True)

            if (
                hasattr(self, "main_image_header")
                and self.main_image_header is not None
            ):
                self.main_image_header.set_visibility(True)
                self.main_image_label.text = "Original Image"
                self.main_image_tag.text = "ORIGINAL"
                if hasattr(self, "main_image_tag") and self.main_image_tag is not None:
                    self.main_image_tag.set_visibility(True)
        else:
            self.comparison_container.set_visibility(False)
            if (
                hasattr(self, "main_image_header")
                and self.main_image_header is not None
            ):
                self.main_image_header.set_visibility(True)
                if (
                    hasattr(self, "stepper")
                    and getattr(self.stepper, "value", "") == NAME_ADJUST
                ):
                    self.main_image_label.text = "Adjusted Image Preview"
                    self.main_image_tag.text = "ADJUSTED"
                    if (
                        hasattr(self, "main_image_tag")
                        and self.main_image_tag is not None
                    ):
                        self.main_image_tag.set_visibility(True)
                else:
                    self.main_image_label.text = "Original Image"
                    if (
                        hasattr(self, "main_image_tag")
                        and self.main_image_tag is not None
                    ):
                        self.main_image_tag.set_visibility(False)

    def print_image_hash(self, text: str, image: str) -> None:
        if image is None or image == "":
            logger.debug(f"{text}, hash: empty")
        else:
            data = image.encode("utf-8")
            logger.debug(f"{text}, hash: {sha256(data).hexdigest()}")

    def set_refs_to_svg_func(self, refs: str) -> None:
        self.refs = refs
        self.update_svg()

    def set_digital_rois_to_svg_func(self, rois: str) -> None:
        self.digital_rois = rois
        self.update_svg()

    def set_analog_rois_to_svg_func(self, rois: str) -> None:
        self.analog_rois = rois
        self.update_svg()

    def show_temp_draw_in_svg_func(self, draw: str) -> None:
        self.update_svg(draw)

    def gather_config(self) -> Config:
        self.config = self.config_manager.gather_config(
            download_image_step=self.download_image_step,
            initial_rotate_step=self.initial_rotate_step,
            draw_refs_step=self.draw_refs_step,
            adjust_step=self.adjust_step,
            draw_digital_rois_step=self.draw_digital_rois_step,
            draw_analog_rois_step=self.draw_analog_rois_step,
            meters_step=self.meters_step,
            services_step=self.services_step,
        )
        return self.config

    def save_refs(self) -> None:
        self.config_manager.save_refs(
            draw_refs_step=self.draw_refs_step,
            initial_rotate_step=self.initial_rotate_step,
            fallback_image_b64=self.image,
        )

    def get_step_by_name(self, step_name: str) -> Any:
        step_map = {
            NAME_METER_TYPE: getattr(self, "meter_type_step", None),
            NAME_DOWNLOAD_IMAGE: getattr(self, "download_image_step", None),
            NAME_INITIAL_ROTATE: getattr(self, "initial_rotate_step", None),
            NAME_DRAW_REFS: getattr(self, "draw_refs_step", None),
            NAME_ADJUST: getattr(self, "adjust_step", None),
            NAME_DRAW_DIGITAL_ROIS: getattr(self, "draw_digital_rois_step", None),
            NAME_DRAW_ANALOG_ROIS: getattr(self, "draw_analog_rois_step", None),
            NAME_METERS: getattr(self, "meters_step", None),
            NAME_SERVICES: getattr(self, "services_step", None),
            NAME_FINAL: getattr(self, "final_step", None),
        }
        return step_map.get(step_name)

    def update_wizard_nav(self, current_step: str) -> None:
        self.navigator.update_wizard_nav(
            current_step=current_step,
            wizard_prev_btn=getattr(self, "wizard_prev_btn", None),
            wizard_step_badge=getattr(self, "wizard_step_badge", None),
            wizard_next_btn=getattr(self, "wizard_next_btn", None),
        )

    def on_download_error(self, err_msg: str = "") -> None:
        self.show_offline_placeholder(
            message="Camera Offline / Unreachable",
            subtext="Check camera IP, port or credentials in Step 2",
            is_error=True,
        )
        if (
            hasattr(self, "download_image_step")
            and self.download_image_step is not None
        ):
            self.download_image_step.handle_camera_error(err_msg)

    def _apply_meter_type_preset(
        self, force: bool = False, preset: MeterTypePreset | None = None
    ) -> None:
        if preset is None:
            preset = self.meter_type_step.selected_preset
        if preset is None or preset.id == "custom":
            return

        digital_names = self.meter_type_step.effective_digital_roi_names
        analog_names = self.meter_type_step.effective_analog_roi_names
        unit = self.meter_type_step.unit

        # Get actual image dimensions for ROI placement
        img_w, img_h = self.get_image_dimensions()

        has_existing = bool(
            self.draw_refs_step.rois
            or self.draw_digital_rois_step.rois
            or self.draw_analog_rois_step.rois
        )
        is_rescale = force or (self._applied_preset_id == preset.id)

        def do_apply() -> None:
            # 1. Alignment Reference Markers
            ref_pos = preset.get_reference_positions(img_w, img_h)
            if ref_pos:
                self.draw_refs_step.load_rois(ref_pos)

            # 2. Initial Coarse Rotation
            if preset.alignment.rotate_angle is not None and hasattr(
                self.initial_rotate_step, "angle"
            ):
                self.initial_rotate_step.angle = float(preset.alignment.rotate_angle)
                if (
                    hasattr(self.initial_rotate_step, "angle_label")
                    and self.initial_rotate_step.angle_label is not None
                ):
                    self.initial_rotate_step.angle_label.set_text(
                        f"Rotate: {int(self.initial_rotate_step.angle)}°"
                    )

            # 3. Digital and Analog Readout ROIs
            flow_split = 0
            if preset.has_secondary_group:
                flow_split = len([n for n in digital_names if n.startswith("flow")])
            dig_pos = preset.get_digital_roi_positions(
                digital_names, img_w, img_h, flow_split
            )
            self.draw_digital_rois_step.load_rois(dig_pos or [])
            ana_pos = preset.get_analog_roi_positions(analog_names, img_w, img_h)
            self.draw_analog_rois_step.load_rois(ana_pos or [])

            if (
                hasattr(self.draw_digital_rois_step, "detect_negative_sign")
                and self.draw_digital_rois_step.detect_negative_sign is not None
            ):
                self.draw_digital_rois_step.detect_negative_sign.value = any(
                    m.detect_negative_sign for m in preset.meters
                )

            # 4. Virtual Meter Configurations
            configs = preset.build_meter_configs(digital_names, analog_names, unit)
            if configs:
                self.meters_step.load_from_config(configs)

            # 5. Image Adjustments
            if preset.image_adjustments.enabled:
                if (
                    hasattr(self.adjust_step, "contrast")
                    and self.adjust_step.contrast is not None
                ):
                    self.adjust_step.contrast.value = preset.image_adjustments.contrast
                if (
                    hasattr(self.adjust_step, "gamma")
                    and self.adjust_step.gamma is not None
                ):
                    self.adjust_step.gamma.value = preset.image_adjustments.gamma
                if (
                    hasattr(self.adjust_step, "sharpness")
                    and self.adjust_step.sharpness is not None
                ):
                    self.adjust_step.sharpness.value = (
                        preset.image_adjustments.sharpness
                    )

            # 6. Leak Monitor Sensitivity
            if (
                hasattr(self.services_step, "leak_min_flow")
                and self.services_step.leak_min_flow is not None
            ):
                self.services_step.leak_min_flow.value = (
                    preset.leak_detection.recommended_min_flow_threshold
                )

            # 7. Auto-select CNN models based on preset recommendation
            if (
                preset.digital_category_preference
                and hasattr(self.draw_digital_rois_step, "cnn_file")
                and self.draw_digital_rois_step.cnn_file is not None
                and isinstance(self.draw_digital_rois_step.cnn_file.options, dict)
            ):
                best_dig_model = select_best_model(
                    self.draw_digital_rois_step.cnn_file.options,
                    preset.digital_category_preference,
                    preset.digital_preferred_filename,
                )
                if best_dig_model:
                    self.draw_digital_rois_step.cnn_file.value = best_dig_model
                if (
                    hasattr(self.draw_digital_rois_step, "cnn_type")
                    and self.draw_digital_rois_step.cnn_type is not None
                ):
                    self.draw_digital_rois_step.cnn_type.value = preset.digital_cnn_type

            if (
                preset.analog_category_preference
                and hasattr(self.draw_analog_rois_step, "cnn_file")
                and self.draw_analog_rois_step.cnn_file is not None
                and isinstance(self.draw_analog_rois_step.cnn_file.options, dict)
            ):
                best_ana_model = select_best_model(
                    self.draw_analog_rois_step.cnn_file.options,
                    preset.analog_category_preference,
                    preset.analog_preferred_filename,
                )
                if best_ana_model:
                    self.draw_analog_rois_step.cnn_file.value = best_ana_model
                if (
                    hasattr(self.draw_analog_rois_step, "cnn_type")
                    and self.draw_analog_rois_step.cnn_type is not None
                ):
                    self.draw_analog_rois_step.cnn_type.value = preset.analog_cnn_type

            # 8. Auto-select template model image if available
            if (
                preset.has_image
                and hasattr(self, "download_image_step")
                and self.download_image_step is not None
                and hasattr(self.download_image_step, "url")
                and self.download_image_step.url is not None
            ):
                model_uri = preset.model_uri
                if (
                    hasattr(self.download_image_step.url, "options")
                    and isinstance(self.download_image_step.url.options, dict)
                    and model_uri not in self.download_image_step.url.options
                ):
                    self.download_image_step.url.options[model_uri] = (
                        f"{model_uri} ({preset.label})"
                    )
                self.download_image_step.url.value = model_uri

            self._applied_preset_id = preset.id
            self._applied_preset_dims = (img_w, img_h)

            parts = []
            if ref_pos:
                parts.append(f"{len(ref_pos)} refs")
            if dig_pos:
                parts.append(f"{len(dig_pos)} digital")
            if ana_pos:
                parts.append(f"{len(ana_pos)} analog")
            details = f": {', '.join(parts)}" if parts else ""
            ui.notify(
                f"Preset '{preset.label}' applied{details}, CNN models configured.",
                type="positive",
                timeout=4000,
            )

        def on_cancel() -> None:
            if (
                self._applied_preset_id
                and self._applied_preset_id in self.meter_type_step.preset_by_id
            ):
                self.meter_type_step._select_preset(self._applied_preset_id)
            else:
                self.meter_type_step._select_preset("custom")

        if has_existing and not is_rescale:
            if self._confirm_dialog_open:
                return
            self._confirm_dialog_open = True

            def _wrapped_confirm() -> None:
                self._confirm_dialog_open = False
                do_apply()

            def _wrapped_cancel() -> None:
                self._confirm_dialog_open = False
                on_cancel()

            open_confirm_dialog(
                title="Apply Meter Type Preset?",
                subtitle="This will replace existing ROI and model configurations",
                message=(
                    f"Applying preset '{preset.label}' will replace existing ROI boxes, "
                    "CNN model selections, and meter configurations. Continue?"
                ),
                confirm_label="Apply Preset",
                confirm_icon="auto_fix_high",
                color_scheme="indigo",
                icon="auto_fix_high",
                on_confirm=lambda *_: _wrapped_confirm(),
                on_cancel=lambda *_: _wrapped_cancel(),
            )
        else:
            do_apply()

    def handle_stepper_change(self, step: str) -> None:
        prev_step = self.navigator.previous_step
        if prev_step != step and WizardNavigator.is_step_forward(step, prev_step):
            can_move, msg = self.navigator.validate_transition(
                current_step=prev_step,
                target_step=step,
                step_getter=self.get_step_by_name,
            )
            if not can_move:
                ui.notify(msg, type="warning", close_button="OK")
                if hasattr(self, "stepper") and self.stepper is not None:
                    self.stepper.value = prev_step
                return

        # Apply preset immediately when leaving Meter Type step going forward with a non-custom preset
        if (
            prev_step == NAME_METER_TYPE
            and WizardNavigator.is_step_forward(step, NAME_METER_TYPE)
            and self.meter_type_step.selected_preset_id != "custom"
        ):
            self._preset_pending = True
            self._apply_meter_type_preset()

        # If moving forward from Download Image and new image has different dimensions, re-scale ROIs
        if (
            prev_step == NAME_DOWNLOAD_IMAGE
            and WizardNavigator.is_step_forward(step, NAME_DOWNLOAD_IMAGE)
            and self._preset_pending
        ):
            self._preset_pending = False
            if self.image:
                w, h = self.get_image_dimensions()
                if self._applied_preset_dims and (w, h) != self._applied_preset_dims:
                    self._apply_meter_type_preset(force=True)

        # Fallback: if user jumps past Download Image to any step while _preset_pending
        if self._preset_pending and step not in (NAME_METER_TYPE, NAME_DOWNLOAD_IMAGE):
            self._preset_pending = False
            self._apply_meter_type_preset(force=True)

        self.navigator.handle_stepper_change(
            step=step,
            download_image_step=self.download_image_step,
            initial_rotate_step=self.initial_rotate_step,
            draw_refs_step=self.draw_refs_step,
            adjust_step=self.adjust_step,
            draw_digital_rois_step=self.draw_digital_rois_step,
            draw_analog_rois_step=self.draw_analog_rois_step,
            meters_step=self.meters_step,
            services_step=self.services_step,
            final_step=self.final_step,
            set_image_fn=self.set_image,
            set_comparison_image_fn=self.set_comparison_image,
            update_svg_fn=self.update_svg,
            gather_config_fn=self.gather_config,
            wizard_prev_btn=getattr(self, "wizard_prev_btn", None),
            wizard_step_badge=getattr(self, "wizard_step_badge", None),
            wizard_next_btn=getattr(self, "wizard_next_btn", None),
            fallback_image=self.image,
        )

    async def on_wizard_next(self) -> None:
        curr_step_name = getattr(self.stepper, "value", steps_order[0])
        curr_idx = (
            steps_order.index(curr_step_name) if curr_step_name in steps_order else 0
        )
        if curr_idx < len(steps_order) - 1:
            target_step_name = steps_order[curr_idx + 1]
            can_move, msg = self.navigator.validate_transition(
                current_step=curr_step_name,
                target_step=target_step_name,
                step_getter=self.get_step_by_name,
            )
            if not can_move:
                ui.notify(msg, type="warning", close_button="OK")
                return
        self.stepper.next()

    def show_offline_placeholder(
        self,
        message: str = "Camera Offline",
        subtext: str = "Check camera URL and click Download to retry",
        is_error: bool = True,
    ) -> None:
        stroke_color = "#ef4444" if is_error else "#6366f1"
        circle_color = "#334155" if is_error else "#1e1b4b"
        strike_line = (
            '<line x1="280" y1="160" x2="360" y2="220" '
            'stroke="#ef4444" stroke-width="3" stroke-linecap="round"/>'
            if is_error
            else ""
        )
        svg = (
            '<svg width="640" height="480" viewBox="0 0 640 480" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<rect width="100%" height="100%" fill="#1e293b"/>'
            f'<circle cx="320" cy="190" r="48" fill="{circle_color}"/>'
            '<path d="M 296 214 L 344 166 M 304 174 L 320 174 L 326 166 '
            "L 338 166 L 344 174 L 352 174 C 356 174 360 178 360 182 "
            "L 360 206 C 360 210 356 214 352 214 L 288 214 C 284 214 "
            '280 210 280 206 L 280 182 C 280 178 284 174 288 174 Z" '
            f'stroke="{stroke_color}" stroke-width="3" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
            f"{strike_line}"
            f'<text x="320" y="275" text-anchor="middle" fill="#f8fafc" '
            'font-family="system-ui, -apple-system, sans-serif" '
            f'font-size="20" font-weight="600">{message}</text>'
            f'<text x="320" y="305" text-anchor="middle" fill="#94a3b8" '
            'font-family="system-ui, -apple-system, sans-serif" '
            f'font-size="13">{subtext}</text>'
            "</svg>"
        )
        b64_svg = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        if hasattr(self, "interactive_image") and self.interactive_image is not None:
            self.interactive_image.set_source(f"data:image/svg+xml;base64,{b64_svg}")
            self.interactive_image.content = ""
        if hasattr(self, "image_details") and self.image_details is not None:
            self.image_details.text = f"Size: 640x480 ({message})"

    def _handle_clean_reset(self, create_backup: bool = True) -> None:
        try:
            curr_cfg = self.callbacks.get_config()
            if create_backup:
                try:
                    curr_cfg.create_backup(
                        ini_file=f"{curr_cfg.config_dir}/config.ini",
                        tag="Pre-Clean Reset",
                    )
                except Exception as b_err:
                    logger.warning(f"Could not create pre-clean safety backup: {b_err}")

            clean_config = Config.create_clean_default(
                config_dir=curr_cfg.config_dir,
                data_dir=curr_cfg.data_dir,
            )

            self.download_image_step.load_from_config(clean_config.image_source)
            self.initial_rotate_step.load_from_config(clean_config.alignment)
            self.draw_refs_step.load_from_config(clean_config.alignment.ref_images)
            self.adjust_step.load_from_config(clean_config)
            self.draw_digital_rois_step.load_from_config(clean_config.digital_readout)
            self.draw_analog_rois_step.load_from_config(clean_config.analog_readout)
            self.meters_step.load_from_config(clean_config.meter_configs)
            self.services_step.load_from_config(clean_config)

            # Reset all step image state
            self.image = ""
            self.processed_image = ""
            self.download_image_step.image = ""
            self.initial_rotate_step.image = ""
            self.initial_rotate_step.org_image = ""
            self.draw_refs_step.image = ""
            self.adjust_step.image = ""
            self.adjust_step.org_image = ""
            self.adjust_step.ref_images = []
            self.draw_digital_rois_step.image = ""
            self.draw_analog_rois_step.image = ""
            self.meters_step.image = ""
            self.services_step.image = ""
            self.final_step.image = ""

            # Reset ROI svg strings and visibility
            self.refs = ""
            self.digital_rois = ""
            self.analog_rois = ""
            self.refs_enabled_in_image = False
            self.digital_rois_enabled_in_image = False
            self.analog_rois_enabled_in_image = False

            self.previous_step = NAME_METER_TYPE
            if (
                hasattr(self, "interactive_image")
                and self.interactive_image is not None
            ):
                self.interactive_image.content = ""
            self.show_offline_placeholder(
                message="Ready for New Setup",
                subtext="Enter camera URL and click Download to start",
                is_error=False,
            )
            if (
                hasattr(self, "comparison_container")
                and self.comparison_container is not None
            ):
                self.comparison_container.set_visibility(False)

            if hasattr(self, "stepper") and self.stepper is not None:
                self.stepper.value = NAME_METER_TYPE
                self.update_wizard_nav(NAME_METER_TYPE)

            self._preset_pending = False
            self.meter_type_step.selected_preset_id = "custom"
            self.meter_type_step._update_ui_state()

            ui.notify("Wizard reset to clean configuration", type="positive")
        except Exception as e:
            logger.error(f"Failed to reset wizard to clean config: {e}")
            ui.notify(f"Clean reset failed: {e}", type="negative")

    def open_clean_config_dialog(self) -> None:
        open_confirm_dialog(
            title="Start Clean Configuration?",
            subtitle="Reset all steps to blank defaults",
            message=(
                "All drawn reference markers, digital/analog ROIs, custom meters, "
                "and image adjustments will be cleared. You can start calibrating "
                "your meter from scratch."
            ),
            confirm_label="Start Clean",
            confirm_icon="cleaning_services",
            color_scheme="rose",
            icon="cleaning_services",
            checkbox_label="Create safety backup before clearing",
            checkbox_default=True,
            on_confirm=lambda create_backup: self._handle_clean_reset(
                create_backup=create_backup
            ),
        )

    async def _handle_reset_from_file(self) -> None:
        try:
            config_str = self.callbacks.load_config_file()
            fresh_config = Config()
            fresh_config.load_from_string(config_str)

            self.download_image_step.load_from_config(fresh_config.image_source)
            self.initial_rotate_step.load_from_config(fresh_config.alignment)
            self.draw_refs_step.load_from_config(fresh_config.alignment.ref_images)
            self.adjust_step.load_from_config(fresh_config)
            self.draw_digital_rois_step.load_from_config(fresh_config.digital_readout)
            self.draw_analog_rois_step.load_from_config(fresh_config.analog_readout)
            self.meters_step.load_from_config(fresh_config.meter_configs)
            self.services_step.load_from_config(fresh_config)

            # Reset all step image state
            self.image = ""
            self.processed_image = ""
            self.download_image_step.image = ""
            self.initial_rotate_step.image = ""
            self.initial_rotate_step.org_image = ""
            self.draw_refs_step.image = ""
            self.adjust_step.image = ""
            self.adjust_step.org_image = ""
            self.adjust_step.ref_images = []
            self.draw_digital_rois_step.image = ""
            self.draw_analog_rois_step.image = ""
            self.meters_step.image = ""
            self.services_step.image = ""
            self.final_step.image = ""

            self.previous_step = NAME_METER_TYPE
            if (
                hasattr(self, "interactive_image")
                and self.interactive_image is not None
            ):
                self.interactive_image.content = ""
            self.show_offline_placeholder(
                message="No Image Loaded",
                subtext="Enter camera URL and click Download to start",
                is_error=False,
            )
            if (
                hasattr(self, "comparison_container")
                and self.comparison_container is not None
            ):
                self.comparison_container.set_visibility(False)

            if hasattr(self, "stepper") and self.stepper is not None:
                self.stepper.value = NAME_METER_TYPE
                self.update_wizard_nav(NAME_METER_TYPE)

            self._preset_pending = False
            self.meter_type_step.selected_preset_id = "custom"
            self.meter_type_step._update_ui_state()

            if fresh_config.image_source.url:
                await self.download_image_step.download()

            ui.notify("Wizard reset from config file", type="positive")
        except Exception as e:
            logger.error(f"Failed to reset wizard: {e}")
            ui.notify(f"Reset failed: {e}", type="negative")

    def open_reset_dialog(self) -> None:
        open_confirm_dialog(
            title="Reset Configuration Wizard?",
            subtitle="Discard unsaved changes",
            message=(
                "All wizard fields, ROIs, and adjustment parameters will be "
                "reloaded from the current config file on disk."
            ),
            confirm_label="Reset to File",
            confirm_icon="restart_alt",
            color_scheme="amber",
            icon="restart_alt",
            on_confirm=self._handle_reset_from_file,
        )

    def open_restore_backup_dialog(self) -> None:
        async def on_restore(target_name: str, target_time: str) -> None:
            try:
                self.callbacks.restore_config_backup(target_name)
                await self._handle_reset_from_file()
                ui.notify(
                    f"Wizard restored from backup {target_time}",
                    type="positive",
                )
            except Exception as err:
                ui.notify(f"Restore failed: {err}", type="negative")

        open_config_history_dialog(
            callbacks=self.callbacks,
            title="Restore Wizard from Backup",
            subtitle="Select a saved snapshot to load into the wizard",
            show_snapshot_creator=False,
            on_restore=on_restore,
            allow_diff=False,
            allow_delete=False,
            max_width="max-w-xl",
        )

    def open_model_alignment(self) -> None:
        preset = self.meter_type_step.selected_preset
        if preset is None or preset.id == "custom":
            ui.notify(
                "Please select a known meter preset in Step 1 to use model alignment",
                type="warning",
            )
            return

        img_b64 = self.image or self.download_image_step.image
        if not img_b64:
            ui.notify(
                "Please download or load a meter image first",
                type="warning",
            )
            return

        def on_alignment_applied(results: dict[str, Any]) -> None:
            if "rotation" in results and hasattr(self.initial_rotate_step, "angle"):
                self.initial_rotate_step.angle = float(results["rotation"])
                if (
                    hasattr(self.initial_rotate_step, "angle_label")
                    and self.initial_rotate_step.angle_label is not None
                ):
                    self.initial_rotate_step.angle_label.set_text(
                        f"Rotate: {int(self.initial_rotate_step.angle)}°"
                    )
            if results.get("references"):
                self.draw_refs_step.load_rois(results["references"])
            if results.get("digital"):
                self.draw_digital_rois_step.load_rois(results["digital"])
            if results.get("analog"):
                self.draw_analog_rois_step.load_rois(results["analog"])
            self.update_svg()

        open_model_alignment_dialog(
            camera_image_b64=img_b64,
            preset=preset,
            digital_names=self.meter_type_step.effective_digital_roi_names,
            analog_names=self.meter_type_step.effective_analog_roi_names,
            on_applied=on_alignment_applied,
        )

    def _init_steps(self) -> None:
        config_dir = "config"
        try:
            cfg = self.callbacks.get_config()
            if cfg and getattr(cfg, "config_dir", None):
                config_dir = cfg.config_dir
        except Exception:
            pass

        self.download_image_step = DownloadImageStep(
            name=NAME_DOWNLOAD_IMAGE,
            set_image_callback=self.set_image,
            on_error_callback=self.on_download_error,
            spinner=self.spinner,
            config_dir=config_dir,
        )
        self.meter_type_step = MeterTypeStep(
            name=NAME_METER_TYPE,
            set_image_callback=self.set_image,
            spinner=self.spinner,
            config_dir=config_dir,
            on_preset_selected=lambda p: self._apply_meter_type_preset(preset=p),
        )
        self.initial_rotate_step = InitialRotateStep(
            name=NAME_INITIAL_ROTATE,
            set_image_callback=self.set_image,
            spinner=self.spinner,
        )
        self.draw_refs_step = DrawRefsStep(
            name=NAME_DRAW_REFS,
            name_template="Ref",
            set_image_callback=self.set_image,
            set_rois_to_svg_func=self.set_refs_to_svg_func,
            show_temp_draw_in_svg_func=self.show_temp_draw_in_svg_func,
            spinner=self.spinner,
            zoom_callback=self.apply_canvas_zoom,
            get_zoom_text=self._get_current_zoom_text,
        )
        self.adjust_step = AdjustStep(
            name=NAME_ADJUST,
            set_image_callback=self.set_image,
            set_comparison_callback=self.set_comparison_image,
            spinner=self.spinner,
        )
        self.draw_digital_rois_step = DrawDigitalRoisStep(
            name=NAME_DRAW_DIGITAL_ROIS,
            name_template="digit",
            set_image_callback=self.set_image,
            set_rois_to_svg_func=self.set_digital_rois_to_svg_func,
            show_temp_draw_in_svg_func=self.show_temp_draw_in_svg_func,
            spinner=self.spinner,
            digital_models_dir=self.callbacks.get_config().digital_models_dir,
            zoom_callback=self.apply_canvas_zoom,
            get_zoom_text=self._get_current_zoom_text,
        )
        self.draw_analog_rois_step = DrawAnalogRoisStep(
            name=NAME_DRAW_ANALOG_ROIS,
            name_template="analog",
            set_image_callback=self.set_image,
            set_rois_to_svg_func=self.set_analog_rois_to_svg_func,
            show_temp_draw_in_svg_func=self.show_temp_draw_in_svg_func,
            spinner=self.spinner,
            analog_models_dir=self.callbacks.get_config().analog_models_dir,
            zoom_callback=self.apply_canvas_zoom,
            get_zoom_text=self._get_current_zoom_text,
        )
        self.adjust_step.roi_provider = lambda: (
            [
                ImagePosition(name=r.name, x=r.x, y=r.y, w=r.w, h=r.h)
                for r in self.draw_digital_rois_step.rois
                if getattr(r, "enabled", True)
            ],
            [
                ImagePosition(name=r.name, x=r.x, y=r.y, w=r.w, h=r.h)
                for r in self.draw_analog_rois_step.rois
                if getattr(r, "enabled", True)
            ],
        )
        self.initial_rotate_step.on_align_to_model = self.open_model_alignment

        self.meters_step = MeterStep(
            name=NAME_METERS,
            set_image_callback=self.set_image,
            get_digit_names_func=lambda: WizardConfigManager.get_digit_names(
                self.draw_digital_rois_step, self.draw_analog_rois_step
            ),
            spinner=self.spinner,
        )
        self.services_step = ServicesStep(
            name=NAME_SERVICES,
            set_image_callback=self.set_image,
            spinner=self.spinner,
        )
        self.final_step = FinalStep(
            name=NAME_FINAL,
            callbacks=self.callbacks,
            set_image_callback=self.set_image,
            save_refs_func=self.save_refs,
            spinner=self.spinner,
        )

    def _build_top_bar(self) -> None:
        with ui.row().classes(
            "w-full justify-between items-center mb-2 px-4 py-2 bg-slate-900/60 "
            "border border-white/10 rounded-xl shadow-md backdrop-blur-md shrink-0"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("auto_fix_high", size="md").classes("text-indigo-400")
                with ui.column().classes("gap-0"):
                    ui.label("Configuration Wizard").classes(
                        "text-lg font-bold text-slate-100 leading-tight"
                    )
                    ui.label("Interactive Calibration & Deployment Pipeline").classes(
                        "text-xs text-slate-400"
                    )
                self.spinner = ui.spinner("dots", size="md", color="indigo")
                self.spinner.visible = False
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Start Clean",
                    icon="cleaning_services",
                    on_click=self.open_clean_config_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Clear all ROIs and settings to start a new setup from scratch"
                )

                ui.button(
                    "Restore Backup",
                    icon="history",
                    on_click=self.open_restore_backup_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Select and restore a previous configuration backup"
                )

                ui.button(
                    "Reset to File",
                    icon="restart_alt",
                    on_click=self.open_reset_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Reload all wizard values from saved config file"
                )

                ui.label("10-Step Setup").classes(
                    "text-xs font-semibold text-indigo-300 bg-indigo-950/70 "
                    "border border-indigo-500/30 px-3 py-1 rounded-full shadow-inner"
                )

    def _build_canvas_panel(self, mouse_handler: Any) -> None:
        with ui.column().classes(
            "w-full h-full rounded-xl bg-slate-950/80 p-2.5 "
            "border border-white/10 shadow-2xl backdrop-blur-md "
            "gap-2.5 overflow-y-auto overflow-x-hidden min-w-0 no-wrap"
        ):
            # Original Image Card
            with ui.card().classes(
                "w-full p-2 bg-slate-900/60 border border-white/10 "
                "rounded-xl shadow-md flex flex-col gap-2 shrink-0 min-w-0"
            ):
                with ui.row().classes(
                    "w-full min-w-0 shrink-0 justify-between items-center px-1"
                ) as self.main_image_header:
                    with ui.row().classes("items-center gap-1.5 min-w-0"):
                        self.main_image_icon = ui.icon("image", size="xs").classes(
                            "text-indigo-400 shrink-0"
                        )
                        self.main_image_label = ui.label("Original Image").classes(
                            "text-xs font-semibold text-slate-300 truncate"
                        )
                    with ui.row().classes("items-center gap-1.5"):
                        with ui.row().classes(TOOLBAR_ZOOM_CONTAINER):
                            ui.icon("zoom_in", size="13px").classes(
                                "text-cyan-400 shrink-0 ml-0.5"
                            )
                            ui.button(
                                icon="remove",
                                on_click=lambda: self.apply_canvas_zoom(delta=-0.25),
                            ).props(
                                "flat dense round size=xs aria-label='Zoom Out' data-testid='zoom-out'"
                            ).classes(
                                "text-slate-300 hover:text-white"
                            ).tooltip(
                                "Zoom Out Canvas (-)"
                            )
                            self.zoom_label = ui.label("Fit").classes(TEXT_ZOOM_LABEL)
                            ui.button(
                                icon="add",
                                on_click=lambda: self.apply_canvas_zoom(delta=0.25),
                            ).props(
                                "flat dense round size=xs aria-label='Zoom In' data-testid='zoom-in'"
                            ).classes(
                                "text-slate-300 hover:text-white"
                            ).tooltip(
                                "Zoom In Canvas (+)"
                            )
                            ui.button(
                                "1:1",
                                on_click=lambda: self.apply_canvas_zoom(1.0),
                            ).props("flat dense size=xs").classes(
                                "text-[10px] font-mono text-slate-300 hover:text-cyan-300 px-1 font-semibold"
                            ).tooltip(
                                "100% Native Size"
                            )
                            ui.button(
                                icon="fit_screen",
                                on_click=lambda: self.apply_canvas_zoom(fit=True),
                            ).props("flat dense round size=xs").classes(
                                "text-slate-300 hover:text-white"
                            ).tooltip(
                                "Fit to Window"
                            )

                        self.main_image_tag = ui.label("ORIGINAL").classes(
                            "text-[10px] font-mono font-bold text-cyan-400 "
                            "px-2 py-0.5 rounded-md bg-cyan-950/60 "
                            "border border-cyan-500/30 shrink-0"
                        )
                        self.main_image_tag.set_visibility(False)

                with ui.element("div").classes(
                    "w-full max-h-[640px] overflow-auto rounded-lg bg-slate-950 flex items-start justify-center relative border border-white/5"
                ) as self.canvas_wrapper:
                    self.interactive_image = ui.interactive_image(
                        size=(640, 480),
                        on_mouse=mouse_handler,
                        events=["mousedown", "mouseup", "mousemove"],
                        cross=True,
                    ).classes(
                        "w-full max-w-full min-w-0 shrink-0 "
                        "bg-slate-950 shadow-inner interactive-image-canvas transition-all"
                    )

                with ui.row().classes(
                    "w-full min-w-0 shrink-0 justify-between items-center "
                    "px-2.5 py-1 rounded-lg bg-slate-950/80 border "
                    "border-white/5 text-xs text-slate-400 gap-2"
                ):
                    self.image_details = ui.label("").classes(
                        "font-mono text-cyan-400 font-semibold truncate"
                    )
                    with (
                        ui.element("div")
                        .props('id="roi-move-indicator"')
                        .classes(
                            "items-center gap-1 px-2 py-0.5 rounded bg-amber-500/20 "
                            "border border-amber-500/40 text-[10px] font-mono font-bold "
                            "text-amber-300 animate-pulse shrink-0"
                        )
                    ):
                        ui.icon("open_with", size="12px").classes("text-amber-400")
                        ui.label("MOVE MODE")
                    self.mouse_position = ui.label("").classes(
                        "font-mono text-slate-400 truncate"
                    )
                    self.selected_position = ui.label("").classes(
                        "font-mono text-emerald-400 font-bold truncate"
                    )
                self.show_offline_placeholder(
                    "No Image Loaded",
                    "Enter camera URL and click Download to start",
                    is_error=False,
                )

            # Adjusted Image Preview Card (under the status bar)
            with ui.card().classes(
                "w-full p-2 bg-slate-900/60 border border-white/10 "
                "rounded-xl shadow-md flex flex-col gap-2 shrink-0 min-w-0"
            ) as self.comparison_container:
                with ui.row().classes(
                    "w-full min-w-0 shrink-0 items-center justify-between px-1"
                ):
                    with ui.row().classes("items-center gap-1.5 min-w-0"):
                        ui.icon("auto_fix_high", size="xs").classes(
                            "text-emerald-400 shrink-0"
                        )
                        ui.label("Adjusted Image").classes(
                            "text-xs font-semibold text-slate-300 truncate"
                        )
                    ui.label("ADJUSTED").classes(
                        "text-[10px] font-mono font-bold text-emerald-400 "
                        "px-2 py-0.5 rounded-md bg-emerald-950/60 "
                        "border border-emerald-500/30 shrink-0"
                    )

                self.comparison_image = (
                    ui.image("")
                    .props('fit=contain no-spinner ratio="1.3333"')
                    .classes(
                        "w-full max-w-full min-w-0 shrink-0 aspect-[4/3] "
                        "min-h-[120px] rounded-lg bg-slate-950 shadow-inner"
                    )
                )
            self.comparison_container.set_visibility(False)

    async def _build_stepper(self, handle_stepper_change: Any) -> None:
        with (
            ui.stepper(on_value_change=lambda x: handle_stepper_change(x.value))
            .props("vertical")
            .classes(
                "w-full rounded-2xl shadow-xl bg-slate-900/40 " "border border-white/5"
            ) as stepper
        ):
            self.stepper = stepper
            await self.meter_type_step.show(stepper, first_step=True)
            await self.download_image_step.show(stepper)
            await self.initial_rotate_step.show(stepper)
            await self.draw_refs_step.show(stepper)
            await self.adjust_step.show(stepper)
            await self.draw_digital_rois_step.show(stepper)
            await self.draw_analog_rois_step.show(stepper)
            await self.meters_step.show(stepper)
            await self.services_step.show(stepper)
            await self.final_step.show(stepper, last_step=True)

    def _build_docked_nav(self, on_wizard_next: Any) -> None:
        with ui.row().classes(
            "w-full justify-between items-center px-4 py-2 mt-1.5 "
            "bg-slate-900/90 border border-white/10 rounded-xl "
            "shadow-2xl backdrop-blur-md shrink-0"
        ):
            with ui.row().classes("items-center gap-2"):
                self.wizard_prev_btn = (
                    ui.button(
                        "Back",
                        icon="arrow_back",
                        on_click=lambda: self.stepper.previous(),
                    )
                    .props("flat no-caps color=grey text-color=white")
                    .classes(
                        "px-3.5 py-1.5 rounded-lg text-sm font-medium "
                        "hover:bg-white/10 transition-colors"
                    )
                )
                self.wizard_prev_btn.visible = False

                self.wizard_step_badge = ui.label(
                    f"Step 1 of {len(steps_order)}: {steps_order[0]}"
                ).classes(
                    "text-xs font-semibold text-slate-300 font-mono "
                    "bg-slate-950/70 border border-white/10 px-2.5 "
                    "py-1 rounded-lg shadow-inner"
                )

            self.wizard_next_btn = (
                ui.button(
                    "Continue",
                    on_click=on_wizard_next,
                )
                .props("unelevated no-caps icon-right=arrow_forward")
                .classes(
                    "px-4 py-1.5 rounded-lg text-sm font-semibold "
                    "bg-blue-600 hover:bg-blue-500 "
                    "text-white shadow-md shadow-blue-950/40 "
                    "transition-colors"
                )
            )

    async def show(self) -> None:
        last_mouse_pos_update = 0.0

        def mouse_handler(e: events.MouseEventArguments) -> None:
            nonlocal last_mouse_pos_update
            if e.type == "mousemove":
                now = time.monotonic()
                if now - last_mouse_pos_update >= 0.040:
                    last_mouse_pos_update = now
                    self.mouse_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"
            elif e.type == "mousedown":
                self.selected_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"

            active_val = getattr(self.stepper, "value", "")
            if active_val == NAME_DRAW_REFS:
                self.draw_refs_step.mouse_event(e)
            elif active_val == NAME_DRAW_DIGITAL_ROIS:
                self.draw_digital_rois_step.mouse_event(e)
            elif active_val == NAME_DRAW_ANALOG_ROIS:
                self.draw_analog_rois_step.mouse_event(e)

        def handle_page_keyboard(e: events.KeyEventArguments) -> None:
            if not e.action.keydown:
                return
            shift = bool(getattr(e.modifiers, "shift", False))
            ctrl = bool(
                getattr(e.modifiers, "ctrl", False)
                or getattr(e.modifiers, "meta", False)
            )

            # Global canvas zoom shortcuts with Ctrl / Cmd key
            if ctrl and e.key in ("+", "="):
                self.apply_canvas_zoom(delta=0.25)
                return
            if ctrl and e.key in ("-", "_"):
                self.apply_canvas_zoom(delta=-0.25)
                return
            if ctrl and e.key in ("0", ")"):
                self.apply_canvas_zoom(fit=True)
                return

            active_step_name = getattr(self.stepper, "value", "")
            active_step = self.get_step_by_name(active_step_name)
            if hasattr(
                active_step, "handle_keyboard_event"
            ) and active_step.handle_keyboard_event(e.key, shift=shift, ctrl=ctrl):
                self.is_dirty = True

        ui.keyboard(on_key=handle_page_keyboard)

        self._build_top_bar()

        self._init_steps()

        with (
            ui.splitter(value=42, limits=(20, 80))
            .classes("w-full flex-1 min-h-0")
            .props(
                'separator-class="bg-white/10 hover:bg-indigo-500/70 '
                'transition-all duration-200 cursor-col-resize" '
                'separator-style="width: 2px; margin: 0 8px;"'
            ) as splitter
        ):
            with (
                splitter.add_slot("separator"),
                ui.element("div")
                .classes(
                    "w-2.5 h-8 -ml-[4px] rounded-full bg-slate-800/90 border "
                    "border-white/20 flex flex-col items-center justify-center "
                    "gap-0.5 hover:bg-indigo-600 hover:border-indigo-400 "
                    "transition-all duration-150 shadow-md cursor-col-resize"
                )
                .tooltip("Resize panels"),
            ):
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")

            with splitter.before:
                self._build_canvas_panel(mouse_handler)

            with (
                splitter.after,
                ui.element("div").classes(
                    "w-full h-full flex flex-col justify-between min-h-0 overflow-hidden pr-1"
                ),
            ):
                with ui.element("div").classes(
                    "w-full flex-1 min-h-0 overflow-y-auto pr-1"
                ):
                    await self._build_stepper(self.handle_stepper_change)
                self._build_docked_nav(self.on_wizard_next)

        self.update_wizard_nav(self.stepper.value or steps_order[0])

        for img in self.callbacks.get_config().alignment.ref_images:
            if img.w == 0 or img.h == 0:
                img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

        config = self.callbacks.get_config()

        self.download_image_step.load_from_config(config.image_source)
        self.initial_rotate_step.load_from_config(config.alignment)
        self.draw_refs_step.load_from_config(config.alignment.ref_images)
        self.adjust_step.load_from_config(config)
        self.draw_digital_rois_step.load_from_config(config.digital_readout)
        self.draw_analog_rois_step.load_from_config(config.analog_readout)
        self.meters_step.load_from_config(config.meter_configs)
        self.services_step.load_from_config(config)

        if config.image_source.url:
            await self.download_image_step.download()
