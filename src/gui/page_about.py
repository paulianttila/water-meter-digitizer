import logging
import platform
import sys
from typing import Any

import nicegui
from nicegui import ui

from callbacks import Callbacks
from gui.theme import CARD_DEFAULT, FONT_MONO_VALUE, ROW_ACTIONS, ROW_HEADER
from main import VERSION
from utils.diagnostics import get_process_memory_info, get_system_info

logger = logging.getLogger(__name__)


class AboutPage:
    """About & System Diagnostics Page."""

    def __init__(self, callbacks: Callbacks | None = None) -> None:
        self.callbacks = callbacks

    def _get_diagnostics_data(self) -> dict[str, Any]:
        """Collect full diagnostics information for telemetry."""
        sys_info = get_system_info(VERSION)
        mem_info = get_process_memory_info()

        health_data: dict[str, Any] = {}
        if self.callbacks:
            try:
                health_data = self.callbacks.get_health_data() or {}
            except Exception as e:
                health_data = {"error": str(e)}

        return {
            "version": VERSION,
            "system": sys_info,
            "python": {
                "version": sys.version.split()[0],
                "platform": f"{platform.system()} {platform.release()}",
                "architecture": platform.machine(),
            },
            "memory": mem_info,
            "health": health_data,
        }

    def show(self) -> None:
        diag = self._get_diagnostics_data()
        health = diag.get("health", {})
        uptime_info = health.get("uptime", {})
        memory_info = diag.get("memory", {})

        with ui.column().classes(
            "w-full h-full flex flex-col gap-4 p-4 overflow-y-auto"
        ):
            # Header Hero Card
            with (
                ui.element("div").classes(
                    "w-full p-6 rounded-2xl "
                    "bg-gradient-to-tr from-blue-900/40 via-cyan-900/30 to-slate-900/60 "
                    "border border-cyan-500/30 shadow-xl shadow-cyan-500/10 "
                    "flex flex-col md:flex-row justify-between items-start md:items-center gap-6"
                ),
                ui.row().classes("items-center gap-4"),
            ):
                with ui.element("div").classes(
                    "w-16 h-16 rounded-2xl "
                    "bg-gradient-to-tr from-blue-600 to-cyan-400 "
                    "flex items-center justify-center shadow-lg "
                    "shadow-cyan-500/30 shrink-0"
                ):
                    ui.icon("water_drop", color="white").classes("text-3xl")

                with ui.column().classes("gap-1"):
                    with ui.row().classes(ROW_ACTIONS):
                        ui.label("About Water Meter Digitizer").classes(
                            "text-h4 font-['Outfit'] font-bold text-white leading-none"
                        )
                        ui.label(f"v{VERSION}").classes(
                            "text-xs font-bold text-cyan-400 bg-cyan-500/15 "
                            "border border-cyan-500/30 px-2.5 py-0.5 rounded-full"
                        )
                    ui.label(
                        "Edge-AI automated utility meter digitizer using neural network inference, "
                        "affine geometric alignment, and predecessor odometer consistency deduction."
                    ).classes("text-sm text-gray-300 max-w-2xl")

            # System Telemetry Metric Cards
            with ui.row().classes("w-full gap-3 flex-wrap"):
                # Application Version
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("APPLICATION VERSION").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("verified", color="cyan").classes("text-sm")
                    ui.label(f"v{VERSION}").classes(f"{FONT_MONO_VALUE} text-white")
                    ui.label("Edge AI System").classes("text-xs text-gray-400")

                # Python & Platform
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("RUNTIME ENVIRONMENT").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("terminal", color="purple").classes("text-sm")
                    ui.label(f"Python {diag['python']['version']}").classes(
                        f"{FONT_MONO_VALUE} text-purple-400"
                    )
                    ui.label(
                        f"{diag['python']['platform']} ({diag['python']['architecture']})"
                    ).classes("text-xs text-gray-400 truncate")

                # Inference Engine
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("INFERENCE ENGINE").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("memory", color="cyan").classes("text-sm")
                    ui.label("Google LiteRT").classes(
                        f"{FONT_MONO_VALUE} text-cyan-400"
                    )
                    ui.label("Quantized CNN Interpreter Pool").classes(
                        "text-xs text-gray-400"
                    )

                # Frontend Framework
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("FRONTEND FRAMEWORK").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("web", color="emerald").classes("text-sm")
                    ui.label(f"NiceGUI {nicegui.__version__}").classes(
                        f"{FONT_MONO_VALUE} text-emerald-400"
                    )
                    ui.label("FastAPI & Vue Quasar Engine").classes(
                        "text-xs text-gray-400"
                    )

                # Memory Footprint
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("PROCESS MEMORY").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("data_usage", color="amber").classes("text-sm")
                    ui.label(f"{memory_info.get('rss_mb', 0):.1f} MB").classes(
                        f"{FONT_MONO_VALUE} text-amber-400"
                    )
                    ui.label(
                        f"Peak RSS: {memory_info.get('peak_rss_mb', 0):.1f} MB"
                    ).classes("text-xs text-gray-400")

                # Process Uptime
                with ui.element("div").classes(f"{CARD_DEFAULT} flex-1 min-w-[200px]"):
                    with ui.row().classes(f"{ROW_HEADER} mb-1"):
                        ui.label("SYSTEM UPTIME").classes(
                            "text-xs font-semibold text-gray-400 tracking-wider"
                        )
                        ui.icon("schedule", color="rose").classes("text-sm")
                    ui.label(f"{uptime_info.get('uptime_human', 'Active')}").classes(
                        f"{FONT_MONO_VALUE} text-rose-400"
                    )
                    ui.label(
                        f"Started: {uptime_info.get('started_at', 'Now')[:19]}"
                    ).classes("text-xs text-gray-400 truncate")
