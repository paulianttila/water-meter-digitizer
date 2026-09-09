import re
from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from data_classes import MeterConfig

from .step_base import BaseStep

HELP_TEXT = (
    "- **Meter & Digits**: Name your meter and choose digital/analog digits "
    "and decimal points.\n"
    "- **Consistency**: Enable rate limits (`Max rate value`) and negative "
    "rate rejection.\n"
    "- **Previous Value**: Substitute unreadable digits (`N`) with last "
    "known good reading.\n"
    "- **Extended Resolution**: Append fractional sub-digit decimal.\n"
    "- **Unit**: Measurement unit displayed in outputs (e.g. `m³`, `kWh`)."
)


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
    def __init__(
        self,
        digit_names: list[str],
        name_candidate: str = "",
        on_delete: Callable[["Meter"], None] | None = None,
    ) -> None:
        self.digit_names = digit_names
        self.name_candidate = name_candidate
        self.meter = MeterParams()
        self.meter.name = self.name_candidate
        self.on_delete = on_delete
        self.preview_label: ui.label | None = None

    def update_vals(self) -> None:
        digits = self.digits.value if self.digits.value else []
        value = "".join("{" + val + "}" for val in digits)
        self.meter.value = value.replace("{.}", ".")
        if hasattr(self, "preview_label") and self.preview_label is not None:
            unit_str = f" {self.meter.unit}" if self.meter.unit else ""
            self.preview_label.text = f"{self.meter.value or '—'}{unit_str}"

    def show_new(self) -> MeterParams:
        self.value_container = ui.card().classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "p-4 gap-3 my-2 shadow-md"
        )
        with self.value_container:
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("speed", size="sm").classes("text-indigo-400")
                    ui.label(self.name_candidate or "Meter").classes(
                        "font-semibold text-slate-200"
                    )
                with ui.row().classes("items-center gap-2"):
                    ui.label("Pattern:").classes("text-xs text-slate-400 font-mono")
                    self.preview_label = ui.label("—").classes(
                        "text-xs font-mono font-bold text-indigo-300 bg-indigo-950/60 "
                        "px-2 py-0.5 rounded border border-indigo-500/30"
                    )
                    if self.on_delete:
                        ui.button(
                            icon="delete",
                            on_click=lambda: self.on_delete(self),  # type: ignore
                        ).props("flat round dense text-color=negative").tooltip(
                            "Delete this meter"
                        )

            with ui.grid(columns="160px 1fr 100px").classes(
                "w-full gap-3 items-center"
            ):
                ui.input("Meter Name").bind_value(self.meter, "name").classes(
                    "w-full"
                ).tooltip(
                    "Unique logical name for this meter (e.g. main, total, digital)"
                )
                self.digits = (
                    ui.select(
                        [*self.digit_names, "."],
                        multiple=True,
                        label="Ordered Digits & Analogs",
                        on_change=self.update_vals,
                    )
                    .classes("w-full")
                    .props("use-chips")
                    .tooltip(
                        "Select ordered sequence of digit/analog ROIs and "
                        "decimal points comprising this meter"
                    )
                )
                ui.input("Unit", value="㎥").bind_value(self.meter, "unit").classes(
                    "w-full"
                ).tooltip("Engineering unit of measurement (e.g. m³, L, kWh)").on(
                    "blur", self.update_vals
                )

            with ui.row().classes("w-full items-center gap-4 flex-wrap text-sm"):
                ui.checkbox("Consistency checks").bind_value(
                    self.meter, "consistency_enabled"
                ).tooltip(
                    "Validate rate of change against max rate to reject "
                    "outlier misreadings"
                )
                ui.checkbox("Allow negative rates").bind_value(
                    self.meter, "allow_negative_rates"
                ).tooltip("Allow consumption to decrease between readouts")
                ui.checkbox("Use previous value").bind_value(
                    self.meter, "use_previous_value"
                ).tooltip(
                    "Substitute unreadable digits ('N') with digits from the "
                    "previous valid reading"
                )
                ui.checkbox("Extended resolution").bind_value(
                    self.meter, "use_extended_resolution"
                ).tooltip(
                    "Append fractional decimal from lowest significant digit "
                    "or analog dial"
                )

            with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                ui.number("Max Rate (/min)", value=0.2, min=0, step=0.01).bind_value(
                    self.meter, "max_rate_value"
                ).classes("w-36").tooltip(
                    "Maximum allowed consumption increase per reading/minute before "
                    "flagging as inconsistent"
                )
                ui.number("Prevalue Max Age (min)", value=0, min=0, step=1).bind_value(
                    self.meter, "prevalue_from_file_max_age"
                ).classes("w-44").tooltip(
                    "Maximum age in minutes for reading prevalue from persistent file "
                    "(0 = unlimited)"
                )

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
        self.meters: list[Meter] = []
        self.meter_params: list[MeterParams] = []

    def _delete_meter(self, meter_obj: Meter) -> None:
        if meter_obj in self.meters:
            idx = self.meters.index(meter_obj)
            self.meters.remove(meter_obj)
            if idx < len(self.meter_params):
                self.meter_params.pop(idx)
            meter_obj.remove()

    def load_from_config(self, meter_configs: list[MeterConfig]) -> None:
        self.meters.clear()
        self.meter_params.clear()
        if hasattr(self, "values_container") and self.values_container is not None:
            self.values_container.clear()
            for m in meter_configs:
                with self.values_container:
                    meter_container = Meter(
                        self.get_digit_names_func(),
                        m.name,
                        on_delete=self._delete_meter,
                    )
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
            meter_container = Meter(
                self.get_digit_names_func(),
                name,
                on_delete=self._delete_meter,
            )
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
            self.add_help(HELP_TEXT)

            with ui.row().classes("w-full items-center justify-between my-2"):
                ui.label("Configured Meters").classes(
                    "text-sm font-semibold text-slate-300"
                )
                ui.button(
                    "Add Meter",
                    icon="add",
                    on_click=self._add_meter,
                ).props("unelevated dense").classes(
                    "bg-indigo-600 hover:bg-indigo-500 text-white text-xs "
                    "px-3 py-1 font-medium"
                ).tooltip(
                    "Add a new meter definition"
                )

            self.values_container = ui.column().classes("w-full gap-2")

            super().add_navigator(stepper, first_step, last_step)
