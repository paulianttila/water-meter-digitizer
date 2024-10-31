from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class AdjustStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.rotate_angle: ui.number
        self.org_image: str = ""

    def update_image(self, image: str) -> None:
        self.org_image = image
        self.image = self._do_adjust(image)

    def _reset_image(self) -> None:
        if self.org_image != "":
            self.image = self.org_image
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def do_adjust(self) -> None:
        self._reset_image()
        self.image = self._do_adjust(self.image)
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

    def _do_adjust(self, image: str) -> str:
        return (
            ImageProcessor()
            .set_image_from_base64_str(image)
            .if_(self.rotate_enabled.value)
            .rotate_image(self.rotate_angle.value)
            .endif_()
            .if_(self.crop_enabled.value)
            .crop_image(
                x=self.crop_x.value,
                y=self.crop_y.value,
                w=self.crop_w.value,
                h=self.crop_h.value,
            )
            .endif_()
            .if_(self.resize_enabled.value)
            .resize_image(
                width=int(self.resize_w.value),
                height=int(self.resize_h.value),
            )
            .endif_()
            .if_(self.adjust_enabled.value)
            .adjust_image(
                contrast=self.adjust_contrast.value,
                brightness=self.adjust_brightness.value,
                sharpness=self.adjust_sharpness.value,
                color=self.adjust_color.value,
            )
            .endif_()
            .if_(self.grayscale_enabled.value)
            .to_gray_scale()
            .endif_()
            .if_(self.autocontrast_enabled.value)
            .autocontrast_image(
                cutoff_low=self.autocontrast_cutoff_low.value,
                cutoff_high=self.autocontrast_cutoff_high.value,
            )
            .endif_()
            .get_image_as_base64_str()
        )

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):

            with ui.row().classes("w-full items-center"):
                self.rotate_enabled = ui.checkbox("Enable Rotate", value=False)
                self.rotate_angle = ui.number(
                    "Angle", min=-359, max=359, step=1, value=0
                )

            with ui.row().classes("w-full items-center"):
                self.crop_enabled = ui.checkbox("Enable Crop", value=False)
                self.crop_x = ui.number("X", min=-0, max=10000, step=1, value=0)
                self.crop_y = ui.number("Y", min=-0, max=10000, step=1, value=0)
                self.crop_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.crop_h = ui.number("Height", min=-480, max=10000, step=1, value=0)

            with ui.row().classes("w-full items-center"):
                self.adjust_enabled = ui.checkbox("Enable Adjust", value=False)
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
                self.resize_enabled = ui.checkbox("Enable Resize", value=False)
                self.resize_w = ui.number("Width", min=-640, max=10000, step=1, value=0)
                self.resize_h = ui.number(
                    "Height", min=-480, max=10000, step=1, value=0
                )

            with ui.row().classes("w-full items-center"):
                self.grayscale_enabled = ui.checkbox(
                    "Enable Grayscale image", value=False
                )

            with ui.row().classes("w-full items-center"):
                self.autocontrast_enabled = ui.checkbox(
                    "Enable Autocontrast", value=False
                )
                self.autocontrast_cutoff_low = ui.number(
                    "Cutoff low", min=0, max=100, step=1, value=2
                )
                self.autocontrast_cutoff_high = ui.number(
                    "Cutoff high", min=0, max=100, step=1, value=45
                )

            with ui.row().classes("w-full items-center"):
                self.autocontrast_cut_images_enabled = ui.checkbox(
                    "Enable Autocontrast for cutted images", value=False
                )
                self.autocontrast_cut_images_cutoff_low = ui.number(
                    "Cutoff low", min=0, max=100, step=1, value=2
                )
                self.autocontrast_cut_images_cutoff_high = ui.number(
                    "Cutoff high", min=0, max=100, step=1, value=45
                )

            with ui.row().classes("w-full items-center"):
                ui.button(icon="sym_s_resize", on_click=self.do_adjust).tooltip(
                    "Adjust image"
                )
                ui.button(icon="sym_s_restore", on_click=self._reset_image).tooltip(
                    "Restore original image"
                )

            super().add_navigator(stepper, first_step, last_step)
