import re
from collections.abc import Callable
from dataclasses import dataclass

from nicegui import events, ui

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
    detect_negative_sign: bool = False
    max_rate_value: float = 0.2
    prevalue_from_file_max_age: int = 0
    unit: str = "㎥"
    value: str = ""


class DigitsHolder:
    """Manages ordered sequence of digit/analog tokens and options for a Meter."""

    def __init__(
        self,
        value: list[str] | None = None,
        options: list[str] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._value: list[str] = list(value) if value else []
        self.options: list[str] = list(options) if options else []
        self.on_change = on_change

    @property
    def value(self) -> list[str]:
        return self._value

    @value.setter
    def value(self, val: list[str] | None) -> None:
        self._value = list(val) if val else []
        if self.on_change:
            self.on_change()

    def update(self) -> None:
        if self.on_change:
            self.on_change()


class Meter:
    def __init__(
        self,
        digit_names: list[str],
        name_candidate: str = "",
        on_delete: Callable[["Meter"], None] | None = None,
    ) -> None:
        self.digit_names = list(digit_names)
        self.name_candidate = name_candidate
        self.meter = MeterParams()
        self.meter.name = self.name_candidate
        self.on_delete = on_delete
        self.preview_label: ui.label | None = None
        self.badge_container: ui.row | None = None
        self.digits = DigitsHolder(
            value=[],
            options=list(dict.fromkeys([*self.digit_names, "."])),
            on_change=self.render_inline_badges,
        )

    def render_inline_badges(self) -> None:
        if not hasattr(self, "badge_container") or self.badge_container is None:
            return
        self.badge_container.clear()
        with self.badge_container:
            selected = (
                self.digits.value
                if hasattr(self, "digits") and self.digits.value
                else []
            )
            if not selected:
                ui.label("No sequence configured").classes(
                    "text-xs text-slate-500 italic truncate"
                )
            else:
                for item_name in selected:
                    if item_name == ".":
                        ui.label(".").classes(
                            "px-1.5 py-0.5 text-xs font-mono font-bold bg-amber-500/20 "
                            "text-amber-300 border border-amber-500/30 rounded shrink-0"
                        )
                    else:
                        ui.label(item_name).classes(
                            "px-2 py-0.5 text-xs font-mono font-medium bg-slate-800 "
                            "text-slate-200 border border-slate-700/80 rounded shrink-0"
                        )

    def update_vals(self) -> None:
        digits = (
            self.digits.value if hasattr(self, "digits") and self.digits.value else []
        )
        value = "".join("{" + val + "}" for val in digits)
        self.meter.value = value.replace("{.}", ".")
        if hasattr(self, "preview_label") and self.preview_label is not None:
            unit_str = f" {self.meter.unit}" if self.meter.unit else ""
            self.preview_label.text = f"{self.meter.value or '—'}{unit_str}"
        self.render_inline_badges()

    def update_digit_names(self, digit_names: list[str]) -> None:
        self.digit_names = list(digit_names)
        if hasattr(self, "digits") and self.digits is not None:
            current_values = self.digits.value if self.digits.value else []
            combined = list(dict.fromkeys([*self.digit_names, *current_values, "."]))
            self.digits.options = combined
            self.digits.update()
            self.update_vals()

    def open_order_dialog(self) -> None:
        temp_selected: list[str] = (
            list(self.digits.value)
            if hasattr(self, "digits") and self.digits.value
            else []
        )
        all_options = list(dict.fromkeys([*self.digit_names, *temp_selected, "."]))

        with (
            ui.dialog() as order_dialog,
            ui.card().classes(
                "bg-slate-900 border border-white/10 rounded-2xl p-5 "
                "max-w-xl w-full gap-3.5 shadow-2xl"
            ),
        ):
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2.5"):
                    with ui.element("div").classes(
                        "w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 "
                        "flex items-center justify-center text-indigo-400"
                    ):
                        ui.icon("format_list_numbered", size="sm")
                    with ui.column().classes("gap-0"):
                        ui.label(
                            f"Configure Sequence: {self.meter.name or 'Meter'}"
                        ).classes("text-sm font-bold text-slate-100")
                        ui.label(
                            "Add, remove, and drag items to set the reading sequence"
                        ).classes("text-xs text-slate-400")
                ui.button(icon="close", on_click=order_dialog.close).props(
                    "flat round dense text-color=slate-400"
                )

            # Dialog preview row
            with ui.row().classes(
                "w-full items-center justify-between px-3 py-1.5 bg-slate-950/60 "
                "border border-slate-800 rounded-lg text-xs"
            ):
                ui.label("Pattern Preview:").classes("text-slate-400 font-mono")
                dialog_preview = ui.label("—").classes(
                    "font-mono font-bold text-indigo-300"
                )

            def update_dialog_preview() -> None:
                val = "".join("{" + t + "}" for t in temp_selected).replace("{.}", ".")
                unit_str = f" {self.meter.unit}" if self.meter.unit else ""
                dialog_preview.text = f"{val or '—'}{unit_str}"

            # 2-column container: Left = Available, Right = Selected Order
            with ui.grid(columns="1fr 1.3fr").classes("w-full gap-3"):
                # Available column
                with ui.column().classes("gap-1.5"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Available Items").classes(
                            "text-xs font-semibold text-slate-300"
                        )
                        ui.button(
                            "Add All",
                            icon="playlist_add",
                            on_click=lambda: add_all_available(),
                        ).props("flat dense").classes(
                            "text-indigo-400 hover:text-indigo-300 text-xs px-1.5 py-0"
                        ).tooltip(
                            "Add all available items to sequence"
                        )

                    avail_container = ui.column().classes(
                        "w-full gap-1 p-1.5 bg-slate-950/40 border border-slate-800/80 "
                        "rounded-xl min-h-[220px] max-h-[280px] overflow-y-auto"
                    )

                # Selected order column
                with ui.column().classes("gap-1.5"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Selected Sequence").classes(
                            "text-xs font-semibold text-slate-300"
                        )
                        ui.button(
                            "Clear All",
                            icon="clear_all",
                            on_click=lambda: clear_all_selected(),
                        ).props("flat dense").classes(
                            "text-rose-400 hover:text-rose-300 text-xs px-1.5 py-0"
                        ).tooltip(
                            "Clear all selected items"
                        )

                    selected_container = ui.column().classes(
                        "w-full gap-1 p-1.5 bg-slate-950/40 border border-slate-800/80 "
                        "rounded-xl min-h-[220px] max-h-[280px] overflow-y-auto"
                    )

            def on_sort_end(e: events.SortableEventArguments) -> None:
                if (
                    e.old_index is not None
                    and e.new_index is not None
                    and e.old_index != e.new_index
                ):
                    item = temp_selected.pop(e.old_index)
                    temp_selected.insert(e.new_index, item)
                    refresh_lists()

            selected_container.make_sortable(
                handle=".drag-handle",
                animation=0.15,
                ghost_class="opacity-40",
                on_end=on_sort_end,
            )

            def add_item(item: str) -> None:
                temp_selected.append(item)
                refresh_lists()

            def remove_item(index: int) -> None:
                if 0 <= index < len(temp_selected):
                    temp_selected.pop(index)
                    refresh_lists()

            def add_all_available() -> None:
                for opt in all_options:
                    if opt not in temp_selected:
                        temp_selected.append(opt)
                refresh_lists()

            def clear_all_selected() -> None:
                temp_selected.clear()
                refresh_lists()

            def refresh_lists() -> None:
                avail_container.clear()
                with avail_container:
                    available = [
                        opt
                        for opt in all_options
                        if opt == "." or opt not in temp_selected
                    ]
                    if not available:
                        ui.label("All items added").classes(
                            "text-xs text-slate-500 italic p-3 text-center w-full"
                        )
                    else:
                        for opt in available:
                            with ui.row().classes(
                                "w-full items-center justify-between px-2.5 py-1.5 "
                                "bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 "
                                "rounded-lg transition-colors flex-nowrap"
                            ):
                                with ui.row().classes(
                                    "items-center gap-1.5 flex-nowrap min-w-0"
                                ):
                                    if opt == ".":
                                        ui.label(".").classes(
                                            "w-4 h-4 flex items-center justify-center "
                                            "text-xs font-mono font-bold bg-amber-500/20 text-amber-300 "
                                            "border border-amber-500/30 rounded shrink-0"
                                        )
                                        ui.label("Decimal (.)").classes(
                                            "text-xs font-mono font-medium text-amber-300 truncate"
                                        )
                                    else:
                                        ui.icon("pin", size="xs").classes(
                                            "text-indigo-400 shrink-0"
                                        )
                                        ui.label(opt).classes(
                                            "text-xs font-mono font-medium text-slate-200 truncate"
                                        )
                                ui.button(
                                    icon="add",
                                    on_click=lambda o=opt: add_item(o),
                                ).props(
                                    "flat round dense text-color=indigo-400 size=sm"
                                ).classes(
                                    "shrink-0"
                                ).tooltip(
                                    f"Add {opt} to sequence"
                                )

                selected_container.clear()
                with selected_container:
                    if not temp_selected:
                        ui.label(
                            "No items selected. Click '+' on the left to add items."
                        ).classes(
                            "text-xs text-slate-500 italic p-3 text-center w-full"
                        )
                    else:
                        for idx, item_name in enumerate(temp_selected):
                            with ui.row().classes(
                                "w-full items-center justify-between px-2.5 py-1.5 "
                                "bg-slate-900/90 border border-slate-700/60 rounded-lg "
                                "hover:border-slate-600 transition-colors flex-nowrap"
                            ):
                                with ui.row().classes(
                                    "items-center gap-2 flex-nowrap min-w-0"
                                ):
                                    ui.icon("drag_indicator", size="xs").classes(
                                        "drag-handle text-slate-500 hover:text-slate-300 "
                                        "cursor-grab active:cursor-grabbing shrink-0"
                                    ).tooltip("Drag to reorder")
                                    ui.label(f"#{idx + 1}").classes(
                                        "text-[10px] font-mono font-bold bg-indigo-500/20 "
                                        "text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-500/30 shrink-0"
                                    )
                                    if item_name == ".":
                                        ui.label(".").classes(
                                            "w-4 h-4 flex items-center justify-center "
                                            "text-xs font-mono font-bold bg-amber-500/20 text-amber-300 "
                                            "border border-amber-500/30 rounded shrink-0"
                                        )
                                        ui.label("Decimal (.)").classes(
                                            "text-xs font-mono font-medium text-amber-300 truncate"
                                        )
                                    else:
                                        ui.label(item_name).classes(
                                            "text-xs font-mono font-semibold text-slate-200 truncate"
                                        )
                                ui.button(
                                    icon="close",
                                    on_click=lambda i=idx: remove_item(i),
                                ).props(
                                    "flat round dense text-color=negative size=sm"
                                ).classes(
                                    "shrink-0"
                                ).tooltip(
                                    f"Remove {item_name}"
                                )

                update_dialog_preview()

            refresh_lists()

            # Dialog footer
            with ui.row().classes(
                "w-full justify-end items-center gap-2 pt-2 border-t border-white/5"
            ):
                ui.button("Cancel", on_click=order_dialog.close).props(
                    "flat dense"
                ).classes("text-slate-300 px-3")

                def on_apply() -> None:
                    self.digits.value = list(temp_selected)
                    self.update_vals()
                    order_dialog.close()

                ui.button(
                    "Apply Order",
                    icon="check",
                    on_click=on_apply,
                ).props("unelevated dense").classes(
                    "bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 shadow-md"
                )

        order_dialog.open()

    def show_new(self) -> MeterParams:
        self.value_container = ui.card().classes(
            "w-full bg-slate-900/60 border border-white/10 rounded-xl "
            "p-3.5 gap-2.5 my-1.5 shadow-md"
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

            with ui.grid(columns="150px 1fr 90px").classes(
                "w-full gap-2.5 items-center"
            ):
                ui.input("Meter Name").props("dense outlined").bind_value(
                    self.meter, "name"
                ).classes("w-full").tooltip(
                    "Unique logical name for this meter (e.g. main, total, digital)"
                )

                with ui.element("div").classes(
                    "w-full flex items-center justify-between gap-2 px-2.5 py-1 "
                    "rounded-lg border border-slate-700/80 bg-slate-950/40 min-h-[38px] overflow-hidden"
                ):
                    self.badge_container = ui.row().classes(
                        "items-center gap-1.5 flex-1 min-w-0 overflow-x-auto no-scrollbar py-0.5"
                    )
                    self.render_inline_badges()

                    ui.button(
                        "Edit Order",
                        icon="tune",
                        on_click=self.open_order_dialog,
                    ).props("unelevated dense").classes(
                        "bg-indigo-600/90 hover:bg-indigo-500 text-white text-xs px-2.5 py-1 "
                        "font-medium shrink-0 rounded shadow-sm"
                    ).tooltip(
                        "Open dialog to arrange the ordered sequence of digits, analogs, and decimal points"
                    )

                ui.input("Unit", value="㎥").props("dense outlined").bind_value(
                    self.meter, "unit"
                ).classes("w-full").tooltip(
                    "Engineering unit of measurement (e.g. m³, L, kWh)"
                ).on(
                    "blur", self.update_vals
                )

            with ui.row().classes("w-full items-center gap-3 flex-wrap text-xs"):
                ui.checkbox("Consistency checks").props("dense").bind_value(
                    self.meter, "consistency_enabled"
                ).tooltip(
                    "Validate rate of change against max rate to reject "
                    "outlier misreadings"
                )
                ui.checkbox("Allow negative rates").props("dense").bind_value(
                    self.meter, "allow_negative_rates"
                ).tooltip("Allow consumption to decrease between readouts")
                ui.checkbox("Use previous value").props("dense").bind_value(
                    self.meter, "use_previous_value"
                ).tooltip(
                    "Substitute unreadable digits ('?') with digits from the "
                    "previous valid reading"
                )
                ui.checkbox("Extended resolution").props("dense").bind_value(
                    self.meter, "use_extended_resolution"
                ).tooltip(
                    "Append fractional decimal from lowest significant digit "
                    "or analog dial"
                )
                ui.checkbox("Detect negative sign (-)").props("dense").bind_value(
                    self.meter, "detect_negative_sign"
                ).tooltip("Detect '-' sign for negative flow on leading digital digits")

            with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                ui.number("Max Rate (/min)", value=0.2, min=0, step=0.01).props(
                    "dense outlined"
                ).bind_value(self.meter, "max_rate_value").classes("w-36").tooltip(
                    "Maximum allowed consumption increase per reading/minute before "
                    "flagging as inconsistent"
                )
                ui.number("Prevalue Max Age (min)", value=0, min=0, step=1).props(
                    "dense outlined"
                ).bind_value(self.meter, "prevalue_from_file_max_age").classes(
                    "w-44"
                ).tooltip(
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

    def refresh_digit_names(self) -> None:
        current_names = (
            self.get_digit_names_func() if self.get_digit_names_func is not None else []
        )
        for meter in self.meters:
            meter.update_digit_names(current_names)

    def load_from_config(self, meter_configs: list[MeterConfig]) -> None:
        self.meters.clear()
        self.meter_params.clear()
        if hasattr(self, "values_container") and self.values_container is not None:
            self.values_container.clear()
            current_digit_names = (
                self.get_digit_names_func()
                if self.get_digit_names_func is not None
                else []
            )
            for m in meter_configs:
                with self.values_container:
                    tokens = (
                        [
                            t.strip("{}") if t.startswith("{") else t
                            for t in re.findall(r"\{[^{}]+\}|\.", m.format)
                        ]
                        if m.format
                        else m.value_names
                    )
                    available_names = list(
                        dict.fromkeys([*current_digit_names, *(tokens or [])])
                    )
                    meter_container = Meter(
                        available_names,
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
                    meter_param.detect_negative_sign = m.detect_negative_sign
                    meter_param.max_rate_value = m.max_rate_value
                    meter_param.prevalue_from_file_max_age = (
                        m.pre_value_from_file_max_age
                    )
                    meter_param.unit = m.unit
                    meter_container.digits.value = tokens if tokens else m.value_names
                    meter_container.update_vals()
                    self.meter_params.append(meter_param)

    def _add_meter(self) -> None:
        with self.values_container:
            name = f"Meter{len(self.meters) + 1}"
            current_digit_names = (
                self.get_digit_names_func()
                if self.get_digit_names_func is not None
                else []
            )
            meter_container = Meter(
                current_digit_names,
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
