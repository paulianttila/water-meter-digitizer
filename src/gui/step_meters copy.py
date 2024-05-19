from dataclasses import dataclass
from typing import Callable

from nicegui import ui

from configuration import Config

from .step_base import BaseStep


@dataclass
class MeterParams:
    name: str = ""
    consistency_enabled: bool = False
    allow_negative_rates: bool = False
    use_previous_value_filling: bool = False
    use_extended_resolution: bool = False
    max_rate_value: float = 0.2
    prevalue_from_file_max_age: int = 0
    unit: str = "㎥"
    value: str = None


class Digits:
    def __init__(self, digit_names: list[str], meter_params: MeterParams) -> None:
        self.digit_names = digit_names
        self.digit_container = None
        self.meter_params = meter_params

    def update_vals(self):
        value = "".join(
            "{" + item.value + "}"
            for item in self.digit_container
            if item is not None
        )
        self.meter_params.value = value

    def add_digit(self):
        with self.digit_container:
            ui.select(self.digit_names + ["."], value=1, on_change=self.update_vals)
            ui.select(self.digit_names + ["."], multiple=True, label='With digits') \
                .classes('w-full').props('use-chips')

    def remove_digit(self):
        last = len(list(self.digit_container)) - 1
        self.digit_container.remove(last)

    def show_new(self):
        self.digit_container = ui.row().classes("w-full")
        with ui.grid(columns=2):
            ui.button(icon="add", on_click=self.add_digit).tooltip("Add digit")
            ui.button(icon="remove", on_click=self.remove_digit).bind_enabled_from(
                self, "container", lambda x: len(list(x)) > 0
            ).tooltip("Remove last digit")


class Meter:
    def __init__(self, digit_names: list[str], name_candidate: str = "") -> None:
        self.digit_names = digit_names
        self.name_candidate = name_candidate

    def show_new(self) -> MeterParams:
        self.value_container = ui.row().classes("w-full")
        meter = MeterParams()
        meter.name = self.name_candidate
        with self.value_container:
            ui.separator()
            with ui.grid(columns="110px auto").classes("w-full gap-2"):
                ui.input("Name").bind_value(meter, "name")
                Digits(self.digit_names, meter).show_new()
            with ui.grid(columns="auto auto auto auto").classes("w-full gap-2"):
                ui.checkbox("Consistency enabled").bind_value(
                    meter, "consistency_enabled"
                )
                ui.checkbox("Allow negative rates").bind_value(
                    meter, "allow_negative_rates"
                )
                ui.checkbox("Use previous value filling").bind_value(
                    meter, "use_previous_value_filling"
                )
                ui.checkbox("Use extended resolution").bind_value(
                    meter, "use_extended_resolution"
                )
            with ui.grid(columns="auto auto auto").classes("w-full gap-2"):
                ui.number("Max rate value", value=0.2, min=0, step=0.01).bind_value(
                    meter, "max_rate_value"
                )
                ui.number(
                    "Prevalue from file max age", value=0, min=0, step=1
                ).bind_value(meter, "prevalue_from_file_max_age")
                ui.input("Unit", value="㎥")
            return meter

    def remove(self):
        self.value_container.clear()
        self.value_container.delete()


class MeterStep(BaseStep):
    def __init__(
        self,
        name: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
        digit_names: list[str] = None,
    ) -> None:
        super().__init__(name, spinner, get_image_func, set_image_func)
        self.digit_names = digit_names
        self.meters = []
        self.meter_params = []

    def add_meter(self):
        with self.values_container:
            name = f"Meter{len(self.meters) + 1}"
            meter_container = Meter(self.digit_names, name)
            self.meters.append(meter_container)
            meter = meter_container.show_new()
            self.meter_params.append(meter)

    def remove_meter(self):
        meter_container: Meter = self.meters.pop()
        meter_container.remove()

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            self.values_container = ui.row().classes("w-full")
            ui.separator()
            with ui.row():
                ui.button("Meter", icon="add", on_click=self.add_meter).tooltip(
                    "Add meter value"
                )
                ui.button(
                    "Meter", icon="remove", on_click=self.remove_meter
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Remove last meter value"
                )

            super().add_navigator(stepper, first_step, last_step)
