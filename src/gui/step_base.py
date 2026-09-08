from configuration import ImageSource
from typing import Callable

from nicegui import ui


class BaseStep:
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        spinner=None,
    ) -> None:
        self.name = name
        self.spinner = spinner
        self.set_image_callback = set_image_callback
        self.image: str = ""

    @staticmethod
    def decorator_spinner(func):
        async def wrapper(self, *args, **kwargs):
            if self.spinner is not None:
                self.spinner.set_visibility(True)
            try:
                return await func(self, *args, **kwargs)
            finally:
                if self.spinner is not None:
                    self.spinner.set_visibility(False)

        return wrapper

    @staticmethod
    def decorator_catch_err(func):
        async def wrapper(self, *args, **kwargs):
            try:
                await func(self, *args, **kwargs)
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")

        return wrapper

    def load_from_config(self, image_source: ImageSource) -> None:
        if self.url:
            self.url.value = image_source.url
        if self.timeout:
            self.timeout.value = image_source.timeout

    def get_image(self) -> str:
        return self.image

    def update_image(self, image: str) -> None:
        self.image = image

    def set_spinner(self, spinner) -> None:
        self.spinner = spinner

    def add_help(self, content: str) -> None:
        classes = (
            "w-full text-caption text-slate-300 bg-slate-900/60 "
            "border border-white/10 rounded-xl mb-3 overflow-hidden shadow-sm"
        )
        with (
            ui.expansion("Help & Guidance", icon="help_outline")
            .classes(classes)
            .props("dense header-class='text-cyan-400 font-semibold'")
        ):
            with ui.column().classes("w-full px-3 py-2 text-slate-300"):
                ui.markdown(content).classes("text-caption leading-relaxed")

    def add_navigator(self, stepper, first_step=False, last_step=False) -> None:
        """Navigation is handled globally by the persistent wizard footer."""
        pass
