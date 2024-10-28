from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class AdjustStep(BaseStep):
    def __init__(
        self,
        name: str,
        get_image_func: Callable[[], str],
        set_image_func: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            get_image_func=get_image_func,
            set_image_func=set_image_func,
            spinner=spinner,
        )
        self.rotate_angle: ui.number
        self.org_image: str = ""

    def reset_image(self) -> None:
        if self.get_image_func is not None:
            if self.org_image == "":
                self.org_image = self.get_image_func()
            self.image = self.org_image
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def do_adjust(self) -> None:
        self.reset_image()
        if self.rotate_angle.value != 0:
            self.rotate_image()
        if self.crop_enabled.value:
            self.crop_image()
        if self.resize_enabled.value:
            self.resize_image()
        if self.adjust_enabled.value:
            self.adjust_image()
        if self.grayscale_enabled.value:
            self.grayscale_image()

    def rotate_image(self) -> None:
        imageProcessor = ImageProcessor()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.rotate_image(
            self.rotate_angle.value
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    def crop_image(self) -> None:
        imageProcessor = ImageProcessor()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.crop_image(
            x=self.crop_x.value,
            y=self.crop_y.value,
            w=self.crop_w.value,
            h=self.crop_h.value,
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    def resize_image(self) -> None:
        imageProcessor = ImageProcessor()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.resize_image(
            width=int(self.resize_w.value),
            height=int(self.resize_h.value),
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    def adjust_image(self) -> None:
        imageProcessor = ImageProcessor()
        # self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.adjust_image(
            contrast=self.adjust_contrast.value,
            brightness=self.adjust_brightness.value,
            sharpness=self.adjust_sharpness.value,
            color=self.adjust_color.value,
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    def grayscale_image(self) -> None:
        imageProcessor = ImageProcessor()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.to_gray_scale().get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            ui.label("Rotate image")
            with ui.row().classes("w-full items-center"):
                self.rotate_enabled = ui.checkbox("Enable", value=False)
                self.rotate_angle = ui.number(
                    "Angle", min=-359, max=359, step=1, value=0
                )

            ui.label("Crop image")
            with ui.row().classes("w-full items-center"):
                self.crop_enabled = ui.checkbox("Enabled", value=False)
                self.crop_x = ui.number("X", min=-0, max=10000, step=1, value=0)
                self.crop_y = ui.number("Y", min=-0, max=10000, step=1, value=0)
                self.crop_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.crop_h = ui.number("Height", min=-480, max=10000, step=1, value=0)

            ui.label("Adjust image")
            with ui.row().classes("w-full items-center"):
                # ui.button(icon="adjust", on_click=self.adjust_image).tooltip(
                #    "Adjust image"
                # )
                self.adjust_enabled = ui.checkbox("Enabled", value=False)
                self.adjust_contrast = ui.number(
                    "Contrast", min=-0, max=10, step=0.1, value=1.0
                )
                self.adjust_brightness = ui.number(
                    "Brightness", min=-0, max=10, step=0.1, value=1.0
                )
                self.adjust_sharpness = ui.number(
                    "Sharpness", min=-0, max=10, step=0.1, value=1.0
                )
                self.adjust_color = ui.number(
                    "Color", min=-0, max=10, step=0.1, value=1.0
                )

            ui.label("Resize image")
            with ui.row().classes("w-full items-center"):
                self.resize_enabled = ui.checkbox("Enabled", value=False)
                self.resize_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.resize_h = ui.number(
                    "Height", min=-480, max=10000, step=1, value=0
                )

            ui.label("Grayscale image")
            with ui.row().classes("w-full items-center"):
                self.grayscale_enabled = ui.checkbox("Enabled", value=False)

            with ui.row().classes("w-full items-center"):
                ui.button(icon="sym_s_resize", on_click=self.do_adjust).tooltip(
                    "Adjust image"
                )
                ui.button(icon="sym_s_restore", on_click=self.reset_image).tooltip(
                    "Restore original image"
                )

            super().add_navigator(stepper, first_step, last_step)
