from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class InitialRotateStep(BaseStep):
    def __init__(
        self,
        name: str,
        #get_image_callback: Callable[[], str],
        set_image_callback: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            #get_image_callback=get_image_callback,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.angle = 0
        self.org_image: str = ""

    def update_image(self, image: str) -> None:
        self.org_image = image
        self.image = self._rotate_image(image, self.angle)

    def _reset_image(self) -> None:
        if self.org_image != "":
            self.image = self.org_image
            self.angle = 0
            self.angle_label.set_text(f"Rotate: {self.angle}°")
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

    def _rotate(self, angle: float) -> None:
        self._reset_image()
        self.image = self._rotate_image(self.image, angle)
        self.angle = angle
        self.angle_label.set_text(f"Rotate: {self.angle}°")
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

    def _rotate_image(self, image: str, angle: float) -> str:
        return (
            ImageProcessor()
            .set_image_from_base64_str(image)
            .rotate_image(angle)
            .get_image_as_base64_str()
        )

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def _rotate_left(self) -> None:
        self._rotate(-90)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def _rotate_180(self) -> None:
        self._rotate(180)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def _rotate_right(self) -> None:
        self._rotate(90)

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            with ui.row():
                ui.button(icon="rotate_left", on_click=self._rotate_left).tooltip(
                    "Rotate image 90° left"
                )
                ui.button(
                    icon="flip_camera_android", on_click=self._rotate_180
                ).tooltip("Rotate image 180°")
                ui.button(icon="rotate_right", on_click=self._rotate_right).tooltip(
                    "Rotate image 90° right"
                )
            self.angle_label = ui.label("")
            ui.button(icon="sym_s_restore", on_click=self._reset_image).tooltip(
                "Restore original image"
            )

            super().add_navigator(stepper, first_step, last_step)
