import asyncio
from typing import Callable

from nicegui import ui

from processor.image import ImageProcessor
from .step_base import BaseStep


class DownloadImageStep(BaseStep):
    def __init__(
        self,
        name: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
    ) -> None:
        self.url = None
        super().__init__(name, spinner, get_image_func, set_image_func)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def download(self):
        def do() -> str:
            return (
                ImageProcessor()
                .download_image(self.url.value, self.timeout.value)
                .get_image_as_base64_str()
            )

        if self.url.value == "":
            return
        self.image = await asyncio.to_thread(do)
        if self.set_image_func is not None:
            self.set_image_func(self.image)

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            with ui.row().classes("w-full items-center"):
                self.url = ui.input(label="URL", placeholder="URL").classes("w-4/5")
                ui.button(
                    icon="sym_s_download", on_click=self.download
                ).bind_enabled_from(self.url, "value").tooltip(
                    "Download image from URL"
                )
                self.timeout = ui.number(
                    "Timeout", value=10, min=1, max=60, step=1
                ).classes("w-1/5")

            super().add_navigator(stepper, first_step, last_step)
