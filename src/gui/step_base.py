from typing import Callable
from nicegui import ui


class BaseStep:
    def __init__(
        self,
        name: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
    ) -> None:
        self.name = name
        self.spinner = spinner
        self.get_image_func = get_image_func
        self.set_image_func = set_image_func
        self.image = None

    def get_image(self):
        return self.image

    def set_get_image_func(self, func: Callable[[], None]) -> "BaseStep":
        self.get_image_func = func

    def set_set_image_func(self, func: Callable[[], None]) -> "BaseStep":
        self.set_image_func = func

    def decorator_spinner(func):
        async def wrapper(self, *args, **kwargs):
            self.spinner.set_visibility(True)
            try:
                await func(self, *args, **kwargs)
            finally:
                self.spinner.set_visibility(False)

        return wrapper

    def decorator_catch_err(func):
        async def wrapper(self, *args, **kwargs):
            try:
                await func(self, *args, **kwargs)
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")

        return wrapper

    def set_spinner(self, spinner) -> None:
        self.spinner = spinner

    def add_navigator(self, stepper, first_step=False, last_step=False):

        with ui.stepper_navigation():
            if not first_step:
                ui.button("Back", on_click=stepper.previous).props(
                    "flat color=green"
                ).tooltip("Go back")
            if not last_step:
                ui.button("Next", on_click=stepper.next).props("color=green").tooltip(
                    "Go next"
                )
