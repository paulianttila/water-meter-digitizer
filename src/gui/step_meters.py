import re
from data_classes import MeterConfig
from dataclasses import dataclass
from typing import Callable

from nicegui import ui

from .step_base import BaseStep


@dataclass
class MeterParams:
    name: str = ""
    consistency_enabled: bool = False
    allow_negative_rates: bool = False
    use_previous_value: bool = False
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
                ui.checkbox("Use previous value").bind_value(
                    self.meter, "use_previous_value"
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
                ui.input("Unit", value="㎥").bind_value(self.meter, "unit")
        self.update_vals()
        return self.meter

    def remove(self) -> None:
        self.value_container.clear()
        self.value_container.delete()


class MeterStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        get_digit_names_func: Callable[[], list[str]],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.get_digit_names_func = get_digit_names_func
        self.meters = []
        self.meter_params: list[MeterParams] = []

    def load_from_config(self, meter_configs: list[MeterConfig]) -> None:
        self.meters.clear()
        self.meter_params.clear()
        if hasattr(self, "values_container") and self.values_container is not None:
            self.values_container.clear()
            for m in meter_configs:
                with self.values_container:
                    meter_container = Meter(self.get_digit_names_func(), m.name)
                    self.meters.append(meter_container)
                    meter_param = meter_container.show_new()
                    # Populate values
                    meter_param.name = m.name
                    meter_param.consistency_enabled = m.consistency_enabled
                    meter_param.allow_negative_rates = m.allow_negative_rates
                    meter_param.use_previous_value = m.use_previous_value
                    meter_param.use_extended_resolution = m.use_extended_resolution
                    meter_param.max_rate_value = m.max_rate_value
                    meter_param.prevalue_from_file_max_age = (
                        m.pre_value_from_file_max_age
                    )
                    meter_param.unit = m.unit
                    # Parse {digit1}{digit2}... into select list values
                    tokens = (
                        [
                            t.strip("{}") if t.startswith("{") else t
                            for t in re.findall(r"\{[^{}]+\}|\.", m.format)
                        ]
                        if m.format
                        else m.value_names
                    )
                    meter_container.digits.value = tokens if tokens else m.value_names
                    meter_container.update_vals()
                    self.meter_params.append(meter_param)

    def _add_meter(self) -> None:
        with self.values_container:
            name = f"Meter{len(self.meters) + 1}"
            meter_container = Meter(self.get_digit_names_func(), name)
            self.meters.append(meter_container)
            meter = meter_container.show_new()
            self.meter_params.append(meter)

    def _remove_meter(self) -> None:
        if self.meters:
            meter_container: Meter = self.meters.pop()
            meter_container.remove()
        if self.meter_params:
            self.meter_params.pop()

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            self.add_help(
                """
- **Meter Name & Digits**: Name your meter and select which digital/analog digits and decimal points form its value.
- **Consistency**: Enable rate limits (`Max rate value`) and negative rate rejection.
- **Previous Value**: Automatically substitute unreadable digits (`N`) with the last known good reading.
- **Extended Resolution**: Append fractional sub-digit decimal places from the last analog dial.
- **Unit**: Measurement unit displayed in outputs (e.g. `m³`, `kWh`).
                """
            )
            self.values_container = ui.row().classes("w-full")
            ui.separator()
            with ui.row():
                ui.button("Meter", icon="add", on_click=self._add_meter).tooltip(
                    "Add meter value"
                )
                ui.button(
                    "Meter", icon="remove", on_click=self._remove_meter
                ).bind_enabled_from(
                    self, "values_container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Remove last meter value"
                )

            super().add_navigator(stepper, first_step, last_step)
