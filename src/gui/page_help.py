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
            "w-full h-full flex flex-col gap-3 p-4 overflow-hidden min-h-0 min-w-0 max-w-full"
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
                    "w-full bg-slate-900/90 border border-white/10 rounded-xl p-1 shrink-0 min-w-0"
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

            with (
                ui.tab_panels(tabs, value=tab_workflow)
                .classes(
                    "w-full flex-1 min-h-0 min-w-0 bg-transparent p-0 overflow-hidden"
                )
                .props('id="help-tab-panels"')
            ):
                # -------------------------------------------------------------
                # TAB 1: Setup Workflow & Pipeline
                # -------------------------------------------------------------
                with (
                    ui.tab_panel(tab_workflow)
                    .classes(theme.PANEL_TAB_CONTENT)
                    .props('id="help-subtab-workflow"')
                ):
                    # Card 1: Runtime Architecture
                    with (
                        ui.expansion(
                            "Runtime Architecture",
                            icon="account_tree",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("pipeline_architecture.md")).classes(
                            "text-xs text-gray-300 w-full leading-relaxed"
                        )

                    # Card 2: Setup Wizard Progression
                    with (
                        ui.expansion(
                            "Setup Wizard Progression",
                            icon="format_list_numbered",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("wizard_steps.md")).classes(
                            "text-xs text-gray-300 w-full leading-relaxed"
                        )

                    # Card 3: Marker Placement Rules & Calibration Tips
                    with (
                        ui.expansion(
                            "Marker Placement Rules & Calibration Tips",
                            icon="check_circle",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("calibration_tips.md")).classes(
                            "text-xs text-gray-300 w-full leading-relaxed"
                        )

                    # Card 4: Wiki Documentation & Deep Dives
                    with (
                        ui.expansion(
                            "Wiki Documentation & Deep Dives",
                            icon="menu_book",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.label(
                            "Explore complete architecture, hardware, and integration guides on the GitHub Wiki:"
                        ).classes("text-xs text-gray-400")
                        with ui.element("div").classes(
                            "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 w-full pt-1"
                        ):
                            wiki_links = [
                                (
                                    "Getting Started & Hardware",
                                    "https://github.com/paulianttila/water-meter-digitizer/wiki/Getting-Started-&-Hardware",
                                    "Hardware selection, ESP32-CAM setup, and prerequisites",
                                ),
                                (
                                    "Setup & Calibration Manual",
                                    "https://github.com/paulianttila/water-meter-digitizer/wiki/Setup-Wizard-&-Calibration",
                                    "Step-by-step alignment, cropping, and ROI configuration",
                                ),
                                (
                                    "Smart Home & API Reference",
                                    "https://github.com/paulianttila/water-meter-digitizer/wiki/Integrations-&-API-Reference",
                                    "Home Assistant, MQTT, and REST API integration details",
                                ),
                                (
                                    "Architecture & Neural Models",
                                    "https://github.com/paulianttila/water-meter-digitizer/wiki/Architecture-&-Neural-Networks",
                                    "CNN model architectures and inference pipelines",
                                ),
                                (
                                    "Configuration & Storage",
                                    "https://github.com/paulianttila/water-meter-digitizer/wiki/Configuration-&-Storage-Manual",
                                    "INI configuration reference and storage backend guides",
                                ),
                            ]
                            for title, url, desc in wiki_links:
                                with ui.link(target=url, new_tab=True).classes(
                                    "p-3 rounded-lg bg-slate-950/60 border border-white/5 hover:border-cyan-500/30 hover:bg-slate-950/80 transition-all flex flex-col gap-1 no-underline"
                                ):
                                    with ui.row().classes("items-center gap-1.5"):
                                        ui.icon("open_in_new", color="cyan").classes(
                                            "text-xs"
                                        )
                                        ui.label(title).classes(
                                            "text-xs font-semibold text-cyan-400 hover:text-cyan-300"
                                        )
                                    ui.label(desc).classes("text-[11px] text-gray-400")

                # -------------------------------------------------------------
                # TAB 2: Calibration & Canvas Tools
                # -------------------------------------------------------------
                with (
                    ui.tab_panel(tab_canvas)
                    .classes(theme.PANEL_TAB_CONTENT)
                    .props('id="help-subtab-canvas"')
                ):
                    # Card 1: Alignment Best Practices
                    with (
                        ui.expansion(
                            "Alignment Best Practices",
                            icon="center_focus_strong",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("calibration_tips.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # Card 2: Canvas Controls & Keyboard Shortcuts
                    with (
                        ui.expansion(
                            "Canvas Controls & Keyboard Shortcuts",
                            icon="touch_app",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("canvas_keyboard_shortcuts.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # Card 3: Neural Network Models & ROIs
                    with (
                        ui.expansion(
                            "Neural Network Models & ROIs",
                            icon="memory",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("roi_best_practices.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                # -------------------------------------------------------------
                # TAB 3: Integrations & API Specs
                # -------------------------------------------------------------
                with (
                    ui.tab_panel(tab_integrations)
                    .classes(theme.PANEL_TAB_CONTENT)
                    .props('id="help-subtab-integrations"')
                ):
                    # Card 1: Smart Home & Automations
                    with (
                        ui.expansion(
                            "Smart Home & Automations",
                            icon="home",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.markdown(_load_help("home_assistant.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # Card 2: MQTT Topics & Telemetry
                    with (
                        ui.expansion(
                            "MQTT Topics & Telemetry",
                            icon="hub",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        ui.label("Prefix configured in [MQTT] section").classes(
                            "text-xs text-gray-400"
                        )
                        ui.markdown(_load_help("mqtt_integration.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )

                    # Card 3: Primary REST API Endpoints
                    with (
                        ui.expansion(
                            "Primary REST API Endpoints",
                            icon="api",
                            value=False,
                        )
                        .classes(theme.CARD_EXPANSION)
                        .props("header-class='text-white font-semibold text-sm'"),
                        ui.column().classes(
                            "w-full max-w-full p-4 pt-2 border-t border-white/5 gap-2.5 min-w-0 overflow-x-auto"
                        ),
                    ):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label(
                                "Core REST endpoints for integration and automation"
                            ).classes("text-xs text-gray-400")
                            ui.link(
                                "Open Interactive API Console", "/api_console"
                            ).classes(
                                "text-xs font-semibold text-cyan-400 hover:underline"
                            )
                        ui.markdown(_load_help("api_reference.md")).classes(
                            "text-xs text-gray-300 leading-relaxed"
                        )
