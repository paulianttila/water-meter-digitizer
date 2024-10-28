from dataclasses import dataclass
from typing import Callable

from nicegui import ui

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
    value: str = ""


class Meter:
    def __init__(self, digit_names: list[str], name_candidate: str = "") -> None:
        self.digit_names = digit_names
        self.name_candidate = name_candidate
        self.meter = MeterParams()
        self.meter.name = self.name_candidate

    def update_vals(self) -> None:
        digits = self.digits.value if self.digits.value else []
        value = "".join("{" + val + "}" for val in digits)
        self.meter.value = value.replace("{.}", ".")

    def show_new(self) -> MeterParams:
        self.value_container = ui.row().classes("w-full")
        with self.value_container:
            ui.separator()

            with ui.grid(columns="110px auto").classes("w-full gap-2"):
                ui.input("Name").bind_value(self.meter, "name")
                self.digits = (
                    ui.select(
                        self.digit_names + ["."],
                        multiple=True,
                        label="With digits",
                        on_change=self.update_vals,
                    )
                    .classes("w-full")
                    .props("use-chips")
                )
            with ui.grid(columns="auto auto auto auto").classes("w-full gap-2"):
                ui.checkbox("Consistency enabled").bind_value(
                    self.meter, "consistency_enabled"
                )
                ui.checkbox("Allow negative rates").bind_value(
                    self.meter, "allow_negative_rates"
                )
                ui.checkbox("Use previous value filling").bind_value(
                    self.meter, "use_previous_value_filling"
                )
                ui.checkbox("Use extended resolution").bind_value(
                    self.meter, "use_extended_resolution"
                )
            with ui.grid(columns="auto auto auto").classes("w-full gap-2"):
                ui.number("Max rate value", value=0.2, min=0, step=0.01).bind_value(
                    self.meter, "max_rate_value"
                )
                ui.number(
                    "Prevalue from file max age", value=0, min=0, step=1
                ).bind_value(self.meter, "prevalue_from_file_max_age")
                ui.input("Unit", value="㎥")
        return self.meter

    def remove(self) -> None:
        self.value_container.clear()
        self.value_container.delete()


class MeterStep(BaseStep):
    def __init__(
        self,
        name: str,
        get_image_func: Callable[[], str],
        set_image_func: Callable[[str], None],
        get_digit_names_func: Callable[[], list[str]],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            get_image_func=get_image_func,
            set_image_func=set_image_func,
            spinner=spinner,
        )
        self.get_digit_names_func = get_digit_names_func
        self.meters = []
        self.meter_params: list[MeterParams] = []

    def add_meter(self) -> None:
        with self.values_container:
            name = f"Meter{len(self.meters) + 1}"
            meter_container = Meter(self.get_digit_names_func(), name)
            self.meters.append(meter_container)
            meter = meter_container.show_new()
            self.meter_params.append(meter)

    def remove_meter(self) -> None:
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
