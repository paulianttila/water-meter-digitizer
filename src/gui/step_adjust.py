from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class AdjustStep(BaseStep):
    def __init__(
        self,
        name: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
    ) -> None:
        super().__init__(name, spinner, get_image_func, set_image_func)
        self.rotate_angle = None
        self.org_image = None

    def reset_image(self):
        if self.get_image_func is not None:
            if self.org_image is None:
                self.org_image = self.get_image_func()
            self.image = self.org_image
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def rotate_image(self):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.rotate_image(
            self.rotate_angle.value
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def crop_image(self):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.crop_image(
            x=self.crop_x.value,
            y=self.crop_y.value,
            w=self.crop_w.value,
            h=self.crop_h.value,
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def resize_image(self):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.resize_image(
            width=int(self.resize_w.value),
            height=int(self.resize_h.value),
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def adjust_image(self):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.adjust_image(
            contrast=self.adjust_contrast.value,
            brightness=self.adjust_brightness.value,
            sharpness=self.adjust_sharpness.value,
            color=self.adjust_color.value,
        ).get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def grayscale_image(self):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.to_gray_scale().get_image_as_base64_str()
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            with ui.row().classes("w-full items-center"):
                ui.button(icon="sym_s_autorenew", on_click=self.rotate_image).tooltip(
                    "Rotate image"
                )
                self.rotate_angle = ui.number(
                    "Angle", min=-359, max=359, step=1, value=0
                )
            with ui.row().classes("w-full items-center"):
                ui.button(icon="crop", on_click=self.crop_image).tooltip("Crop image")
                self.crop_enabled = ui.checkbox("Enabled", value=False)
                self.crop_x = ui.number("X", min=-0, max=10000, step=1, value=0)
                self.crop_y = ui.number("Y", min=-0, max=10000, step=1, value=0)
                self.crop_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.crop_h = ui.number("Height", min=-480, max=10000, step=1, value=0)
            with ui.row().classes("w-full items-center"):
                ui.button(icon="adjust", on_click=self.adjust_image).tooltip(
                    "Adjust image"
                )
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
            with ui.row().classes("w-full items-center"):
                ui.button(icon="sym_s_resize", on_click=self.resize_image).tooltip(
                    "Crop image"
                )
                self.resize_enabled = ui.checkbox("Enabled", value=False)
                self.resize_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.resize_h = ui.number(
                    "Height", min=-480, max=10000, step=1, value=0
                )
            with ui.row().classes("w-full items-center"):
                ui.button(icon="sym_s_resize", on_click=self.grayscale_image).tooltip(
                    "Grayscale image"
                )
                self.grayscale_enabled = ui.checkbox("Enabled", value=False)
            ui.button(icon="sym_s_restore", on_click=self.reset_image).tooltip(
                "Restore original image"
            )

            super().add_navigator(stepper, first_step, last_step)
