import asyncio
import contextlib
from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from configuration import ImageSource
from processor.image import ImageProcessor

from .base import BaseStep

HELP_TEXT = (
    "- **Camera URL**: Select a template model image (`model://...`) or enter a camera snapshot URL (`http://...`, `file://...`).\n"
    "- **Timeout**: Set network request timeout in seconds (1-60s).\n"
    "- **Download**: Click the download button to fetch a frame."
)


class DownloadImageStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        on_error_callback: Callable[[str], None] | None = None,
        spinner=None,
        config_dir: str | Path | None = None,
    ) -> None:
        self.url: ui.input
        self.timeout: ui.number
        self.minsize: ui.number
        self._initial_url: str = ""
        self._url_menu: ui.menu | None = None
        self.config_dir = config_dir
        self.on_error_callback = on_error_callback
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )

    def _get_url_options(
        self, current_url: str = "", force_reload: bool = False
    ) -> dict[str, str]:
        from config.meter_presets import get_available_template_images

        options: dict[str, str] = {}
        if current_url:
            options[current_url] = current_url

        # Available template model pictures
        for uri, label in get_available_template_images(
            config_dir=self.config_dir, force_reload=force_reload
        ):
            options[uri] = label

        # Fallback built-in options
        mock_uri = "model://mock_camera"
        if mock_uri not in options:
            options[mock_uri] = f"{mock_uri} (Mock Camera: Aqua-Digitizer AQ-20)"

        demo_url = "file://${ConfigDir}/original.jpg"
        if demo_url not in options:
            options[demo_url] = f"{demo_url} (Local Demo Image)"

        mock_cam_url = "http://localhost:3000/api/mock_camera"
        if mock_cam_url not in options:
            options[mock_cam_url] = f"{mock_cam_url} (Mock Camera API)"

        return options

    def refresh_options(self, force_reload: bool = True) -> dict[str, str]:
        """Refreshes available template image options from disk and updates dropdown."""
        cur = (
            self.url.value
            if hasattr(self, "url") and self.url is not None
            else getattr(self, "_initial_url", "")
        )
        options = self._get_url_options(current_url=cur, force_reload=force_reload)
        if hasattr(self, "url") and self.url is not None:
            self.url.options = options  # type: ignore[attr-defined]
            self._render_url_menu_items()
            if hasattr(self.url, "update"):
                self.url.update()
        return options

    def _render_url_menu_items(self) -> None:
        """Populates the template picker dropdown menu attached to the URL input."""
        if not hasattr(self, "_url_menu") or self._url_menu is None:
            return
        with contextlib.suppress(Exception):
            self._url_menu.clear()
            with self._url_menu:
                opts = getattr(self.url, "options", {}) or {}
                for uri, label in opts.items():
                    ui.menu_item(label, on_click=lambda u=uri: self._set_url_value(u))

    def _set_url_value(self, uri: str) -> None:
        if hasattr(self, "url") and self.url is not None:
            self.url.value = uri

    def _handle_refresh_click(self) -> None:
        self.refresh_options(force_reload=True)
        ui.notify("Template images reloaded from disk", type="positive")

    def load_from_config(self, image_source: ImageSource) -> None:
        self._initial_url = image_source.url
        if hasattr(self, "url") and self.url is not None:
            if (
                hasattr(self.url, "options")
                and isinstance(self.url.options, dict)
                and image_source.url
                and image_source.url not in self.url.options
            ):
                self.url.options[image_source.url] = image_source.url
                self._render_url_menu_items()
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
                init_val = getattr(self, "_initial_url", "")
                options = self._get_url_options(init_val)
                self.url = (
                    ui.input(
                        label="URL",
                        value=init_val or next(iter(options.keys()), ""),
                        placeholder="http://... or model://...",
                    )
                    .props("dense outlined clearable")
                    .classes("flex-grow")
                    .tooltip(
                        "Camera snapshot URL (http://...) or template model image (model://...)"
                    )
                )
                self.url.options = options  # type: ignore[attr-defined]
                self.url.on("keydown.enter", self.download)

                with (
                    self.url.add_slot("append"),
                    ui.button(icon="arrow_drop_down")
                    .props("flat dense round")
                    .tooltip("Choose template image or sample URL"),
                ):
                    self._url_menu = ui.menu().props("auto-close")
                    self._url_menu.on("before-show", self._render_url_menu_items)
                    self._render_url_menu_items()

                ui.button(icon="refresh", on_click=self._handle_refresh_click).props(
                    "dense flat"
                ).tooltip("Reload template images from disk")
                ui.button(icon="download", on_click=self.download).props(
                    "dense"
                ).bind_enabled_from(self.url, "value").tooltip(
                    "Download image from URL"
                )
                self.timeout = (
                    ui.number("Timeout (s)", value=10, min=1, max=60, step=1)
                    .props("dense outlined")
                    .classes("w-28")
                    .tooltip("Network request timeout in seconds (1-60s)")
                )
                self.minsize = (
                    ui.number("Min Size (bytes)", value=10000, min=1000, step=1000)
                    .props("dense outlined")
                    .classes("w-36")
                    .tooltip("Minimum valid image payload size in bytes")
                )

            super().add_navigator(stepper, first_step, last_step)
