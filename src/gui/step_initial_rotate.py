from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class InitialRotateStep(BaseStep):
    def __init__(
        self,
        name: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
    ) -> None:
        super().__init__(name, spinner, get_image_func, set_image_func)
        self.org_image = None
        self.angle = 0

    def reset_image(self):
        if self.get_image_func is not None:
            if self.org_image is None:
                self.org_image = self.get_image_func()
            self.image = self.org_image
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    async def rotate_image(self, angle):
        imageProcessor = ImageProcessor()
        self.reset_image()
        imageProcessor.set_image_from_base64_str(self.image)
        self.image = imageProcessor.rotate_image(angle).get_image_as_base64_str()
        self.angle = angle
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def initial_rotation_left(self):
        await self.rotate_image(-90)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def rotate_image_180(self):
        await self.rotate_image(180)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def initial_rotation_right(self):
        await self.rotate_image(90)

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            with ui.row():
                ui.button(
                    icon="rotate_left", on_click=self.initial_rotation_left
                ).tooltip("Rotate image 90° left")
                ui.button(
                    icon="flip_camera_android", on_click=self.rotate_image_180
                ).tooltip("Rotate image 180°")
                ui.button(
                    icon="rotate_right", on_click=self.initial_rotation_right
                ).tooltip("Rotate image 90° right")
            ui.label("")
            ui.button(icon="sym_s_restore", on_click=self.reset_image).tooltip(
                "Restore original image"
            )

            super().add_navigator(stepper, first_step, last_step)
