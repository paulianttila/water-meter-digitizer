"""Services Status Card (Poller & MQTT) for NiceGUI."""

import asyncio
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.components.async_data_loader import async_fetch_and_render
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
    ROW_ACTIONS,
    ROW_HEADER,
    ROW_ITEMS_CENTER,
    TEXT_MONO_MUTED,
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
        self,
        poller_data: dict[str, Any] | Any,
        mqtt_data: dict[str, Any] | Any,
    ) -> None:
        """Update services data and refresh card."""
        self._poller_data = (
            poller_data.model_dump()
            if hasattr(poller_data, "model_dump")
            else poller_data
        )
        self._mqtt_data = (
            mqtt_data.model_dump() if hasattr(mqtt_data, "model_dump") else mqtt_data
        )
        if self.container is not None:
            self.container.clear()
            with self.container:
                self._render_content()

    async def _fetch_status_data(self) -> tuple[Any, Any]:
        return await asyncio.gather(
            asyncio.to_thread(self.callbacks.get_poller_status),
            asyncio.to_thread(self.callbacks.get_mqtt_status),
        )

    async def fetch_and_update(self) -> None:
        """Fetch fresh poller and MQTT data asynchronously."""
        await async_fetch_and_render(
            fetch_fn=self._fetch_status_data,
            render_fn=lambda data: self.update_data(data[0], data[1]),
            error_message="Failed to fetch services status",
            suppress_errors=True,
        )

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
        p_last_error = self._poller_data.get("last_error", "")
        next_run = self._poller_data.get("next_run")

        m_enabled = self._mqtt_data.get("enabled", False)
        m_connected = self._mqtt_data.get("connected", False)
        m_broker = self._mqtt_data.get("broker", "—")
        m_port = self._mqtt_data.get("port", 1883)
        m_topic = self._mqtt_data.get("topic_prefix", "watermeter")
        m_ha = self._mqtt_data.get("ha_discovery", False)

        with ui.card().classes(f"{CARD_DEFAULT} gap-4"):
            # Header Row
            with ui.row().classes(ROW_HEADER):
                with ui.row().classes(ROW_ACTIONS):
                    ui.icon("hub", color="cyan").classes("text-xl")
                    ui.label("Services & Integrations").classes(HEADING_SECTION)

                with ui.row().classes(ROW_ACTIONS):
                    ui.button(
                        icon="refresh",
                        on_click=self.fetch_and_update,
                    ).props(
                        "flat round dense color=cyan text-xs"
                    ).tooltip("Refresh Services Status")

            # 2 Main Columns: Poller Scheduler & MQTT Broker
            with ui.grid(columns=2).classes("w-full gap-4 grid-cols-1 md:grid-cols-2"):
                # 1. Background Poller Card
                with ui.element("div").classes(PANEL_INNER):
                    with ui.row().classes(ROW_HEADER):
                        with ui.row().classes(ROW_ITEMS_CENTER):
                            ui.icon("schedule", color="cyan").classes("text-sm")
                            ui.label("Background Poller").classes(HEADING_SUBSECTION)

                        if p_running:
                            if p_last_error:
                                p_badge_cls = (
                                    BADGE_ERROR if p_success == 0 else BADGE_WARNING
                                )
                                p_badge_label = (
                                    "ERROR" if p_success == 0 else "DEGRADED"
                                )
                            else:
                                p_badge_cls = BADGE_SUCCESS
                                p_badge_label = "ACTIVE"
                        else:
                            if not p_enabled:
                                p_badge_cls = BADGE_INFO
                                p_badge_label = "DISABLED"
                            else:
                                p_badge_cls = BADGE_WARNING
                                p_badge_label = "STOPPED"

                        with ui.element("span").classes(p_badge_cls):
                            ui.label(p_badge_label)

                    with ui.row().classes("items-baseline gap-2 my-1"):
                        ui.label(f"{p_interval}s").classes(
                            f"{FONT_MONO_VALUE} text-cyan-300"
                        )
                        ui.label("poll interval").classes("text-xs text-gray-400")

                    with ui.row().classes(ROW_HEADER):
                        ui.label(
                            f"Next: {str(next_run)[:19] if next_run else '—'}"
                        ).classes(TEXT_MONO_MUTED)
                        ui.button(
                            "Trigger Readout",
                            icon="play_arrow",
                            on_click=self.trigger_poller,
                        ).props("unelevated color=primary size=xs").classes(
                            "font-semibold"
                        )

                    # Last error alert banner
                    if p_last_error:
                        with ui.element("div").classes(
                            "w-full p-2.5 rounded-lg bg-rose-950/50 border border-rose-500/40 "
                            "text-rose-200 text-xs flex items-start gap-2 mt-1"
                        ):
                            ui.icon("error", color="rose").classes(
                                "text-sm mt-0.5 shrink-0"
                            )
                            with ui.column().classes("gap-0.5 overflow-hidden"):
                                ui.label("Last Execution Error:").classes(
                                    "font-semibold text-rose-300 text-[11px]"
                                )
                                ui.label(p_last_error).classes(
                                    "font-mono text-[10px] break-all leading-tight text-rose-200"
                                )

                    with ui.row().classes(
                        "items-center gap-1 text-[11px] text-gray-400 flex-wrap"
                    ):
                        ui.label(f"Runs: {p_total} | Success: {p_success} |")
                        err_color = (
                            "text-rose-400 font-semibold"
                            if p_failed > 0
                            else "text-gray-400"
                        )
                        ui.label(f"Errors: {p_failed}").classes(err_color)

                # 2. MQTT & Home Assistant Card
                with ui.element("div").classes(PANEL_INNER):
                    with ui.row().classes(ROW_HEADER):
                        with ui.row().classes(ROW_ITEMS_CENTER):
                            ui.icon("sensors", color="teal").classes("text-sm")
                            ui.label("MQTT & Home Assistant").classes(
                                HEADING_SUBSECTION
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
