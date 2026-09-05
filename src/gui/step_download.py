import asyncio
from typing import Callable

from nicegui import ui

from configuration import ImageSource
from processor.image import ImageProcessor
from .step_base import BaseStep


class DownloadImageStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        on_error_callback: Callable[[str], None] = None,
        spinner=None,
    ) -> None:
        self.url: ui.input
        self.timeout: ui.number
        self.on_error_callback = on_error_callback
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )

    def load_from_config(self, image_source: ImageSource) -> None:
        if hasattr(self, "url") and self.url is not None:
            self.url.value = image_source.url
        if hasattr(self, "timeout") and self.timeout is not None:
            self.timeout.value = image_source.timeout

    @BaseStep.decorator_spinner
    async def download(self) -> bool:
        def do() -> str:
            return (
                ImageProcessor()
                .download_image(self.url.value, int(self.timeout.value))
                .get_image_as_base64_str()
            )

        if not self.url.value:
            return False
        try:
            self.image = await asyncio.to_thread(do)
            if self.set_image_callback is not None:
                self.set_image_callback(self.image)
            return True
        except Exception as e:
            try:
                ui.notify(f"Download failed: {e}", type="negative")
            except Exception:
                pass
            if self.on_error_callback is not None:
                self.on_error_callback(str(e))
            return False

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(
                """
- **Camera URL**: Enter your snapshot camera endpoint (e.g. `http://192.168.1.100/capture` or `file:///config/original.jpg`).
- **Timeout**: Set network request timeout in seconds (1–60s).
- **Download**: Click the download button to fetch a frame from the camera.
                """
            )
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
