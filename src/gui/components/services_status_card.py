"""Services Status Card (Poller & MQTT) for NiceGUI."""

import asyncio
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    CARD_DEFAULT,
)


class ServicesStatusCard:
    """Component rendering Background Poller scheduler and MQTT integration status."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.container: ui.column | None = None
        self._poller_data: dict[str, Any] = {}
        self._mqtt_data: dict[str, Any] = {}

    def render(self) -> None:
        """Render the Services Status Card."""
        with ui.column().classes("w-full gap-4") as self.container:
            self._render_content()

    def update_data(
        self, poller_data: dict[str, Any], mqtt_data: dict[str, Any]
    ) -> None:
        """Update services data and refresh card."""
        self._poller_data = poller_data
        self._mqtt_data = mqtt_data
        if self.container is not None:
            self.container.clear()
            with self.container:
                self._render_content()

    async def fetch_and_update(self) -> None:
        """Fetch fresh poller and MQTT data asynchronously."""
        try:
            p_data, m_data = await asyncio.gather(
                asyncio.to_thread(self.callbacks.get_poller_status),
                asyncio.to_thread(self.callbacks.get_mqtt_status),
            )
            self.update_data(p_data, m_data)
        except Exception as e:
            ui.notify(f"Failed to fetch services status: {e}", type="negative")

    async def trigger_poller(self) -> None:
        """Trigger background poller readout immediately."""
        try:
            res = await asyncio.to_thread(self.callbacks.trigger_poller)
            if res.get("status") == "success" or "successfully" in res.get(
                "message", ""
            ):
                ui.notify("Poller triggered successfully", type="positive")
            else:
                ui.notify(
                    res.get("message", "Trigger request completed"),
                    type="warning",
                )
            await self.fetch_and_update()
        except Exception as e:
            ui.notify(f"Failed to trigger poller: {e}", type="negative")

    async def reload_config(self) -> None:
        """Trigger runtime configuration hot reload from disk."""
        try:
            await asyncio.to_thread(self.callbacks.use_config)
            ui.notify(
                "Configuration hot reloaded successfully into runtime", type="positive"
            )
            await self.fetch_and_update()
        except Exception as e:
            ui.notify(f"Configuration hot reload failed: {e}", type="negative")

    def _render_content(self) -> None:
        p_enabled = self._poller_data.get("enabled", False)
        p_running = self._poller_data.get("running", False)
        p_interval = self._poller_data.get("interval_seconds", 0)
        p_total = self._poller_data.get("total_runs", 0)
        p_success = self._poller_data.get("successful_runs", 0)
        p_failed = self._poller_data.get("failed_runs", 0)
        next_run = self._poller_data.get("next_run")

        m_enabled = self._mqtt_data.get("enabled", False)
        m_connected = self._mqtt_data.get("connected", False)
        m_broker = self._mqtt_data.get("broker", "—")
        m_port = self._mqtt_data.get("port", 1883)
        m_topic = self._mqtt_data.get("topic_prefix", "watermeter")
        m_ha = self._mqtt_data.get("ha_discovery", False)

        with ui.card().classes(CARD_DEFAULT + " gap-4"):
            # Header Row
            with ui.row().classes("w-full justify-between items-center"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("hub", color="cyan").classes("text-xl")
                    ui.label("Services & Integrations").classes(
                        "font-['Outfit'] font-bold text-base text-gray-100"
                    )

                with ui.row().classes("items-center gap-2"):
                    ui.button(
                        icon="refresh",
                        on_click=self.fetch_and_update,
                    ).props(
                        "flat round dense color=cyan text-xs"
                    ).tooltip("Refresh Services Status")

            # 2 Main Columns: Poller Scheduler & MQTT Broker
            with ui.grid(columns=2).classes("w-full gap-4 grid-cols-1 md:grid-cols-2"):
                # 1. Background Poller Card
                with ui.element("div").classes(
                    "p-3.5 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between gap-2"
                ):
                    with ui.row().classes("w-full justify-between items-center"):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.icon("schedule", color="cyan").classes("text-sm")
                            ui.label("Background Poller").classes(
                                "text-xs font-semibold text-gray-300 uppercase tracking-wider"
                            )
                        with ui.element("span").classes(
                            BADGE_SUCCESS
                            if p_running
                            else (BADGE_INFO if not p_enabled else BADGE_ERROR)
                        ):
                            ui.label(
                                "ACTIVE"
                                if p_running
                                else ("DISABLED" if not p_enabled else "STOPPED")
                            )

                    with ui.row().classes("items-baseline gap-2 my-1"):
                        ui.label(f"{p_interval}s").classes(
                            "font-['Outfit'] text-2xl font-bold text-cyan-300"
                        )
                        ui.label("poll interval").classes("text-xs text-gray-400")

                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(
                            f"Next: {str(next_run)[:19] if next_run else '—'}"
                        ).classes("text-[11px] font-mono text-gray-400")
                        ui.button(
                            "Trigger Readout",
                            icon="play_arrow",
                            on_click=self.trigger_poller,
                        ).props("unelevated color=primary size=xs").classes(
                            "font-semibold"
                        )

                    ui.label(
                        f"Runs: {p_total} | Success: {p_success} | Errors: {p_failed}"
                    ).classes("text-[11px] text-gray-400")

                # 2. MQTT & Home Assistant Card
                with ui.element("div").classes(
                    "p-3.5 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between gap-2"
                ):
                    with ui.row().classes("w-full justify-between items-center"):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.icon("sensors", color="teal").classes("text-sm")
                            ui.label("MQTT & Home Assistant").classes(
                                "text-xs font-semibold text-gray-300 uppercase tracking-wider"
                            )
                        with ui.element("span").classes(
                            BADGE_SUCCESS
                            if m_connected
                            else (BADGE_INFO if not m_enabled else BADGE_ERROR)
                        ):
                            ui.label(
                                "CONNECTED"
                                if m_connected
                                else ("DISABLED" if not m_enabled else "DISCONNECTED")
                            )

                    with ui.row().classes("items-baseline gap-2 my-1"):
                        ui.label(f"{m_broker}:{m_port}").classes(
                            "font-['Outfit'] text-lg font-bold text-white truncate"
                        )

                    with ui.row().classes("items-center gap-2"):
                        with ui.element("span").classes(BADGE_INFO):
                            ui.label(f"Topic: {m_topic}/#")
                        if m_ha:
                            with ui.element("span").classes(BADGE_SUCCESS):
                                ui.label("HA Discovery ON")

                    ui.label("Publishes live meter states & metrics").classes(
                        "text-[11px] text-gray-400"
                    )
