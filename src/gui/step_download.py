import asyncio
import contextlib
from typing import Callable

from nicegui import ui

from configuration import ImageSource
from processor.image import ImageProcessor
from .step_base import BaseStep

HELP_TEXT = (
    "- **Camera URL**: Enter snapshot endpoint (e.g. `http://...` or `file://...`).\n"
    "- **Timeout**: Set network request timeout in seconds (1–60s).\n"
    "- **Download**: Click the download button to fetch a frame."
)


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
        if hasattr(self, "minsize") and self.minsize is not None:
            self.minsize.value = image_source.min_size

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
            with contextlib.suppress(Exception):
                ui.notify(f"Download failed: {e}", type="negative")
            if self.on_error_callback is not None:
                self.on_error_callback(str(e))
            return False

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)
            with ui.row().classes("w-full items-center gap-2"):
                self.url = (
                    ui.input(label="URL", placeholder="URL")
                    .classes("flex-grow")
                    .tooltip("Camera snapshot URL (e.g. http://... or file://...)")
                )
                ui.button(
                    icon="sym_s_download", on_click=self.download
                ).bind_enabled_from(self.url, "value").tooltip(
                    "Download image from URL"
                )
                self.timeout = (
                    ui.number("Timeout (s)", value=10, min=1, max=60, step=1)
                    .classes("w-28")
                    .tooltip("Network request timeout in seconds (1–60s)")
                )
                self.minsize = (
                    ui.number("Min Size (bytes)", value=10000, min=1000, step=1000)
                    .classes("w-36")
                    .tooltip("Minimum valid image payload size in bytes")
                )

            super().add_navigator(stepper, first_step, last_step)
