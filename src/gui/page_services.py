"""Services, System Diagnostics, and Integrations Dashboard Page for NiceGUI."""

import asyncio
import logging

from nicegui import ui

from callbacks import Callbacks
from gui.components import page_header
from gui.components.diagnostics_card import DiagnosticsCard
from gui.components.leak_monitor_card import LeakMonitorCard
from gui.components.services_status_card import ServicesStatusCard

logger = logging.getLogger(__name__)


class ServicesPage:
    """Page rendering System Diagnostics, Zero-Flow Leak Monitor, Poller, and MQTT services."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.diagnostics_card = DiagnosticsCard(self.callbacks)
        self.leak_card = LeakMonitorCard(self.callbacks)
        self.services_card = ServicesStatusCard(self.callbacks)
        self.spinner: ui.spinner | None = None

    async def show(self) -> None:
        """Render the Services and Diagnostics page."""
        with page_header(
            title="Services & System Diagnostics",
            subtitle="Manage background daemons, logs, and live metrics",
            icon="dns",
            color="emerald",
            classes="w-full justify-between items-center mb-2",
        ):
            self.spinner = ui.spinner("dots", size="md", color="cyan")
            self.spinner.visible = False

            ui.button(
                "Refresh All", icon="refresh", on_click=self.fetch_all_telemetry
            ).props("unelevated color=primary").classes("shadow-md shadow-blue-500/20")

        with ui.column().classes("w-full gap-4 pb-6"):
            # 1. System Diagnostics Card
            self.diagnostics_card.render()

            # 2. Zero-Flow Leak Monitor Card
            self.leak_card.render()

            # 3. Services & Integrations Card (Poller & MQTT)
            self.services_card.render()

        await self.fetch_all_telemetry()

    async def fetch_all_telemetry(self) -> None:
        """Fetch fresh telemetry for all diagnostics, leak tracker, and service cards."""
        if self.spinner:
            self.spinner.visible = True

        try:
            h_data = await asyncio.to_thread(self.callbacks.get_health_data)
            self.diagnostics_card.update_data(h_data)
        except Exception:
            logger.warning("Failed to fetch health data telemetry", exc_info=True)

        try:
            l_data = await asyncio.to_thread(self.callbacks.get_leak_status)
            self.leak_card.update_data(l_data)
        except Exception:
            logger.warning("Failed to fetch leak status telemetry", exc_info=True)

        try:
            p_data, m_data = await asyncio.gather(
                asyncio.to_thread(self.callbacks.get_poller_status),
                asyncio.to_thread(self.callbacks.get_mqtt_status),
            )
            self.services_card.update_data(p_data, m_data)
        except Exception:
            logger.warning("Failed to fetch poller/MQTT telemetry", exc_info=True)

        if self.spinner:
            self.spinner.visible = False
