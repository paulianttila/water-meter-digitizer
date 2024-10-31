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
            self.spinner.set_visibility(True)
            try:
                await func(self, *args, **kwargs)
            finally:
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

    def get_image(self) -> str:
        return self.image

    def update_image(self, image: str) -> None:
        self.image = image

    def set_spinner(self, spinner) -> None:
        self.spinner = spinner

    def add_navigator(self, stepper, first_step=False, last_step=False) -> None:

        with ui.stepper_navigation():
            if not first_step:
                ui.button("Back", on_click=stepper.previous).props(
                    "flat color=green"
                ).tooltip("Go back")
            if not last_step:
                ui.button("Next", on_click=stepper.next).props("color=green").tooltip(
                    "Go next"
                )
