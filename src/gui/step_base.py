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
        with ui.stepper_navigation().classes(
            "w-full flex justify-between items-center mt-4 pt-3 border-t "
            "border-white/10"
        ):
            if not first_step:
                ui.button("Back", icon="arrow_back", on_click=stepper.previous).props(
                    "flat color=grey text-color=white"
                ).classes("px-4 py-1.5 rounded-lg text-sm font-medium").tooltip(
                    "Return to previous step"
                )
            else:
                ui.element("div")  # Spacer to keep Next on the right

            if not last_step:
                ui.button("Continue", on_click=stepper.next).props(
                    "icon-right=arrow_forward color=primary"
                ).classes(
                    "px-5 py-1.5 rounded-lg text-sm font-semibold bg-gradient-to-r "
                    "from-blue-600 to-cyan-600 text-white shadow-md shadow-cyan-900/30"
                ).tooltip(
                    "Proceed to next step"
                )
