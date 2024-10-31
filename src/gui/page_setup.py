from hashlib import sha256
import logging

from nicegui import events, ui

from callbacks import Callbacks
from configuration import CNNParams, Config
from data_classes import ImagePosition, MeterConfig, RefImage
from .step_meters import MeterStep
from .step_download import DownloadImageStep
from .step_initial_rotate import InitialRotateStep
from .step_draw_refs import DrawRefsStep
from .step_adjust import AdjustStep
from .step_draw_digital_rois import DrawDigitalRoisStep
from .step_draw_analog_rois import DrawAnalogRoisStep

from .step_final import FinalStep
import utils.image as ImageUtils

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
NAME_FINAL = "Final"

steps_order = [
    NAME_DOWNLOAD_IMAGE,
    NAME_INITIAL_ROTATE,
    NAME_DRAW_REFS,
    NAME_ADJUST,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_ANALOG_ROIS,
    NAME_METERS,
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
        self.ini_rota_step: InitialRotateStep
        self.draw_refs_step: DrawRefsStep
        self.adjust_step: AdjustStep
        self.draw_digital_rois_step: DrawDigitalRoisStep
        self.draw_analog_rois_step: DrawAnalogRoisStep
        self.meters_step: MeterStep
        self.final_step: FinalStep

        self.previous_step: str = ""

        self.config: Config
        self.image: str = ""  # base64 str
        self.refs = ""
        self.refs_enabled_in_image = False
        self.digital_rois = ""
        self.digital_rois_enabled_in_image = ""
        self.analog_rois = ""
        self.analog_rois_enabled_in_image = ""

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
            config.image_source.url = self.download_image_step.url.value
            config.image_source.timeout = self.download_image_step.timeout.value
            config.crop.enabled = self.adjust_step.crop_enabled.value
            config.crop.x = self.adjust_step.crop_x.value
            config.crop.y = self.adjust_step.crop_y.value
            config.crop.w = self.adjust_step.crop_w.value
            config.crop.h = self.adjust_step.crop_h.value
            config.resize.enabled = self.adjust_step.resize_enabled.value
            config.resize.w = self.adjust_step.resize_w.value
            config.resize.h = self.adjust_step.resize_h.value
            config.image_processing.enabled = self.adjust_step.adjust_enabled.value
            config.image_processing.contrast = self.adjust_step.adjust_contrast.value
            config.image_processing.brightness = (
                self.adjust_step.adjust_brightness.value
            )
            config.image_processing.sharpness = self.adjust_step.adjust_brightness.value
            config.image_processing.color = self.adjust_step.adjust_color.value
            config.image_processing.grayscale = self.adjust_step.grayscale_enabled.value
            config.alignment.rotate_angle = self.ini_rota_step.angle
            config.alignment.post_rotate_angle = self.adjust_step.rotate_angle.value
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
            model_file = ""
            if self.draw_digital_rois_step.cnn_file.value is not None:
                model_file = self.draw_digital_rois_step.cnn_file.options[
                    self.draw_digital_rois_step.cnn_file.value
                ]
            model_dir = "${DigitalModelsDir}"
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
            config.digital_readout = CNNParams(
                enabled=True,
                model=str(self.draw_digital_rois_step.cnn_type.value),
                model_file=f"{model_dir}/{model_file}",
                cut_images=digital_cut_images,
            )

            model_file = ""
            if self.draw_analog_rois_step.cnn_file.value is not None:
                model_file = self.draw_analog_rois_step.cnn_file.options[
                    self.draw_analog_rois_step.cnn_file.value
                ]

            model_dir = "${AnalogModelsDir}"
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
            config.analog_readout = CNNParams(
                enabled=True,
                model=str(self.draw_analog_rois_step.cnn_type.value),
                model_file=f"{model_dir}/{model_file}",
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
                        use_previuos_value=meter.use_previous_value_filling,
                        pre_value_from_file_max_age=meter.prevalue_from_file_max_age,
                        use_extended_resolution=meter.use_extended_resolution,
                        unit=meter.unit,
                    )
                )
            config.meter_configs = meters
            self.config = config

        def save_refs() -> None:
            config_dir = self.callbacks.get_config().config_dir
            image = ImageUtils.convert_base64_str_to_image(self.image)
            for roi in self.draw_refs_step.rois:
                ref_img = ImageUtils.cut_image(
                    image, ImagePosition(roi.name, roi.x, roi.y, roi.w, roi.h)
                )
                ImageUtils.save_image(
                    ref_img, f"{config_dir}/{roi.name}_x{roi.x}_y{roi.y}.jpg"
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
                return self.ini_rota_step.get_image()
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
            elif name == NAME_FINAL:
                return self.final_step.get_image()
            return ""

        def set_image_by_step_name(name: str, image: str) -> None:
            if name == NAME_INITIAL_ROTATE:
                self.ini_rota_step.update_image(image)
            elif name == NAME_DRAW_REFS:
                self.draw_refs_step.update_image(image)
            elif name == NAME_ADJUST:
                self.adjust_step.update_image(image)
            elif name == NAME_DRAW_DIGITAL_ROIS:
                self.draw_digital_rois_step.update_image(image)
            elif name == NAME_DRAW_ANALOG_ROIS:
                self.draw_analog_rois_step.update_image(image)
            elif name == NAME_METERS:
                self.meters_step.update_image(image)
            elif name == NAME_FINAL:
                self.final_step.update_image(image)

        def is_step_forward(new_step: str, previous_step: str) -> bool:
            if previous_step == "":
                return True
            return steps_order.index(new_step) > steps_order.index(previous_step)

        def handle_stepper_change(step: str) -> None:
            logger.debug(f"Step: {self.previous_step} -> {step}")

            img = get_image_by_step_name(step)
            print_image_hash(f"step {step}", img)
            step_forward = is_step_forward(step, self.previous_step)
            if step_forward:
                logger.debug("Step forward")
                previous_img = get_image_by_step_name(self.previous_step)
                set_image_by_step_name(step, previous_img)
                img = get_image_by_step_name(step)
                print_image_hash(f"step {self.previous_step}", previous_img)
            else:
                logger.debug("Step backward")

            self.refs_enabled_in_image = step == NAME_DRAW_REFS
            self.digital_rois_enabled_in_image = step == NAME_DRAW_DIGITAL_ROIS
            self.analog_rois_enabled_in_image = step == NAME_DRAW_ANALOG_ROIS
            if step == NAME_METERS:
                self.digital_rois_enabled_in_image = True
                self.analog_rois_enabled_in_image = True
            if step == NAME_FINAL:
                self.refs_enabled_in_image = True
                self.digital_rois_enabled_in_image = True
                self.analog_rois_enabled_in_image = True

            set_image(img)
            if step == NAME_FINAL:
                gather_config()
                self.final_step.set_config(self.config)
            self.previous_step = step

        ui.label("Setup").classes("text-h4")
        with ui.row():
            self.spinner = ui.spinner("dots", size="lg", color="blue")

        self.spinner.visible = False
        self.download_image_step = DownloadImageStep(
            name=NAME_DOWNLOAD_IMAGE,
            set_image_callback=set_image,
            spinner=self.spinner,
        )
        self.ini_rota_step = InitialRotateStep(
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
        self.final_step = FinalStep(
            name=NAME_FINAL,
            callbacks=self.callbacks,
            set_image_callback=set_image,
            save_refs_func=save_refs,
            spinner=self.spinner,
        )

        with ui.splitter(value=40).classes("w-full") as splitter:
            with splitter.before:
                self.interactive_image = ui.interactive_image(
                    size=(640, 480),
                    on_mouse=mouse_handler,
                    events=["mousedown", "mouseup", "mousemove", "shiftKey"],
                    cross=True,
                ).classes("w-full bg-blue-50")
                with ui.row().classes("w-full"):
                    self.image_details = ui.label("")
                    self.mouse_position = ui.label("")
                    self.selected_position = ui.label("")
            with splitter.after:
                with ui.stepper(
                    on_value_change=lambda x: handle_stepper_change(x.value)
                ).props("vertical").classes("w-full") as stepper:
                    await self.download_image_step.show(stepper, first_step=True)
                    await self.ini_rota_step.show(stepper)
                    await self.draw_refs_step.show(stepper)
                    await self.adjust_step.show(stepper)
                    await self.draw_digital_rois_step.show(stepper)
                    await self.draw_analog_rois_step.show(stepper)
                    await self.meters_step.show(stepper)
                    await self.final_step.show(stepper, last_step=True)

        for img in self.callbacks.get_config().alignment.ref_images:
            if img.w == 0 or img.h == 0:
                img.w, img.h = ImageUtils.image_size_from_file(img.file_name)
