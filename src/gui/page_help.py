import json
import logging
from pathlib import Path
from typing import Any

from nicegui import ui

import gui.theme as theme
from callbacks import Callbacks
from gui.base_page import BasePage
from gui.components import page_header
from main import VERSION
from utils.diagnostics import get_process_memory_info, get_system_info

logger = logging.getLogger(__name__)

HELP_DIR = Path(__file__).parent.parent / "web" / "static" / "help"


def _load_help(filename: str) -> str:
    """Load markdown help content from static files."""
    path = HELP_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


class HelpPage(BasePage):
    """Comprehensive Help, Documentation, and Support Center."""

    def __init__(self, callbacks: Callbacks | None = None) -> None:
        super().__init__(callbacks)

    def _generate_support_bundle(self) -> str:
        """Generate a structured Markdown diagnostics bundle for GitHub issues or troubleshooting."""
        sys_info = get_system_info(VERSION)
        mem_info = get_process_memory_info()

        health_data: dict[str, Any] = {}
        if self.callbacks:
            try:
                health_data = self.callbacks.get_health_data() or {}
            except Exception as e:
                health_data = {"error": str(e)}

        bundle_lines = [
            "### 🛠️ Water Meter Digitizer - Support Diagnostic Bundle",
            f"- **Version**: `v{VERSION}`",
            f"- **Python**: `{sys_info.get('python_version', 'Unknown')}`",
            f"- **Platform**: `{sys_info.get('platform', 'Unknown')}`",
            f"- **Process Memory**: RSS `{mem_info.get('rss_mb', 0)} MB` (Peak: `{mem_info.get('peak_rss_mb', 0)} MB`)",
        ]

        if health_data:
            uptime = health_data.get("uptime", {})
            camera = health_data.get("camera", {})
            models = health_data.get("models", {})
            bundle_lines.extend(
                [
                    f"- **System Status**: `{health_data.get('status', 'unknown')}`",
                    f"- **Uptime**: `{uptime.get('uptime_human', 'N/A')}` (Started: `{uptime.get('started_at', 'N/A')}`)",
                    f"- **Camera Reachable**: `{camera.get('reachable', False)}` (Latency: `{camera.get('latency_ms', 'N/A')} ms`, Status: `{camera.get('status_code', 'N/A')}`)",
                    f"- **Digital Model**: `{models.get('digital', {}).get('path', 'N/A')}` (Exists: `{models.get('digital', {}).get('exists', False)}`)",
                    f"- **Analog Model**: `{models.get('analog', {}).get('path', 'N/A')}` (Exists: `{models.get('analog', {}).get('exists', False)}`)",
                    f"- **Average Inference Latency**: `{models.get('avg_inference_ms', 'N/A')} ms`",
                ]
            )

        bundle_lines.extend(
            [
                "",
                "```json",
                json.dumps(
                    {
                        "version": VERSION,
                        "system": sys_info,
                        "memory": mem_info,
                        "health": health_data,
                    },
                    indent=2,
                ),
                "```",
            ]
        )
        return "\n".join(bundle_lines)

    async def show(self) -> None:
        with (
            ui.dialog() as support_dialog,
            ui.card().classes(f"{theme.DIALOG_CARD} max-w-3xl flex-col"),
        ):
            with ui.row().classes(theme.ROW_HEADER):
                with ui.row().classes("items-center gap-2.5"):
                    with ui.element("div").classes(
                        "w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center"
                    ):
                        ui.icon("bug_report", color="cyan").classes("text-lg")
                    ui.label("Support Diagnostic Bundle").classes(
                        f"{theme.HEADING_SECTION} text-white"
                    )
                ui.button(icon="close", on_click=support_dialog.close).props(
                    "flat round dense size=sm color=gray aria-label='Close dialog'"
                )

            ui.label(
                "Formatted Markdown diagnostics report ready for pasting into GitHub Issues, forums, or troubleshooting discussions."
            ).classes("text-xs text-gray-400")

            bundle_textarea = (
                ui.textarea(value="")
                .props("readonly outlined")
                .classes(
                    "w-full font-mono text-xs bg-slate-950/80 text-cyan-300 rounded-lg p-2 border border-white/10 h-72 resize-none"
                )
            )

            with ui.row().classes(
                f"{theme.ROW_HEADER} pt-2 border-t border-white/10 gap-2"
            ):
                with ui.row().classes(theme.ROW_ACTIONS):
                    ui.button(
                        "Download Bundle (.md)",
                        icon="file_download",
                        on_click=lambda: ui.download(
                            bundle_textarea.value.encode("utf-8"),
                            f"watermeter-support-bundle-v{VERSION}.md",
                        ),
                    ).props("unelevated dense color=cyan text-color=dark").classes(
                        "font-semibold px-3"
                    )

                    ui.button(
                        "Copy to Clipboard",
                        icon="content_copy",
                        on_click=lambda: theme.copy_to_clipboard(
                            bundle_textarea.value,
                            notify_message="Support diagnostic bundle copied to clipboard!",
                        ),
                    ).props("outline dense color=cyan").classes("font-semibold px-3")

                ui.button("Close", on_click=support_dialog.close).props(
                    "flat dense color=gray"
                )

        def _open_support_dialog() -> None:
            bundle_text = self._generate_support_bundle()
            bundle_textarea.value = bundle_text
            theme.copy_to_clipboard(
                bundle_text,
                notify_message="Support bundle copied to clipboard!",
            )
            support_dialog.open()

        with ui.column().classes(
            "w-full h-full flex flex-col gap-3 p-4 overflow-hidden"
        ):
            # Header Hero Bar
            with page_header(
                title="Help & Documentation",
                subtitle="Guides, calibration best practices, and integration specifications",
                icon="help_outline",
                color="cyan",
                classes="w-full justify-between items-center shrink-0 mb-1",
            ):
                ui.link(
                    "Wiki Documentation",
                    "https://github.com/paulianttila/water-meter-digitizer/wiki",
                    new_tab=True,
                ).classes(
                    "text-xs font-semibold text-gray-300 hover:text-white px-3 py-1.5 "
                    "rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors flex items-center gap-1.5"
                )

                with (
                    ui.button(
                        "Support Bundle",
                        icon="bug_report",
                        on_click=_open_support_dialog,
                    )
                    .props("outline dense size=sm color=cyan")
                    .classes("font-semibold")
                ):
                    ui.tooltip(
                        "View, download, or copy diagnostics report formatted for GitHub issues"
                    )

                ui.label("Documentation v" + VERSION).classes(
                    "font-mono text-xs text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-3 py-1.5 rounded-full font-semibold hidden md:block"
                )

            # 3 Navigation Tabs
            with (
                ui.tabs().classes(
                    "w-full bg-slate-900/90 border border-white/10 rounded-xl p-1 shrink-0"
                ) as tabs,
                ui.row().classes("w-full gap-2"),
            ):
                tab_workflow = ui.tab(
                    "Setup Workflow & Pipeline", icon="checklist"
                ).classes("font-semibold text-sm")
                tab_canvas = ui.tab(
                    "Calibration & Canvas Tools", icon="center_focus_strong"
                ).classes("font-semibold text-sm")
                tab_integrations = ui.tab(
                    "Integrations & API Specs", icon="hub"
                ).classes("font-semibold text-sm")

            with ui.tab_panels(tabs, value=tab_workflow).classes(
                "w-full flex-1 bg-transparent p-0 overflow-y-auto"
            ):
                # -------------------------------------------------------------
                # TAB 1: Setup Workflow & Pipeline
                # -------------------------------------------------------------
                with ui.tab_panel(tab_workflow).classes(
                    "w-full h-full p-0 flex flex-col gap-4"
                ):
                    # Top Pipeline Architecture Banner
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/70 border border-emerald-500/20 rounded-xl flex flex-col gap-2.5 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("account_tree", color="emerald").classes("text-lg")
                            ui.label("Runtime Architecture").classes(
                                "text-xs font-bold text-emerald-400 tracking-wider uppercase"
                            )
                        ui.markdown(_load_help("pipeline_architecture.md")).classes(
                            "text-xs text-gray-300 w-full"
                        )

                    # 2-Column Split: Wizard Steps (Left) + Quick Reference Cheat-Sheet (Right)
                    with ui.element("div").classes(
                        "grid grid-cols-1 lg:grid-cols-3 gap-4 items-start"
                    ):
                        # Left Column (2/3 width): 9-Step Linear Progression
                        with (
                            ui.column().classes("lg:col-span-2 gap-3 w-full"),
                            ui.card().classes(
                                "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                            ),
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("format_list_numbered", color="cyan").classes(
                                    "text-lg"
                                )
                                ui.label("Setup Wizard Progression").classes(
                                    "text-sm font-bold text-white font-['Outfit']"
                                )
                            ui.markdown(_load_help("wizard_steps.md")).classes(
                                "text-xs text-gray-300 w-full leading-relaxed"
                            )

                        # Right Column (1/3 width): Quick Reference Cheat-Sheet
                        with ui.column().classes("lg:col-span-1 gap-3 w-full"):
                            # Cheat Sheet Card 1: Marker Placement Rules
                            with ui.card().classes(
                                "w-full p-4 bg-slate-900/80 border border-emerald-500/20 rounded-xl flex flex-col gap-2.5"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("check_circle", color="emerald").classes(
                                        "text-base"
                                    )
                                    ui.label("Marker Rules").classes(
                                        "text-xs font-bold text-emerald-400 uppercase tracking-wider"
                                    )
                                ui.markdown(_load_help("calibration_tips.md")).classes(
                                    "text-xs text-gray-300"
                                )

                            # Cheat Sheet Card 2: Deep Documentation Links
                            with ui.card().classes(
                                "w-full p-4 bg-slate-900/80 border border-cyan-500/20 rounded-xl flex flex-col gap-2.5"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("menu_book", color="cyan").classes(
                                        "text-base"
                                    )
                                    ui.label("Wiki Deep Dives").classes(
                                        "text-xs font-bold text-cyan-400 uppercase tracking-wider"
                                    )
                                wiki_links = [
                                    (
                                        "Getting Started & Hardware",
                                        "https://github.com/paulianttila/water-meter-digitizer/wiki/Getting-Started-&-Hardware",
                                    ),
                                    (
                                        "Setup & Calibration Manual",
                                        "https://github.com/paulianttila/water-meter-digitizer/wiki/Setup-Wizard-&-Calibration",
                                    ),
                                    (
                                        "Smart Home & API Reference",
                                        "https://github.com/paulianttila/water-meter-digitizer/wiki/Integrations-&-API-Reference",
                                    ),
                                    (
                                        "Architecture & Neural Models",
                                        "https://github.com/paulianttila/water-meter-digitizer/wiki/Architecture-&-Neural-Networks",
                                    ),
                                    (
                                        "Configuration & Storage",
                                        "https://github.com/paulianttila/water-meter-digitizer/wiki/Configuration-&-Storage-Manual",
                                    ),
                                ]
                                for title, url in wiki_links:
                                    ui.link(title, url, new_tab=True).classes(
                                        "text-xs text-cyan-400 hover:text-cyan-200 underline flex items-center gap-1"
                                    )

                # -------------------------------------------------------------
                # TAB 2: Calibration & Canvas Tools
                # -------------------------------------------------------------
                with (
                    ui.tab_panel(tab_canvas).classes(
                        "w-full h-full p-0 flex flex-col gap-4"
                    ),
                    ui.element("div").classes(
                        "grid grid-cols-1 lg:grid-cols-2 gap-4 items-start"
                    ),
                ):
                    # Left Column: Marker Best Practices
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("center_focus_strong", color="emerald").classes(
                                "text-xl"
                            )
                            ui.label("Alignment Best Practices").classes(
                                "text-base font-bold text-white font-['Outfit']"
                            )
                        ui.markdown(_load_help("calibration_tips.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # Right Column: Canvas Controls & Model Guide
                    with ui.column().classes("w-full gap-4"):
                        with ui.card().classes(
                            "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("touch_app", color="purple").classes("text-xl")
                                ui.label("Canvas Controls").classes(
                                    "text-base font-bold text-white font-['Outfit']"
                                )
                            ui.markdown(
                                _load_help("canvas_keyboard_shortcuts.md")
                            ).classes("text-xs text-gray-300 leading-relaxed")

                        with ui.card().classes(
                            "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-2.5"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("memory", color="cyan").classes("text-base")
                                ui.label("Neural Network Models").classes(
                                    "text-xs font-bold text-cyan-400 uppercase tracking-wider"
                                )
                            ui.markdown(_load_help("roi_best_practices.md")).classes(
                                "text-xs text-gray-300 leading-relaxed"
                            )

                # -------------------------------------------------------------
                # TAB 3: Integrations & API Specs
                # -------------------------------------------------------------
                with ui.tab_panel(tab_integrations).classes(
                    "w-full h-full p-0 flex flex-col gap-4"
                ):
                    # Top Integrations Summary Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("home", color="amber").classes("text-lg")
                            ui.label("Smart Home & Automations").classes(
                                "text-sm font-bold text-white font-['Outfit']"
                            )
                        ui.markdown(_load_help("home_assistant.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # MQTT Schema Reference Table Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("hub", color="cyan").classes("text-lg")
                                ui.label("MQTT Topics & Telemetry").classes(
                                    "text-sm font-bold text-white font-['Outfit']"
                                )
                            ui.label("Prefix configured in [MQTT] section").classes(
                                "text-xs text-gray-400"
                            )
                        ui.markdown(_load_help("mqtt_integration.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # REST Endpoints Table Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("api", color="emerald").classes("text-lg")
                                ui.label("Primary REST API Endpoints").classes(
                                    "text-sm font-bold text-white font-['Outfit']"
                                )
                            ui.link(
                                "Open Interactive API Console", "/api_console"
                            ).classes(
                                "text-xs font-semibold text-cyan-400 hover:underline"
                            )
                        ui.markdown(_load_help("api_reference.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )
