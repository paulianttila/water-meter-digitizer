import logging

from nicegui import events, ui
from PIL import Image

from processor.image import ImageProcessor
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

imageProcessor = ImageProcessor()

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


class SetupPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.interactive_image = None
        self.image_details = None
        self.mouse_position = None
        self.selected_position = None
        self.spinner = None
        self.config: Config = None
        self.image = None
        self.refs = ""
        self.refs_enabled_in_image = False
        self.digital_rois = ""
        self.digital_rois_enabled_in_image = ""
        self.analog_rois = ""
        self.analog_rois_enabled_in_image = ""

    async def show(self):

        def update_svg(draw: str = None):
            self.interactive_image.content = f"""
                {svg_grid}
                <rect width="100%" height="100%" fill="url(#grid)" />
                {self.refs if self.refs_enabled_in_image else ""}
                {self.digital_rois if self.digital_rois_enabled_in_image else ""}
                {self.analog_rois if self.analog_rois_enabled_in_image else ""}
                {draw if draw is not None else ""}
                """

        def set_image(img: Image):
            self.image = img
            w, h = ImageUtils.image_size(ImageUtils.convert_base64_str_to_image(img))
            self.image_details.text = f"Size: {w}x{h}"
            self.interactive_image.set_source(f"data:image/png;base64,{img}")
            self.interactive_image.update()
            update_svg()

        # @decorator_undo_operation
        def update_image(img: Image = None):
            set_image(img)

        def mouse_handler(e: events.MouseEventArguments):
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

        def get_refs_from_config():
            style = "stroke-width:3;stroke:red;fill-opacity:0;stroke-opacity:0.9"
            content = ""
            for ref in self.callbacks.get_config().alignment.ref_images:
                content += (
                    f'<rect x="{ref.x}" y="{ref.y}" width="{ref.w}" '
                    f'height="{ref.h}" style="{style}" />'
                )
            return content

        def get_image() -> Image:
            return self.image

        def set_refs_to_svg_func(refs: str):
            self.refs = refs
            update_svg()

        def set_digital_rois_to_svg_func(rois: str):
            self.digital_rois = rois
            update_svg()

        def set_analog_rois_to_svg_func(rois: str):
            self.analog_rois = rois
            update_svg()

        def show_temp_draw_in_svg_func(draw: str):
            update_svg(draw)

        def gather_config():
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
                model=self.draw_digital_rois_step.cnn_type.value,
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
                model=self.draw_analog_rois_step.cnn_type.value,
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

        def save_refs():
            config_dir = self.callbacks.get_config().config_dir
            image = ImageUtils.convert_base64_str_to_image(self.image)
            for roi in self.draw_refs_step.rois:
                ref_img = ImageUtils.cut_image(
                    image, ImagePosition(roi.name, roi.x, roi.y, roi.w, roi.h)
                )
                ImageUtils.save_image(
                    ref_img, f"{config_dir}/{roi.name}_x{roi.x}_y{roi.y}.jpg"
                )

        def get_digit_names():
            rois = []
            for roi in self.draw_digital_rois_step.rois:
                rois.append(roi.name)
            for roi in self.draw_analog_rois_step.rois:
                rois.append(roi.name)
            return rois

        def handle_stepper_change(step: str):
            if step == NAME_DOWNLOAD_IMAGE:
                img = self.download_image_step.get_image()
            elif step == NAME_INITIAL_ROTATE:
                img = self.ini_rota_step.get_image()
            elif step == NAME_DRAW_REFS:
                img = self.draw_refs_step.get_image()
            elif step == NAME_ADJUST:
                img = self.adjust_step.get_image()
            elif step == NAME_DRAW_DIGITAL_ROIS:
                img = self.draw_digital_rois_step.get_image()
            elif step == NAME_DRAW_ANALOG_ROIS:
                img = self.draw_analog_rois_step.get_image()
            elif step == NAME_METERS:
                img = self.meters_step.get_image()
            elif step == NAME_FINAL:
                gather_config()
                self.final_step.set_config(self.config)
                img = self.final_step.get_image()

            if img is not None:
                self.image = img

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

            if self.image is not None:
                set_image(self.image)
                update_svg()

        ui.label("Setup").classes("text-h4")
        with ui.row():
            self.spinner = ui.spinner("dots", size="lg", color="blue")

        self.spinner.visible = False
        self.download_image_step = DownloadImageStep(
            name=NAME_DOWNLOAD_IMAGE,
            spinner=self.spinner,
            get_image_func=None,
            set_image_func=set_image,
        )
        self.ini_rota_step = InitialRotateStep(
            name=NAME_INITIAL_ROTATE,
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
        )
        self.draw_refs_step = DrawRefsStep(
            name=NAME_DRAW_REFS,
            name_template="Ref",
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
            set_rois_to_svg_func=set_refs_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
        )
        self.adjust_step = AdjustStep(
            name=NAME_ADJUST,
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
        )
        self.draw_digital_rois_step = DrawDigitalRoisStep(
            name=NAME_DRAW_DIGITAL_ROIS,
            name_template="Digital",
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
            set_rois_to_svg_func=set_digital_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            digital_models_dir=self.callbacks.get_config().digital_models_dir,
        )
        self.draw_analog_rois_step = DrawAnalogRoisStep(
            name=NAME_DRAW_ANALOG_ROIS,
            name_template="Analog",
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
            set_rois_to_svg_func=set_analog_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            analog_models_dir=self.callbacks.get_config().analog_models_dir,
        )
        self.meters_step = MeterStep(
            name=NAME_METERS,
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
            get_digit_names_func=get_digit_names,
        )
        self.final_step = FinalStep(
            name=NAME_FINAL,
            callbacks=self.callbacks,
            spinner=self.spinner,
            get_image_func=get_image,
            set_image_func=update_image,
            save_refs_func=save_refs,
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
