"""Previous Values & Baseline Manager Page for NiceGUI."""

import asyncio
from typing import Any

from nicegui import ui

from callbacks import Callbacks


class PreviousValuesPage:
    """Page allowing users to inspect and calibrate baseline meter values."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.table_container: ui.column | None = None
        self.meter_select: ui.select | None = None
        self.value_input: ui.input | None = None

    def refresh_table(self) -> None:
        """Fetch saved baseline values and update table and selector."""
        if self.table_container is None:
            return

        self.table_container.clear()
        cfg = self.callbacks.get_config()
        configured_meters = [m.name for m in getattr(cfg, "meter_configs", [])]
        if not configured_meters:
            configured_meters = ["total"]

        if self.meter_select is not None:
            self.meter_select.options = configured_meters
            if self.meter_select.value not in configured_meters:
                self.meter_select.value = configured_meters[0]

        values_dict = self.callbacks.get_previous_values()

        with self.table_container:
            if not values_dict:
                ui.label(
                    "No previous baseline values saved in prevalue.ini yet."
                ).classes("text-xs text-gray-400 p-4 italic")
                return

            rows = [
                {
                    "id": section,
                    "meter": section,
                    "value": info.get("value", "—"),
                    "time": info.get("time", "—"),
                }
                for section, info in values_dict.items()
            ]
            columns: list[dict[str, Any]] = [
                {
                    "name": "meter",
                    "label": "METER",
                    "field": "meter",
                    "required": True,
                    "align": "left",
                    "sortable": True,
                    "classes": "font-semibold text-cyan-300 text-xs",
                    "headerClasses": "text-gray-400 font-semibold text-xs",
                },
                {
                    "name": "value",
                    "label": "BASELINE VALUE",
                    "field": "value",
                    "required": True,
                    "align": "left",
                    "sortable": True,
                    "classes": "font-mono font-bold text-white text-xs",
                    "headerClasses": "text-gray-400 font-semibold text-xs",
                },
                {
                    "name": "time",
                    "label": "LAST UPDATED",
                    "field": "time",
                    "required": True,
                    "align": "left",
                    "sortable": True,
                    "classes": "font-mono text-gray-400 text-xs",
                    "headerClasses": "text-gray-400 font-semibold text-xs",
                },
            ]

            with ui.element("div").classes(
                "w-full rounded-xl bg-slate-950/80 border border-white/5 overflow-hidden"
            ):
                table = (
                    ui.table(
                        columns=columns,
                        rows=rows,
                        row_key="id",
                        pagination=10,
                    )
                    .props("dark flat dense wrap-cells")
                    .classes("w-full")
                )
                table.add_slot(
                    "body-cell-meter",
                    """
                    <q-td :props="props">
                        <div class="flex items-center gap-2">
                            <span class="font-semibold text-cyan-300">{{ props.value }}</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                                SAVED
                            </span>
                        </div>
                    </q-td>
                    """,
                )

    async def _save_baseline(self) -> None:
        if not self.meter_select or not self.meter_select.value:
            ui.notify("Please select a meter name", type="warning")
            return
        if not self.value_input or not self.value_input.value:
            ui.notify("Please enter a numeric baseline value", type="warning")
            return

        meter_name = str(self.meter_select.value).strip()
        meter_val = str(self.value_input.value).strip()

        try:
            val_float = float(meter_val)
            if val_float < 0:
                ui.notify("Baseline value cannot be negative", type="negative")
                return
        except ValueError:
            ui.notify("Value must be a valid number", type="negative")
            return

        try:
            res = await asyncio.to_thread(
                self.callbacks.set_previous_value, meter_name, meter_val
            )
            if res.get("status") == "success":
                ui.notify(
                    f"Baseline for '{meter_name}' updated to {meter_val}!",
                    type="positive",
                )
                if self.value_input:
                    self.value_input.value = ""
                self.refresh_table()
            else:
                ui.notify(
                    res.get("message", "Failed to update baseline"), type="negative"
                )
        except Exception as e:
            ui.notify(f"Error updating baseline: {e}", type="negative")

    def show(self) -> None:
        with ui.column().classes("w-full max-w-4xl gap-4"):
            # Header
            with ui.row().classes("w-full justify-between items-center"):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 "
                        "flex items-center justify-center shadow-lg shadow-cyan-500/10"
                    ):
                        ui.icon("tune", color="cyan").classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label("Baseline & Previous Values Manager").classes(
                            "text-h5 font-['Outfit']"
                        )
                        ui.label(
                            "Inspect and calibrate meter baseline readings from prevalue.ini"
                        ).classes("text-xs text-gray-400")

                ui.button(
                    "Refresh",
                    icon="refresh",
                    on_click=self.refresh_table,
                ).props("outline dense color=cyan").classes("text-xs")

            # Table Card
            with ui.card().classes(
                "w-full p-5 bg-slate-900 border border-white/10 rounded-2xl gap-3"
            ):
                ui.label("Stored Meter Baselines (prevalue.ini)").classes(
                    "text-xs font-semibold text-gray-300 uppercase tracking-wider"
                )
                self.table_container = ui.column().classes("w-full gap-1")

            # Manual Set Form Card
            with ui.card().classes(
                "w-full p-5 rounded-2xl bg-slate-900 border border-white/10 gap-3"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("edit_calendar", color="cyan").classes("text-lg")
                    ui.label("Manually Calibrate Baseline Reading").classes(
                        "font-['Outfit'] font-bold text-sm text-gray-200"
                    )

                with ui.row().classes("w-full gap-3 items-center"):
                    self.meter_select = (
                        ui.select(options=["total"], value="total", label="Meter Name")
                        .props("outlined dense options-dense")
                        .classes("flex-1 text-sm bg-slate-950/60")
                    )

                    self.value_input = (
                        ui.input(label="New Baseline Value (e.g. 123.456)")
                        .props("outlined dense type=number step=any")
                        .classes("flex-1 text-sm font-mono bg-slate-950/60")
                    )

                    ui.button(
                        "Save Baseline",
                        icon="save",
                        on_click=self._save_baseline,
                    ).props("unelevated color=primary").classes(
                        "px-4 font-semibold shadow-md shadow-blue-500/20"
                    )

            # Initial load
            self.refresh_table()
