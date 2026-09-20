"""Previous Values & Baseline Manager Page for NiceGUI."""

import asyncio
import contextlib
import csv
import io
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.base_page import BasePage
from gui.components import open_code_inspect_dialog, page_header


class PreviousValuesPage(BasePage):
    """Page allowing users to inspect and calibrate baseline meter values."""

    def __init__(self, callbacks: Callbacks) -> None:
        super().__init__(callbacks)
        self.cards_container: ui.column | None = None
        self.table_container: ui.column | None = None
        self.meter_select: ui.select | None = None
        self.value_input: ui.input | None = None
        self.search_input: ui.input | None = None
        self._live_readouts: dict[str, str] = {}

    def _fetch_live_readings(self) -> dict[str, str]:
        """Attempt to fetch live meter readings from digitizer callbacks."""
        results: dict[str, str] = {}
        with contextlib.suppress(Exception):
            meter_data = self.callbacks.get_meter_data(saveimages=False)
            if meter_data and getattr(meter_data, "meters", None):
                for m in meter_data.meters:
                    if hasattr(m, "name") and hasattr(m, "value"):
                        results[m.name] = str(m.value)
        return results

    def refresh_table(self) -> None:
        """Fetch saved baseline values and update cards, selector, and table."""
        cfg = self.callbacks.get_config()
        configured_meters = [m.name for m in getattr(cfg, "meter_configs", [])]
        if not configured_meters:
            configured_meters = ["total"]

        meter_fallback_flags: dict[str, bool] = {}
        for m in getattr(cfg, "meter_configs", []):
            meter_fallback_flags[m.name] = getattr(m, "use_previous_value", False)

        if self.meter_select is not None:
            self.meter_select.options = configured_meters
            if self.meter_select.value not in configured_meters:
                self.meter_select.value = configured_meters[0]

        values_dict = self.callbacks.get_previous_values()
        self._live_readouts = self._fetch_live_readings()

        # 1. Refresh Meter Hero Cards
        if self.cards_container is not None:
            self.cards_container.clear()
            with self.cards_container, ui.row().classes("w-full gap-4 items-stretch"):
                for m_name in configured_meters:
                    is_fallback_active = meter_fallback_flags.get(m_name, False)
                    baseline_info = values_dict.get(m_name, {})
                    b_val_str = baseline_info.get("value", "—")
                    b_time_str = baseline_info.get("time", "Not calibrated")
                    live_val_str = self._live_readouts.get(m_name, "—")

                    # Calculate delta drift if both are numeric
                    delta_label = "No live delta"
                    delta_cls = "text-slate-400 bg-white/5 border-white/10"
                    if b_val_str != "—" and live_val_str != "—":
                        try:
                            b_f = float(b_val_str)
                            l_f = float(live_val_str)
                            diff = l_f - b_f
                            if diff >= 0:
                                delta_label = f"+{diff:.4f} m³ accumulated"
                                delta_cls = (
                                    "text-emerald-400 bg-emerald-500/10 "
                                    "border-emerald-500/30"
                                )
                            else:
                                delta_label = (
                                    f"{diff:.4f} m³ (Live lower than baseline)"
                                )
                                delta_cls = (
                                    "text-amber-400 bg-amber-500/10 "
                                    "border-amber-500/30 font-semibold"
                                )
                        except ValueError:
                            pass

                    with (
                        ui.card()
                        .classes(
                            "flex-1 min-w-[280px] p-4 bg-slate-900/90 border "
                            "border-white/10 rounded-2xl flex flex-col justify-between gap-3 shadow-lg"
                        )
                        .props(f'id="meter-baseline-card-{m_name}"')
                    ):
                        # Card Header
                        with ui.row().classes("w-full justify-between items-center"):
                            with ui.row().classes("items-center gap-2"):
                                with ui.element("div").classes(
                                    "w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400"
                                ):
                                    ui.icon("water_drop", size="xs")
                                with ui.column().classes("gap-0"):
                                    ui.label(m_name).classes(
                                        "font-bold text-sm text-slate-100 uppercase"
                                    )
                                    ui.label(f"Updated: {b_time_str}").classes(
                                        "text-[10px] text-slate-400 font-mono"
                                    )

                            if is_fallback_active:
                                ui.label("🟢 Fallback Active").classes(
                                    "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                )
                            else:
                                ui.label("⚪ Standby").classes(
                                    "text-[10px] px-2 py-0.5 rounded-full font-semibold bg-white/5 text-slate-400 border border-white/10"
                                )

                        # Values Strip
                        with ui.row().classes(
                            "w-full justify-between items-end bg-slate-950/70 p-3 rounded-xl border border-white/5"
                        ):
                            with ui.column().classes("gap-0.5"):
                                ui.label("SAVED BASELINE").classes(
                                    "text-[10px] text-slate-400 font-semibold uppercase tracking-wider"
                                )
                                ui.label(b_val_str).classes(
                                    "font-mono font-bold text-lg text-cyan-300"
                                )

                            with ui.column().classes("gap-0.5 items-end text-right"):
                                ui.label("LATEST LIVE").classes(
                                    "text-[10px] text-slate-400 font-semibold uppercase tracking-wider"
                                )
                                ui.label(live_val_str).classes(
                                    "font-mono font-bold text-base text-slate-200"
                                )

                        # Delta Pill & Action
                        with ui.row().classes(
                            "w-full justify-between items-center gap-2 pt-1"
                        ):
                            ui.label(delta_label).classes(
                                f"text-[11px] px-2 py-1 rounded-lg border {delta_cls} truncate flex-1"
                            )

                            def make_sync_handler(target_m: str, target_live: str):
                                async def do_sync():
                                    if target_live == "—" or not target_live:
                                        ui.notify(
                                            f"No live reading available for '{target_m}'",
                                            type="warning",
                                        )
                                        return
                                    res = await asyncio.to_thread(
                                        self.callbacks.set_previous_value,
                                        target_m,
                                        target_live,
                                    )
                                    if res.get("status") == "success":
                                        ui.notify(
                                            f"Synced '{target_m}' baseline to {target_live}!",
                                            type="positive",
                                        )
                                        self.refresh_table()
                                    else:
                                        ui.notify(
                                            res.get("message", "Sync failed"),
                                            type="negative",
                                        )

                                return do_sync

                            ui.button(
                                "Sync Live",
                                icon="sync",
                                on_click=make_sync_handler(m_name, live_val_str),
                            ).props("unelevated dense size=sm color=cyan-8").classes(
                                "text-white text-xs font-semibold px-2.5 py-1"
                            ).tooltip(
                                f"Set baseline for '{m_name}' to current live reading ({live_val_str})"
                            )

        # 2. Refresh Table
        if self.table_container is not None:
            self.table_container.clear()
            with self.table_container:
                if not values_dict:
                    with ui.column().classes(
                        "w-full py-8 items-center justify-center text-slate-400 gap-1"
                    ):
                        ui.icon("inventory_2", size="lg")
                        ui.label(
                            "No baseline values saved in prevalue.ini yet."
                        ).classes("text-sm")
                    return

                query = ""
                if self.search_input and isinstance(self.search_input.value, str):
                    query = self.search_input.value.strip().lower()

                rows = []
                for section, info in values_dict.items():
                    val = str(info.get("value", "—"))
                    t = str(info.get("time", "—"))
                    live_v = self._live_readouts.get(section, "—")

                    if (
                        query
                        and query not in section.lower()
                        and query not in val.lower()
                        and query not in t.lower()
                    ):
                        continue

                    rows.append(
                        {
                            "id": section,
                            "meter": section,
                            "value": val,
                            "live": live_v,
                            "time": t,
                        }
                    )

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
                        "name": "live",
                        "label": "LATEST LIVE",
                        "field": "live",
                        "required": True,
                        "align": "left",
                        "sortable": True,
                        "classes": "font-mono text-slate-300 text-xs",
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

    def _apply_stepper_delta(self, delta: float) -> None:
        """Apply numeric increment/decrement to the current input value."""
        if not self.value_input:
            return
        curr_str = str(self.value_input.value or "").strip()
        try:
            curr_val = float(curr_str) if curr_str else 0.0
            new_val = max(0.0, curr_val + delta)
            self.value_input.value = f"{new_val:.4f}".rstrip("0").rstrip(".")
        except ValueError:
            self.value_input.value = f"{max(0.0, delta):.4f}"

    def _use_live_in_form(self) -> None:
        """Populate the calibration input with the selected meter's live reading."""
        if not self.meter_select or not self.value_input:
            return
        meter_name = str(self.meter_select.value)
        live_val = self._live_readouts.get(meter_name, "")
        if live_val and live_val != "—":
            self.value_input.value = live_val
            ui.notify(
                f"Loaded live reading ({live_val}) for '{meter_name}'",
                type="info",
            )
        else:
            ui.notify(f"No live reading available for '{meter_name}'", type="warning")

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
                    res.get("message", "Failed to update baseline"),
                    type="negative",
                )
        except Exception as e:
            ui.notify(f"Error updating baseline: {e}", type="negative")

    def _export_csv(self) -> None:
        """Export all baseline records as CSV download."""
        values_dict = self.callbacks.get_previous_values()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Meter", "BaselineValue", "LatestLive", "LastUpdated"])
        for m_name, info in values_dict.items():
            writer.writerow(
                [
                    m_name,
                    info.get("value", ""),
                    self._live_readouts.get(m_name, ""),
                    info.get("time", ""),
                ]
            )
        csv_bytes = output.getvalue().encode("utf-8")
        ui.download(csv_bytes, filename="meter_baselines.csv")
        ui.notify("Downloading meter_baselines.csv", type="info")

    def _open_raw_prevalue_modal(self) -> None:
        """Open raw prevalue.ini file viewer."""
        values_dict = self.callbacks.get_previous_values()
        lines = []
        for m_name, info in values_dict.items():
            lines.append(f"[{m_name}]")
            lines.append(f"Value = {info.get('value', '')}")
            lines.append(f"Time = {info.get('time', '')}")
            lines.append("")
        raw_text = "\n".join(lines).strip()

        open_code_inspect_dialog(
            title="Raw prevalue.ini Inspector",
            code_content=raw_text,
            language="ini",
            caption="/config/prevalue.ini",
            icon="description",
            max_width="max-w-2xl",
        )

    async def show(self) -> None:
        with ui.column().classes("w-full max-w-5xl gap-4 p-4"):
            # Header
            with page_header(
                title="Baseline & Previous Values Manager",
                subtitle="Inspect, compare, and calibrate meter baselines with live synchronization",
                icon="tune",
                color="cyan",
            ):
                ui.button(
                    "Export CSV",
                    icon="download",
                    on_click=self._export_csv,
                ).props("flat dense color=grey-4 size=sm").tooltip(
                    "Download all meter baselines as CSV"
                )
                ui.button(
                    "Inspect Raw",
                    icon="visibility",
                    on_click=self._open_raw_prevalue_modal,
                ).props("flat dense color=grey-4 size=sm").tooltip(
                    "Inspect raw prevalue.ini text structure"
                )
                ui.button(
                    "Refresh",
                    icon="refresh",
                    on_click=self.refresh_table,
                ).props("outline dense color=cyan size=sm").classes("text-xs")

            # Hero Meter Telemetry Cards Container
            self.cards_container = ui.column().classes("w-full gap-3")

            # Manual Set & Stepper Form Card
            with ui.card().classes(
                "w-full p-5 rounded-2xl bg-slate-900 border border-white/10 gap-3"
            ):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("edit_calendar", color="cyan").classes("text-lg")
                        ui.label("Calibrate Meter Baseline").classes(
                            "font-['Outfit'] font-bold text-sm text-gray-200"
                        )
                    with ui.row().classes("items-center gap-1.5"):
                        ui.button(
                            "Use Live Value",
                            icon="sync",
                            on_click=self._use_live_in_form,
                        ).props("flat dense size=xs color=cyan").tooltip(
                            "Fill input with live digitizer reading"
                        )
                        ui.button(
                            "Reset to 0.000",
                            icon="restart_alt",
                            on_click=lambda: setattr(
                                self.value_input, "value", "0.0000"
                            ),
                        ).props("flat dense size=xs color=grey-4")

                with ui.row().classes("w-full gap-3 items-center"):
                    self.meter_select = (
                        ui.select(
                            options=["total"],
                            value="total",
                            label="Target Meter",
                        )
                        .props("outlined dense options-dense")
                        .classes("w-48 text-sm bg-slate-950/60")
                    )

                    self.value_input = (
                        ui.input(label="New Baseline Value (e.g. 123.4560)")
                        .props("outlined dense type=number step=any debounce=300")
                        .classes("flex-1 text-sm font-mono bg-slate-950/60")
                    )

                    ui.button(
                        "Save Baseline",
                        icon="save",
                        on_click=self._save_baseline,
                    ).props("unelevated color=primary").classes(
                        "px-4 font-semibold shadow-md shadow-blue-500/20"
                    )

                # Rapid Stepper Chips Row
                with ui.row().classes("items-center gap-2 pt-1 flex-wrap"):
                    ui.label("Quick Steppers:").classes(
                        "text-xs text-slate-400 font-semibold"
                    )
                    for delta_val in [0.001, 0.01, 0.1, 1.0, 10.0]:
                        ui.button(
                            f"+{delta_val}",
                            on_click=lambda d=delta_val: self._apply_stepper_delta(d),
                        ).props("outline dense size=xs color=cyan").classes(
                            "font-mono text-xs"
                        )
                    for delta_val in [-1.0, -0.1]:
                        ui.button(
                            f"{delta_val}",
                            on_click=lambda d=delta_val: self._apply_stepper_delta(d),
                        ).props("outline dense size=xs color=amber").classes(
                            "font-mono text-xs"
                        )

            # Table Card with Search
            with ui.card().classes(
                "w-full p-5 bg-slate-900 border border-white/10 rounded-2xl gap-3"
            ):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Stored Meter Baselines (prevalue.ini)").classes(
                        "text-xs font-semibold text-gray-300 uppercase tracking-wider"
                    )
                    self.search_input = (
                        ui.input(
                            placeholder="Search meters or baseline values...",
                            on_change=self.refresh_table,
                        )
                        .props("dense outlined debounce=300")
                        .classes("w-64 text-xs bg-slate-950/60")
                    )
                    self.search_input.add_slot(
                        "prepend",
                        '<q-icon name="search" size="xs" class="text-gray-400" />',
                    )

                self.table_container = ui.column().classes("w-full gap-1")

            # Initial load
            self.refresh_table()
