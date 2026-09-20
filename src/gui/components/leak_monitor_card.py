"""Zero-Flow Leak Monitor Component for NiceGUI."""

import asyncio
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.components.async_data_loader import async_fetch_and_render
from gui.components.page_header import card_header
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
    CARD_DEFAULT,
    FONT_MONO_VALUE,
    HEADING_SECTION,
    HEADING_SUBSECTION,
    PANEL_INNER,
    ROW_HEADER,
    TEXT_MONO_MUTED,
)


class LeakMonitorCard:
    """Component rendering Zero-Flow continuous flow tracking and leak reset controls."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.container: ui.column | None = None
        self._data: dict[str, Any] = {}

    def render(self) -> None:
        """Render the Leak Monitor Card."""
        with ui.column().classes("w-full gap-4") as self.container:
            self._render_content()

    def update_data(self, data: dict[str, Any] | Any) -> None:
        """Update tracker state data and refresh view."""
        if hasattr(data, "to_dict"):
            self._data = data.to_dict()
        elif hasattr(data, "model_dump"):
            self._data = data.model_dump()
        else:
            self._data = data
        if self.container is not None:
            self.container.clear()
            with self.container:
                self._render_content()

    async def fetch_and_update(self) -> None:
        """Fetch fresh leak status asynchronously from backend."""
        await async_fetch_and_render(
            fetch_fn=self.callbacks.get_leak_status,
            render_fn=self.update_data,
            error_message="Failed to fetch leak status",
            suppress_errors=True,
        )

    async def reset_leak_state(self) -> None:
        """Trigger leak state reset and refresh card."""
        try:
            res = await asyncio.to_thread(self.callbacks.reset_leak_status)
            ui.notify("Zero-flow leak state reset successfully", type="positive")
            self.update_data(res)
        except Exception as e:
            ui.notify(f"Failed to reset leak monitor: {e}", type="negative")

    def _render_content(self) -> None:
        if not self._data:
            with ui.card().classes(CARD_DEFAULT):
                with ui.row().classes(ROW_HEADER):
                    ui.label("Leak & Zero-Flow Monitor").classes(
                        f"{HEADING_SECTION} text-gray-200"
                    )
                    ui.button(
                        "Fetch Status",
                        icon="refresh",
                        on_click=self.fetch_and_update,
                    ).props("flat dense color=cyan text-xs")
                ui.label("No zero-flow status available.").classes(
                    "text-xs text-gray-400 mt-2"
                )
            return

        enabled = self._data.get("enabled", False)
        state = str(self._data.get("state", "OK")).upper()
        meter_name = self._data.get("meter_name", "total")
        flow_rate = self._data.get("current_flow_rate", 0.0)
        flow_duration = self._data.get("current_flow_duration_seconds", 0.0)
        flow_vol = self._data.get("current_flow_volume", 0.0)
        consec_zeroes = self._data.get("consecutive_zero_readings", 0)
        last_zero_time = self._data.get("last_zero_flow_time")
        recent_events = self._data.get("recent_events", [])

        if not enabled:
            badge_cls = BADGE_INFO
            state_label = "DISABLED"
        elif "LEAK" in state:
            badge_cls = BADGE_ERROR
            state_label = "LEAK DETECTED"
        elif "FLOW" in state:
            badge_cls = BADGE_WARNING
            state_label = "FLOW ACTIVE"
        else:
            badge_cls = BADGE_SUCCESS
            state_label = "NORMAL (ZERO-FLOW)"

        with ui.card().classes(f"{CARD_DEFAULT} gap-4"):
            # Header Row
            with card_header(
                title="Leak & Zero-Flow Monitor",
                icon="water_damage",
                color="amber",
                badge_text=state_label,
                badge_cls=badge_cls,
            ):
                ui.button(
                    "Reset Leak State",
                    icon="restart_alt",
                    on_click=self.reset_leak_state,
                ).props("unelevated color=negative size=sm").classes(
                    "text-xs font-semibold"
                )
                ui.button(
                    icon="refresh",
                    on_click=self.fetch_and_update,
                ).props(
                    "flat round dense color=cyan text-xs"
                ).tooltip("Refresh Leak Monitor")

            # Telemetry Metrics Grid
            with ui.grid(columns=4).classes(
                "w-full gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
            ):
                # 1. Monitored Meter & State
                with ui.element("div").classes(PANEL_INNER):
                    ui.label("Monitored Meter").classes(f"{HEADING_SUBSECTION} mb-1")
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(meter_name).classes(f"{FONT_MONO_VALUE} text-cyan-300")
                    ui.label(f"State: {state}").classes(TEXT_MONO_MUTED)

                # 2. Current Flow Rate
                with ui.element("div").classes(PANEL_INNER):
                    ui.label("Current Flow Rate").classes(f"{HEADING_SUBSECTION} mb-1")
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(f"{flow_rate:.3f}").classes(
                            f"{FONT_MONO_VALUE} text-white"
                        )
                        ui.label("m³/h").classes("text-xs text-gray-400")
                    ui.label(f"Consecutive Zeroes: {consec_zeroes}").classes(
                        TEXT_MONO_MUTED
                    )

                # 3. Continuous Duration
                with ui.element("div").classes(PANEL_INNER):
                    ui.label("Continuous Duration").classes(
                        f"{HEADING_SUBSECTION} mb-1"
                    )
                    mins, secs = divmod(int(flow_duration), 60)
                    hrs, mins = divmod(mins, 60)
                    dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(dur_str).classes(
                            f"{FONT_MONO_VALUE} text-amber-300 font-mono"
                        )
                    last_z_str = str(last_zero_time)[:19] if last_zero_time else "—"
                    ui.label(f"Last Zero: {last_z_str}").classes(
                        f"{TEXT_MONO_MUTED} truncate"
                    )

                # 4. Continuous Flow Volume
                with ui.element("div").classes(PANEL_INNER):
                    ui.label("Accumulated Volume").classes(f"{HEADING_SUBSECTION} mb-1")
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(f"{flow_vol:.3f}").classes(
                            f"{FONT_MONO_VALUE} text-rose-300"
                        )
                        ui.label("m³").classes("text-xs text-gray-400")
                    liters = flow_vol * 1000.0
                    ui.label(f"≈ {liters:.1f} Liters").classes(TEXT_MONO_MUTED)

            # Historical Events Expandable Section
            if recent_events:
                with (
                    ui.expansion(
                        f"Recent Leak Events ({len(recent_events)})",
                        icon="history",
                    ).classes(
                        "w-full bg-slate-950/40 rounded-xl text-xs text-gray-300"
                    ),
                    ui.column().classes("w-full gap-2 p-2"),
                ):
                    for evt in recent_events[:5]:
                        st_time = evt.get("start_time", "—")
                        dur = evt.get("duration_seconds", 0.0)
                        vol = evt.get("leaked_volume", 0.0)
                        res = evt.get("resolved", False)
                        with ui.row().classes(
                            "w-full justify-between items-center p-2 rounded-lg bg-slate-900 border border-white/5"
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(f"Started: {st_time}").classes(
                                    "font-mono text-gray-300"
                                )
                                ui.label(
                                    f"Duration: {dur:.1f}s | Volume: {vol:.3f} m³"
                                ).classes("text-[11px] text-gray-400")
                            with ui.element("span").classes(
                                BADGE_SUCCESS if res else BADGE_ERROR
                            ):
                                ui.label("Resolved" if res else "ACTIVE")
