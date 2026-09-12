import base64
import logging
import os
from hashlib import sha256
from pathlib import Path

from nicegui import events, ui

import utils.image as ImageUtils
from callbacks import Callbacks
from configuration import CNNParams, Config
from data_classes import ImagePosition, MeterConfig, RefImage

from .step_adjust import AdjustStep
from .step_download import DownloadImageStep
from .step_draw_analog_rois import DrawAnalogRoisStep
from .step_draw_digital_rois import DrawDigitalRoisStep
from .step_draw_refs import DrawRefsStep
from .step_final import FinalStep
from .step_initial_rotate import InitialRotateStep
from .step_meters import MeterStep
from .step_services import ServicesStep

logger = logging.getLogger(__name__)

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


class SetupPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks

        self.interactive_image: ui.interactive_image
        self.image_details: ui.label
        self.mouse_position: ui.label
        self.selected_position: ui.label
        self.spinner: ui.spinner

        self.download_image_step: DownloadImageStep
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

        self.previous_step: str = NAME_DOWNLOAD_IMAGE

        self.config: Config
        self.image: str = ""  # base64 str
        self.refs = ""
        self.refs_enabled_in_image = False
        self.digital_rois = ""
        self.digital_rois_enabled_in_image = False
        self.analog_rois = ""
        self.analog_rois_enabled_in_image = False

    async def show(self) -> None:

        def update_svg(draw: str = "") -> None:
            self.interactive_image.content = f"""
                {svg_grid}
                <rect width="100%" height="100%" fill="url(#grid)" />
                {self.refs if self.refs_enabled_in_image else ""}
                {self.digital_rois if self.digital_rois_enabled_in_image else ""}
                {self.analog_rois if self.analog_rois_enabled_in_image else ""}
                {draw if draw is not None else ""}
                """

        def set_image(base64_str: str) -> None:
            print_image_hash("set_image", base64_str)
            if base64_str is None or base64_str == "":
                return
            self.image = base64_str
            w, h = ImageUtils.image_size(
                ImageUtils.convert_base64_str_to_image(base64_str)
            )
            self.image_details.text = f"Size: {w}x{h}"
            self.interactive_image.set_source(f"data:image/png;base64,{base64_str}")
            self.interactive_image.update()
            update_svg()

        def mouse_handler(e: events.MouseEventArguments) -> None:
            if e.type == "mousemove":
                self.mouse_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"
            elif e.type == "mousedown" and e.alt:
                ui.notify("Ctrl key down with move")
            elif e.type == "mousedown":
                self.selected_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"

            if stepper.value == NAME_DRAW_REFS:
                self.draw_refs_step.mouse_event(e)
            elif stepper.value == NAME_DRAW_DIGITAL_ROIS:
                self.draw_digital_rois_step.mouse_event(e)
            elif stepper.value == NAME_DRAW_ANALOG_ROIS:
                self.draw_analog_rois_step.mouse_event(e)

        def get_refs_from_config() -> str:
            style = "stroke-width:3;stroke:red;fill-opacity:0;stroke-opacity:0.9"
            content = ""
            for ref in self.callbacks.get_config().alignment.ref_images:
                content += (
                    f'<rect x="{ref.x}" y="{ref.y}" width="{ref.w}" '
                    f'height="{ref.h}" style="{style}" />'
                )
            return content

        def print_image_hash(text: str, image: str) -> None:
            if image is None or image == "":
                logger.debug(f"{text}, hash: empty")
            else:
                data = image.encode("utf-8")
                logger.debug(f"{text}, hash: {sha256(data).hexdigest()}")

        def get_image() -> str:
            print_image_hash("get_image", self.image)
            return self.image

        def set_refs_to_svg_func(refs: str) -> None:
            self.refs = refs
            update_svg()

        def set_digital_rois_to_svg_func(rois: str) -> None:
            self.digital_rois = rois
            update_svg()

        def set_analog_rois_to_svg_func(rois: str) -> None:
            self.analog_rois = rois
            update_svg()

        def show_temp_draw_in_svg_func(draw: str) -> None:
            update_svg(draw)

        def gather_config() -> None:
            config = Config()
            orig_config = self.callbacks.get_config()
            config.log_level = orig_config.log_level
            config.config_dir = orig_config.config_dir
            config.digital_models_dir = orig_config.digital_models_dir
            config.analog_models_dir = orig_config.analog_models_dir
            config.previous_value_file = orig_config.previous_value_file

            config.image_source.url = self.download_image_step.url.value
            config.image_source.timeout = int(
                self.download_image_step.timeout.value or 30
            )
            config.image_source.min_size = int(
                self.download_image_step.minsize.value or 10000
            )
            config.crop.enabled = self.adjust_step.crop_enabled.value
            config.crop.x = int(self.adjust_step.crop_x.value or 0)
            config.crop.y = int(self.adjust_step.crop_y.value or 0)
            config.crop.w = int(self.adjust_step.crop_w.value or 0)
            config.crop.h = int(self.adjust_step.crop_h.value or 0)
            config.resize.enabled = self.adjust_step.resize_enabled.value
            config.resize.w = int(self.adjust_step.resize_w.value or 0)
            config.resize.h = int(self.adjust_step.resize_h.value or 0)
            config.image_processing.enabled = self.adjust_step.adjust_enabled.value
            config.image_processing.contrast = float(
                self.adjust_step.adjust_contrast.value or 1.0
            )
            config.image_processing.brightness = float(
                self.adjust_step.adjust_brightness.value or 1.0
            )
            config.image_processing.sharpness = float(
                self.adjust_step.adjust_sharpness.value or 1.0
            )
            config.image_processing.color = float(
                self.adjust_step.adjust_color.value or 1.0
            )
            config.image_processing.grayscale = self.adjust_step.grayscale_enabled.value
            config.image_processing.autocontrast.enabled = (
                self.adjust_step.autocontrast_enabled.value
            )
            config.image_processing.autocontrast.cutoff_low = float(
                self.adjust_step.autocontrast_cutoff_low.value or 2.0
            )
            config.image_processing.autocontrast.cutoff_high = float(
                self.adjust_step.autocontrast_cutoff_high.value or 45.0
            )
            config.image_processing.autocontrast_cut_images.enabled = (
                self.adjust_step.autocontrast_cut_images_enabled.value
            )
            config.image_processing.autocontrast_cut_images.cutoff_low = float(
                self.adjust_step.autocontrast_cut_images_cutoff_low.value or 2.0
            )
            config.image_processing.autocontrast_cut_images.cutoff_high = float(
                self.adjust_step.autocontrast_cut_images_cutoff_high.value or 45.0
            )

            # Glare suppression
            config.image_processing.glare_suppression.enabled = (
                self.adjust_step.glare_enabled.value
            )
            config.image_processing.glare_suppression.mode = str(
                self.adjust_step.glare_mode.value or "clahe"
            )
            config.image_processing.glare_suppression.inpaint_threshold = int(
                self.adjust_step.glare_inpaint_threshold.value or 230
            )
            config.image_processing.glare_suppression.inpaint_radius = int(
                self.adjust_step.glare_inpaint_radius.value or 3
            )
            config.image_processing.glare_suppression.clahe_clip_limit = float(
                self.adjust_step.glare_clahe_clip_limit.value or 2.0
            )
            config.image_processing.glare_suppression.clahe_grid_size = int(
                self.adjust_step.glare_clahe_grid_size.value or 8
            )
            config.image_processing.glare_suppression.apply_to_cut_images = (
                self.adjust_step.glare_apply_to_cut_images.value
            )

            config.alignment.rotate_angle = float(self.initial_rotate_step.angle or 0.0)
            config.alignment.post_rotate_angle = float(
                self.adjust_step.rotate_angle.value or 0.0
            )

            for roi in self.draw_refs_step.rois:
                config_dir = "${ConfigDir}"
                config.alignment.ref_images.append(
                    RefImage(
                        name=roi.name,
                        x=roi.x,
                        y=roi.y,
                        w=roi.w,
                        h=roi.h,
                        file_name=f"{config_dir}/ref_{roi.name}_x{roi.x}_y{roi.y}.jpg",
                    )
                )

            def _resolve_model_path(
                cnn_select: ui.select | None,
                models_dir: str,
                placeholder_var: str,
            ) -> str:
                if cnn_select is None or not cnn_select.value:
                    return ""
                val = str(cnn_select.value).strip()
                if val.startswith("${"):
                    parts = [p.strip() for p in val.split("/")]
                    return "/".join(parts)
                try:
                    p = Path(val)
                    if models_dir:
                        md = Path(models_dir)
                        if p.is_relative_to(md):
                            rel = p.relative_to(md).as_posix()
                            return f"{placeholder_var}/{rel}"
                        if p.resolve().is_relative_to(md.resolve()):
                            rel = p.resolve().relative_to(md.resolve()).as_posix()
                            return f"{placeholder_var}/{rel}"
                except Exception:
                    pass
                parts = [part.strip() for part in val.split("/") if part.strip()]
                clean_rel = "/".join(parts)
                return f"{placeholder_var}/{clean_rel}" if clean_rel else ""

            digital_model_file = _resolve_model_path(
                self.draw_digital_rois_step.cnn_file,
                self.draw_digital_rois_step.digital_models_dir,
                "${DigitalModelsDir}",
            )
            digital_cut_images = []
            for roi in self.draw_digital_rois_step.rois:
                digital_cut_images.append(
                    ImagePosition(
                        name=roi.name,
                        x=roi.x,
                        y=roi.y,
                        w=roi.w,
                        h=roi.h,
                    )
                )
            digital_model_val = (
                str(self.draw_digital_rois_step.cnn_type.value or "auto")
                if self.draw_digital_rois_step.cnn_type is not None
                else "auto"
            )
            config.digital_readout = CNNParams(
                enabled=len(digital_cut_images) > 0,
                model=digital_model_val,
                model_file=digital_model_file,
                cut_images=digital_cut_images,
            )

            analog_model_file = _resolve_model_path(
                self.draw_analog_rois_step.cnn_file,
                self.draw_analog_rois_step.analog_models_dir,
                "${AnalogModelsDir}",
            )
            analog_cut_images = []
            for roi in self.draw_analog_rois_step.rois:
                analog_cut_images.append(
                    ImagePosition(
                        name=roi.name,
                        x=roi.x,
                        y=roi.y,
                        w=roi.w,
                        h=roi.h,
                    )
                )
            analog_model_val = (
                str(self.draw_analog_rois_step.cnn_type.value or "auto")
                if self.draw_analog_rois_step.cnn_type is not None
                else "auto"
            )
            config.analog_readout = CNNParams(
                enabled=len(analog_cut_images) > 0,
                model=analog_model_val,
                model_file=analog_model_file,
                cut_images=analog_cut_images,
            )
            meters = []
            for meter in self.meters_step.meter_params:
                meters.append(
                    MeterConfig(
                        name=meter.name,
                        format=meter.value,
                        consistency_enabled=meter.consistency_enabled,
                        allow_negative_rates=meter.allow_negative_rates,
                        max_rate_value=meter.max_rate_value,
                        use_previous_value=meter.use_previous_value,
                        pre_value_from_file_max_age=meter.prevalue_from_file_max_age,
                        use_extended_resolution=meter.use_extended_resolution,
                        unit=meter.unit,
                    )
                )
            config.meter_configs = meters

            # Apply services (Poller, MQTT, History, DataDir, MinConfidence)
            self.services_step.apply_to_config(config)

            self.config = config

        def save_refs() -> None:
            config_dir = self.callbacks.get_config().config_dir
            ref_source_b64 = (
                self.draw_refs_step.get_image()
                or self.initial_rotate_step.get_image()
                or self.image
            )
            if not ref_source_b64:
                return
            image = ImageUtils.convert_base64_str_to_image(ref_source_b64)
            for roi in self.draw_refs_step.rois:
                ref_img = ImageUtils.cut_image(
                    image,
                    ImagePosition(name=roi.name, x=roi.x, y=roi.y, w=roi.w, h=roi.h),
                )
                ImageUtils.save_image(
                    ref_img, f"{config_dir}/ref_{roi.name}_x{roi.x}_y{roi.y}.jpg"
                )

        def get_digit_names() -> list[str]:
            rois: list[str] = []
            for roi in self.draw_digital_rois_step.rois:
                rois.append(roi.name)
            for roi in self.draw_analog_rois_step.rois:
                rois.append(roi.name)
            return rois

        def get_image_by_step_name(name: str) -> str:
            if name == NAME_DOWNLOAD_IMAGE:
                return self.download_image_step.get_image()
            elif name == NAME_INITIAL_ROTATE:
                return self.initial_rotate_step.get_image()
            elif name == NAME_DRAW_REFS:
                return self.draw_refs_step.get_image()
            elif name == NAME_ADJUST:
                return self.adjust_step.get_image()
            elif name == NAME_DRAW_DIGITAL_ROIS:
                return self.draw_digital_rois_step.get_image()
            elif name == NAME_DRAW_ANALOG_ROIS:
                return self.draw_analog_rois_step.get_image()
            elif name == NAME_METERS:
                return self.meters_step.get_image()
            elif name == NAME_SERVICES:
                return self.services_step.get_image()
            elif name == NAME_FINAL:
                return self.final_step.get_image()
            return ""

        def get_source_image_for_step(step_name: str) -> str:
            raw_img = self.download_image_step.get_image() or self.image
            if step_name in (NAME_DOWNLOAD_IMAGE, NAME_INITIAL_ROTATE):
                return raw_img

            rotated_img = self.initial_rotate_step.get_image() or raw_img
            if step_name in (NAME_DRAW_REFS, NAME_ADJUST):
                return rotated_img

            adjusted_img = self.adjust_step.get_image() or rotated_img
            return adjusted_img

        def set_image_by_step_name(name: str, image: str) -> None:
            if not image:
                return
            if name == NAME_INITIAL_ROTATE:
                self.initial_rotate_step.update_image(image)
            elif name == NAME_DRAW_REFS:
                self.draw_refs_step.update_image(image)
            elif name == NAME_ADJUST:
                self.adjust_step.update_image(image)
            elif name == NAME_DRAW_DIGITAL_ROIS:
                self.draw_digital_rois_step.update_image(
                    image,
                    self.adjust_step.autocontrast_cut_images_enabled.value,
                    self.adjust_step.autocontrast_cut_images_cutoff_low.value,
                    self.adjust_step.autocontrast_cut_images_cutoff_high.value,
                    glare_suppression=(
                        self.adjust_step.glare_enabled.value
                        and self.adjust_step.glare_apply_to_cut_images.value
                    ),
                    glare_mode=self.adjust_step.glare_mode.value or "clahe",
                    glare_inpaint_threshold=int(
                        self.adjust_step.glare_inpaint_threshold.value or 230
                    ),
                    glare_inpaint_radius=int(
                        self.adjust_step.glare_inpaint_radius.value or 3
                    ),
                    glare_clahe_clip_limit=float(
                        self.adjust_step.glare_clahe_clip_limit.value or 2.0
                    ),
                    glare_clahe_grid_size=int(
                        self.adjust_step.glare_clahe_grid_size.value or 8
                    ),
                )
            elif name == NAME_DRAW_ANALOG_ROIS:
                self.draw_analog_rois_step.update_image(
                    image,
                    self.adjust_step.autocontrast_cut_images_enabled.value,
                    self.adjust_step.autocontrast_cut_images_cutoff_low.value,
                    self.adjust_step.autocontrast_cut_images_cutoff_high.value,
                    glare_suppression=(
                        self.adjust_step.glare_enabled.value
                        and self.adjust_step.glare_apply_to_cut_images.value
                    ),
                    glare_mode=self.adjust_step.glare_mode.value or "clahe",
                    glare_inpaint_threshold=int(
                        self.adjust_step.glare_inpaint_threshold.value or 230
                    ),
                    glare_inpaint_radius=int(
                        self.adjust_step.glare_inpaint_radius.value or 3
                    ),
                    glare_clahe_clip_limit=float(
                        self.adjust_step.glare_clahe_clip_limit.value or 2.0
                    ),
                    glare_clahe_grid_size=int(
                        self.adjust_step.glare_clahe_grid_size.value or 8
                    ),
                )
            elif name == NAME_METERS:
                self.meters_step.update_image(image)
            elif name == NAME_SERVICES:
                self.services_step.update_image(image)
            elif name == NAME_FINAL:
                self.final_step.update_image(image)

        def is_step_forward(new_step: str, previous_step: str) -> bool:
            if previous_step == "" or previous_step not in steps_order:
                return True
            if new_step not in steps_order:
                return False
            return steps_order.index(new_step) > steps_order.index(previous_step)

        def handle_stepper_change(step: str) -> None:
            logger.debug(f"Step: {self.previous_step} -> {step}")

            # Update ROI overlay visibility flags before updating any step images
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
                for roi in self.draw_refs_step.rois:
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
                self.adjust_step.ref_images = ref_images

            # Update step's image from its pipeline predecessor
            src_img = get_source_image_for_step(step)
            set_image_by_step_name(step, src_img)

            if step == NAME_ADJUST:
                self.adjust_step._update_preview_canvas()
            else:
                current_img = get_image_by_step_name(step) or src_img
                set_image(current_img)
                set_comparison_image("")

            if step == NAME_METERS:
                self.meters_step.refresh_digit_names()

            if step == NAME_FINAL:
                gather_config()
                self.final_step.set_config(self.config)
            self.previous_step = step
            update_wizard_nav(step)

        def set_comparison_image(base64_str: str = "") -> None:
            if (
                not hasattr(self, "comparison_container")
                or self.comparison_container is None
            ):
                return
            if base64_str:
                self.comparison_image.set_source(f"data:image/jpeg;base64,{base64_str}")
                self.comparison_container.set_visibility(True)

                if (
                    hasattr(self, "main_image_header")
                    and self.main_image_header is not None
                ):
                    self.main_image_header.set_visibility(True)
                    self.main_image_label.text = "Original Image"
                    self.main_image_tag.text = "ORIGINAL"
            else:
                self.comparison_container.set_visibility(False)
                if (
                    hasattr(self, "main_image_header")
                    and self.main_image_header is not None
                ):
                    if (
                        hasattr(self, "stepper")
                        and getattr(self.stepper, "value", "") == NAME_ADJUST
                    ):
                        self.main_image_header.set_visibility(True)
                        self.main_image_label.text = "Adjusted Image Preview"
                        self.main_image_tag.text = "ADJUSTED"
                    else:
                        self.main_image_header.set_visibility(False)

        def update_wizard_nav(current_step: str) -> None:
            if not hasattr(self, "wizard_prev_btn") or self.wizard_prev_btn is None:
                return
            idx = steps_order.index(current_step) if current_step in steps_order else 0
            total = len(steps_order)

            # Update Back button visibility
            self.wizard_prev_btn.set_visibility(idx > 0)

            # Update Step Badge
            self.wizard_step_badge.text = f"Step {idx + 1} of {total}: {current_step}"

            # Update Next button visibility & styling
            if idx == total - 1:
                self.wizard_next_btn.set_visibility(False)
            else:
                self.wizard_next_btn.set_visibility(True)
                self.wizard_next_btn.text = "Continue"
                self.wizard_next_btn.props("icon-right=arrow_forward")
                self.wizard_next_btn.classes(
                    "px-5 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r "
                    "from-blue-600 to-cyan-600 hover:from-blue-500 "
                    "hover:to-cyan-500 text-white shadow-lg "
                    "shadow-cyan-950/40 transition-all",
                    remove="from-emerald-600 to-teal-600 hover:from-emerald-500 "
                    "hover:to-teal-500 shadow-emerald-950/40",
                )

        async def on_wizard_next() -> None:
            self.stepper.next()

        def show_offline_placeholder(
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
            self.interactive_image.set_source(f"data:image/svg+xml;base64,{b64_svg}")
            self.interactive_image.content = ""
            if hasattr(self, "image_details") and self.image_details is not None:
                self.image_details.text = f"Size: 640x480 ({message})"

        def on_download_error(err_msg: str = "") -> None:
            show_offline_placeholder(
                message="Camera Offline / Unreachable",
                subtext="Check camera URL and click Download to retry",
                is_error=True,
            )

        async def start_clean_config(create_backup: bool = True) -> None:
            try:
                if create_backup:
                    try:
                        curr_cfg = self.callbacks.get_config()
                        curr_cfg.create_backup(
                            ini_file=f"{curr_cfg.config_dir}/config.ini",
                            tag="Pre-Clean Reset",
                        )
                    except Exception as b_err:
                        logger.warning(
                            f"Could not create pre-clean safety backup: {b_err}"
                        )

                curr_cfg = self.callbacks.get_config()
                clean_config = Config.create_clean_default(
                    config_dir=curr_cfg.config_dir,
                    data_dir=curr_cfg.data_dir,
                )

                self.download_image_step.load_from_config(clean_config.image_source)
                self.initial_rotate_step.load_from_config(clean_config.alignment)
                self.draw_refs_step.load_from_config(clean_config.alignment.ref_images)
                self.adjust_step.load_from_config(clean_config)
                self.draw_digital_rois_step.load_from_config(
                    clean_config.digital_readout
                )
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

                self.previous_step = NAME_DOWNLOAD_IMAGE
                self.interactive_image.content = ""
                show_offline_placeholder(
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
                    self.stepper.value = NAME_DOWNLOAD_IMAGE
                    update_wizard_nav(NAME_DOWNLOAD_IMAGE)

                ui.notify("Wizard reset to clean configuration", type="positive")
            except Exception as e:
                logger.error(f"Failed to reset wizard to clean config: {e}")
                ui.notify(f"Clean reset failed: {e}", type="negative")

        def open_clean_config_dialog() -> None:
            with (
                ui.dialog() as clean_dialog,
                ui.card().classes(
                    "bg-slate-900 border border-white/10 rounded-2xl p-5 "
                    "max-w-md w-full gap-4"
                ),
            ):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-rose-500/20 "
                        "border border-rose-500/30 flex items-center "
                        "justify-center text-rose-400"
                    ):
                        ui.icon("cleaning_services", size="md")
                    with ui.column().classes("gap-0"):
                        ui.label("Start Clean Configuration?").classes(
                            "text-base font-bold text-slate-100"
                        )
                        ui.label("Reset all steps to blank defaults").classes(
                            "text-xs text-slate-400"
                        )
                ui.label(
                    "All drawn reference markers, digital/analog ROIs, custom meters, "
                    "and image adjustments will be cleared. You can start calibrating "
                    "your meter from scratch."
                ).classes("text-sm text-slate-300 leading-relaxed")

                backup_checkbox = ui.checkbox(
                    "Create safety backup before clearing",
                    value=True,
                ).classes("text-xs text-slate-300")

                with ui.row().classes("w-full justify-end items-center gap-2 mt-2"):
                    ui.button("Cancel", on_click=clean_dialog.close).props(
                        "flat dense"
                    ).classes("text-slate-300 px-3")

                    async def on_confirm():
                        clean_dialog.close()
                        await start_clean_config(create_backup=backup_checkbox.value)

                    ui.button(
                        "Start Clean",
                        icon="cleaning_services",
                        on_click=on_confirm,
                    ).props("unelevated dense").classes(
                        "bg-gradient-to-r from-rose-600 to-amber-600 "
                        "hover:from-rose-500 hover:to-amber-500 text-white "
                        "font-medium px-4 shadow-md"
                    )
            clean_dialog.open()

        async def reset_from_config_file() -> None:
            try:
                config_str = self.callbacks.load_config_file()
                fresh_config = Config()
                fresh_config.load_from_string(config_str)

                for img in fresh_config.alignment.ref_images:
                    if img.w == 0 or img.h == 0:
                        img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

                self.download_image_step.load_from_config(fresh_config.image_source)
                self.initial_rotate_step.load_from_config(fresh_config.alignment)
                self.draw_refs_step.load_from_config(fresh_config.alignment.ref_images)
                self.adjust_step.load_from_config(fresh_config)
                self.draw_digital_rois_step.load_from_config(
                    fresh_config.digital_readout
                )
                self.draw_analog_rois_step.load_from_config(fresh_config.analog_readout)
                self.meters_step.load_from_config(fresh_config.meter_configs)
                self.services_step.load_from_config(fresh_config)

                self.previous_step = NAME_DOWNLOAD_IMAGE
                if hasattr(self, "stepper") and self.stepper is not None:
                    self.stepper.value = NAME_DOWNLOAD_IMAGE

                if fresh_config.image_source.url:
                    await self.download_image_step.download()

                ui.notify("Wizard reset from config file", type="positive")
            except Exception as e:
                logger.error(f"Failed to reset wizard: {e}")
                ui.notify(f"Reset failed: {e}", type="negative")

        def open_reset_dialog() -> None:
            with (
                ui.dialog() as reset_dialog,
                ui.card().classes(
                    "bg-slate-900 border border-white/10 rounded-2xl p-5 "
                    "max-w-md w-full gap-4"
                ),
            ):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-amber-500/20 "
                        "border border-amber-500/30 flex items-center "
                        "justify-center text-amber-400"
                    ):
                        ui.icon("restart_alt", size="md")
                    with ui.column().classes("gap-0"):
                        ui.label("Reset Configuration Wizard?").classes(
                            "text-base font-bold text-slate-100"
                        )
                        ui.label("Discard unsaved changes").classes(
                            "text-xs text-slate-400"
                        )
                ui.label(
                    "All wizard fields, ROIs, and adjustment parameters will be "
                    "reloaded from the current config file on disk."
                ).classes("text-sm text-slate-300 leading-relaxed")
                with ui.row().classes("w-full justify-end items-center gap-2 mt-2"):
                    ui.button("Cancel", on_click=reset_dialog.close).props(
                        "flat dense"
                    ).classes("text-slate-300 px-3")

                    async def on_confirm():
                        reset_dialog.close()
                        await reset_from_config_file()

                    ui.button(
                        "Reset to File",
                        icon="restart_alt",
                        on_click=on_confirm,
                    ).props("unelevated dense").classes(
                        "bg-gradient-to-r from-amber-600 to-orange-600 "
                        "hover:from-amber-500 hover:to-orange-500 text-white "
                        "font-medium px-4 shadow-md"
                    )
            reset_dialog.open()

        def open_restore_backup_dialog() -> None:
            try:
                backups = self.callbacks.list_config_backups()
            except Exception:
                backups = []

            with (
                ui.dialog() as restore_dialog,
                ui.card().classes(
                    "bg-slate-900 border border-white/10 rounded-2xl p-5 "
                    "max-w-xl w-full gap-4"
                ),
            ):
                with ui.row().classes(
                    "w-full justify-between items-center pb-2 border-b border-white/10"
                ):
                    with ui.row().classes("items-center gap-3"):
                        with ui.element("div").classes(
                            "w-10 h-10 rounded-xl bg-indigo-500/20 "
                            "border border-indigo-500/30 flex items-center "
                            "justify-center text-indigo-400"
                        ):
                            ui.icon("history", size="md")
                        with ui.column().classes("gap-0"):
                            ui.label("Restore Wizard from Backup").classes(
                                "text-base font-bold text-slate-100"
                            )
                            ui.label(
                                "Select a saved snapshot to load into the wizard"
                            ).classes("text-xs text-slate-400")
                    ui.button(icon="close", on_click=restore_dialog.close).props(
                        "flat round dense"
                    )

                if not backups:
                    with ui.column().classes(
                        "w-full py-6 items-center justify-center text-slate-400 gap-2"
                    ):
                        ui.icon("inventory_2", size="lg")
                        ui.label("No configuration backups found.").classes("text-sm")
                else:
                    with ui.column().classes(
                        "w-full gap-2 max-h-[50vh] overflow-y-auto pr-1"
                    ):
                        for b in backups:
                            b_name = b.get("name", "")
                            b_time = b.get("formatted_time", "")
                            b_tag = b.get("tag", "Auto Backup")
                            b_size = b.get("size_bytes", 0)
                            size_kb = (
                                f"{b_size / 1024:.1f} KB"
                                if b_size > 0
                                else f"{b_size} B"
                            )

                            with ui.row().classes(
                                "w-full items-center justify-between p-3 "
                                "rounded-xl bg-slate-950/50 border border-white/5 "
                                "hover:border-indigo-500/30 transition-all gap-2"
                            ):
                                with ui.column().classes("gap-0.5"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(b_time).classes(
                                            "text-sm font-semibold text-slate-200"
                                        )
                                        ui.label(b_tag).classes(
                                            "text-[10px] px-2 py-0.5 rounded-full "
                                            "font-medium bg-cyan-950/60 text-cyan-300 "
                                            "border border-cyan-500/30"
                                        )
                                    ui.label(f"{b_name} • {size_kb}").classes(
                                        "text-xs font-mono text-slate-400"
                                    )

                                def make_wizard_restore(
                                    target_name: str, target_time: str
                                ):
                                    async def do_wizard_restore():
                                        restore_dialog.close()
                                        try:
                                            self.callbacks.restore_config_backup(
                                                target_name
                                            )
                                            await reset_from_config_file()
                                            ui.notify(
                                                "Wizard restored from backup "
                                                f"{target_time}",
                                                type="positive",
                                            )
                                        except Exception as err:
                                            ui.notify(
                                                f"Restore failed: {err}",
                                                type="negative",
                                            )

                                    return do_wizard_restore

                                ui.button(
                                    "Load Snapshot",
                                    icon="restore",
                                    on_click=make_wizard_restore(b_name, b_time),
                                ).props("unelevated dense").classes(
                                    "text-xs bg-indigo-600 hover:bg-indigo-500 "
                                    "text-white px-3 py-1"
                                )

            restore_dialog.open()

        with ui.row().classes(
            "w-full justify-between items-center mb-3 p-3 bg-slate-900/60 "
            "border border-white/10 rounded-2xl shadow-md backdrop-blur-md shrink-0"
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
                    on_click=open_clean_config_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Clear all ROIs and settings to start a new setup from scratch"
                )

                ui.button(
                    "Restore Backup",
                    icon="history",
                    on_click=open_restore_backup_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Select and restore a previous configuration backup"
                )

                ui.button(
                    "Reset to File",
                    icon="restart_alt",
                    on_click=open_reset_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Reload all wizard values from saved config file"
                )

                ui.label("9-Step Setup").classes(
                    "text-xs font-semibold text-indigo-300 bg-indigo-950/70 "
                    "border border-indigo-500/30 px-3 py-1 rounded-full shadow-inner"
                )

        self.download_image_step = DownloadImageStep(
            name=NAME_DOWNLOAD_IMAGE,
            set_image_callback=set_image,
            on_error_callback=on_download_error,
            spinner=self.spinner,
        )
        self.initial_rotate_step = InitialRotateStep(
            name=NAME_INITIAL_ROTATE,
            set_image_callback=set_image,
            spinner=self.spinner,
        )
        self.draw_refs_step = DrawRefsStep(
            name=NAME_DRAW_REFS,
            name_template="Ref",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_refs_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            spinner=self.spinner,
        )
        self.adjust_step = AdjustStep(
            name=NAME_ADJUST,
            set_image_callback=set_image,
            set_comparison_callback=set_comparison_image,
            spinner=self.spinner,
        )
        self.draw_digital_rois_step = DrawDigitalRoisStep(
            name=NAME_DRAW_DIGITAL_ROIS,
            name_template="Digital",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_digital_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            digital_models_dir=self.callbacks.get_config().digital_models_dir,
            spinner=self.spinner,
        )
        self.draw_analog_rois_step = DrawAnalogRoisStep(
            name=NAME_DRAW_ANALOG_ROIS,
            name_template="Analog",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_analog_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            analog_models_dir=self.callbacks.get_config().analog_models_dir,
            spinner=self.spinner,
        )
        self.meters_step = MeterStep(
            name=NAME_METERS,
            set_image_callback=set_image,
            get_digit_names_func=get_digit_names,
            spinner=self.spinner,
        )
        self.services_step = ServicesStep(
            name=NAME_SERVICES,
            set_image_callback=set_image,
            spinner=self.spinner,
        )
        self.final_step = FinalStep(
            name=NAME_FINAL,
            callbacks=self.callbacks,
            set_image_callback=set_image,
            save_refs_func=save_refs,
            spinner=self.spinner,
        )

        with (
            ui.splitter(value=42, limits=(20, 80))
            .classes("w-full flex-1 min-h-0 h-full")
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
            with (
                splitter.before,
                ui.column().classes(
                    "w-full h-full rounded-2xl bg-slate-950/80 p-3 "
                    "border border-white/10 shadow-2xl backdrop-blur-md "
                    "gap-3 overflow-y-auto overflow-x-hidden min-w-0 no-wrap"
                ),
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
                        self.main_image_tag = ui.label("ORIGINAL").classes(
                            "text-[10px] font-mono font-bold text-cyan-400 "
                            "px-2 py-0.5 rounded-md bg-cyan-950/60 "
                            "border border-cyan-500/30 shrink-0"
                        )

                    self.interactive_image = ui.interactive_image(
                        size=(640, 480),
                        on_mouse=mouse_handler,
                        events=["mousedown", "mouseup", "mousemove", "shiftKey"],
                        cross=True,
                    ).classes(
                        "w-full max-w-full min-w-0 shrink-0 rounded-lg "
                        "bg-slate-950 shadow-inner"
                    )
                    with ui.row().classes(
                        "w-full min-w-0 shrink-0 justify-between items-center "
                        "px-2 py-1.5 rounded-lg bg-slate-950/80 border "
                        "border-white/5 text-xs text-slate-400 gap-2"
                    ):
                        self.image_details = ui.label("").classes(
                            "font-mono text-cyan-400 font-semibold truncate"
                        )
                        self.mouse_position = ui.label("").classes(
                            "font-mono text-slate-400 truncate"
                        )
                        self.selected_position = ui.label("").classes(
                            "font-mono text-emerald-400 font-bold truncate"
                        )
                    show_offline_placeholder(
                        "No Image Loaded",
                        "Enter camera URL and click Download to start",
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

            with (
                splitter.after,
                ui.element("div").classes(
                    "w-full h-full flex flex-col justify-between min-h-0"
                ),
            ):
                with (
                    ui.element("div").classes(
                        "w-full flex-1 min-h-0 overflow-y-auto pr-1"
                    ),
                    ui.stepper(on_value_change=lambda x: handle_stepper_change(x.value))
                    .props("vertical")
                    .classes(
                        "w-full rounded-2xl shadow-xl bg-slate-900/40 "
                        "border border-white/5"
                    ) as stepper,
                ):
                    self.stepper = stepper
                    await self.download_image_step.show(stepper, first_step=True)
                    await self.initial_rotate_step.show(stepper)
                    await self.draw_refs_step.show(stepper)
                    await self.adjust_step.show(stepper)
                    await self.draw_digital_rois_step.show(stepper)
                    await self.draw_analog_rois_step.show(stepper)
                    await self.meters_step.show(stepper)
                    await self.services_step.show(stepper)
                    await self.final_step.show(stepper, last_step=True)

                # Persistent Docked Bottom Navigation Bar
                with ui.row().classes(
                    "w-full justify-between items-center p-3 mt-2 "
                    "bg-slate-900/90 border border-white/10 rounded-2xl "
                    "shadow-2xl backdrop-blur-md shrink-0"
                ):
                    self.wizard_prev_btn = (
                        ui.button(
                            "Back",
                            icon="arrow_back",
                            on_click=lambda: self.stepper.previous(),
                        )
                        .props("flat color=grey text-color=white")
                        .classes(
                            "px-4 py-2 rounded-xl text-sm font-medium "
                            "hover:bg-white/10 transition-all"
                        )
                        .tooltip("Return to previous step")
                    )
                    self.wizard_prev_btn.visible = False

                    with ui.row().classes("items-center gap-2"):
                        self.wizard_step_badge = ui.label(
                            f"Step 1 of {len(steps_order)}: {steps_order[0]}"
                        ).classes(
                            "text-xs font-semibold text-slate-300 font-mono "
                            "bg-slate-950/70 border border-white/10 px-3 "
                            "py-1.5 rounded-xl shadow-inner"
                        )

                    self.wizard_next_btn = (
                        ui.button(
                            "Continue",
                            on_click=on_wizard_next,
                        )
                        .props("unelevated icon-right=arrow_forward")
                        .classes(
                            "px-5 py-2 rounded-xl text-sm font-semibold "
                            "bg-gradient-to-r from-blue-600 to-cyan-600 "
                            "hover:from-blue-500 hover:to-cyan-500 "
                            "text-white shadow-lg shadow-cyan-950/40 "
                            "transition-all"
                        )
                        .tooltip("Proceed to next step")
                    )

        update_wizard_nav(self.stepper.value or steps_order[0])

        for img in self.callbacks.get_config().alignment.ref_images:
            if img.w == 0 or img.h == 0:
                img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

        # After stepper UI is created:
        config = self.callbacks.get_config()

        self.download_image_step.load_from_config(config.image_source)
        self.initial_rotate_step.load_from_config(config.alignment)
        self.draw_refs_step.load_from_config(config.alignment.ref_images)
        self.adjust_step.load_from_config(config)
        self.draw_digital_rois_step.load_from_config(config.digital_readout)
        self.draw_analog_rois_step.load_from_config(config.analog_readout)
        self.meters_step.load_from_config(config.meter_configs)
        self.services_step.load_from_config(config)

        # Automatically fetch the initial image if URL is configured
        if config.image_source.url:
            await self.download_image_step.download()
