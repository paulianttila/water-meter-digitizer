import json
import logging
from typing import Any

from nicegui import ui

import gui.theme as theme
from callbacks import Callbacks
from gui.components import page_header
from main import VERSION
from utils.diagnostics import get_process_memory_info, get_system_info

logger = logging.getLogger(__name__)


class HelpPage:
    """Comprehensive Help, Documentation, and Support Center."""

    def __init__(self, callbacks: Callbacks | None = None) -> None:
        self.callbacks = callbacks

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

    def show(self) -> None:
        with (
            ui.dialog() as support_dialog,
            ui.card().classes(
                "w-full max-w-3xl bg-slate-900 border border-white/10 p-5 rounded-2xl flex flex-col gap-4 text-white shadow-2xl"
            ),
        ):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2.5"):
                    with ui.element("div").classes(
                        "w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center"
                    ):
                        ui.icon("bug_report", color="cyan").classes("text-lg")
                    ui.label("Support Diagnostic Bundle").classes(
                        "text-base font-bold text-white font-['Outfit']"
                    )
                ui.button(icon="close", on_click=support_dialog.close).props(
                    "flat round dense size=sm color=gray"
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
                "w-full items-center justify-between pt-2 border-t border-white/10 gap-2"
            ):
                with ui.row().classes("items-center gap-2"):
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
                # TAB 1: Setup Workflow & Pipeline (Option A 2-Column Split Hub)
                # -------------------------------------------------------------
                with ui.tab_panel(tab_workflow).classes(
                    "w-full h-full p-0 flex flex-col gap-4"
                ):
                    # Top Pipeline Architecture Banner
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/70 border border-emerald-500/20 rounded-xl flex flex-col gap-2.5 shrink-0"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("account_tree", color="emerald").classes(
                                    "text-lg"
                                )
                                ui.label(
                                    "End-to-End Runtime Pipeline Architecture"
                                ).classes(
                                    "text-xs font-bold text-emerald-400 tracking-wider uppercase"
                                )
                            ui.label("6 Autonomous Processing Stages").classes(
                                "text-[11px] text-gray-400 font-medium"
                            )

                        pipeline_stages = [
                            (
                                "1. Capture",
                                "camera_alt",
                                "HTTP/RTSP snapshot or local file",
                            ),
                            (
                                "2. Alignment",
                                "transform",
                                "Affine warp via 3 reference markers",
                            ),
                            (
                                "3. Adjustment",
                                "tune",
                                "Contrast, brightness & sharpness filters",
                            ),
                            (
                                "4. Inference",
                                "memory",
                                "LiteRT quantized CNN classification",
                            ),
                            (
                                "5. Consistency",
                                "rule",
                                "Predecessor odometer rollover deduction",
                            ),
                            (
                                "6. Export",
                                "cloud_upload",
                                "MQTT, Home Assistant & SQLite storage",
                            ),
                        ]

                        with ui.element("div").classes(
                            "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2"
                        ):
                            for title, icon, desc in pipeline_stages:
                                with ui.element("div").classes(
                                    "p-2.5 rounded-lg bg-slate-800/50 border border-white/5 flex flex-col items-center text-center gap-1"
                                ):
                                    ui.icon(icon, color="emerald").classes("text-base")
                                    ui.label(title).classes(
                                        "text-xs font-bold text-white"
                                    )
                                    ui.label(desc).classes(
                                        "text-[11px] text-gray-400 leading-tight"
                                    )

                    # 2-Column Split: Wizard Steps (Left) + Quick Reference Cheat-Sheet (Right)
                    with ui.element("div").classes(
                        "grid grid-cols-1 lg:grid-cols-3 gap-4 items-start"
                    ):
                        # Left Column (2/3 width): 9-Step Linear Progression
                        with ui.column().classes("lg:col-span-2 gap-3 w-full"):
                            with ui.row().classes("items-center justify-between px-1"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon(
                                        "format_list_numbered", color="cyan"
                                    ).classes("text-lg")
                                    ui.label("9-Step Setup Wizard Progression").classes(
                                        "text-sm font-bold text-white font-['Outfit']"
                                    )
                                ui.label(
                                    "Complete sequentially from Step 1 to 9"
                                ).classes("text-xs text-gray-400")

                            wizard_steps = [
                                (
                                    "1",
                                    "Download Image",
                                    "camera_alt",
                                    "Enter camera snapshot URL (HTTP, HTTPS, or file://), timeout, and minimum byte size. Test network reachability live.",
                                ),
                                (
                                    "2",
                                    "Initial Rotate",
                                    "rotate_90_degrees_ccw",
                                    "Rotate coarse 90° increments (0°, 90°, 180°, 270°) so meter numbers and circular dials are oriented naturally upright.",
                                ),
                                (
                                    "3",
                                    "Reference Markers",
                                    "add_location_alt",
                                    "Mark exactly 3 high-contrast visual anchors (screws, dial center pins, logo corners) forming a wide triangle for affine alignment.",
                                ),
                                (
                                    "4",
                                    "Image Adjustments",
                                    "tune",
                                    "Fine-tune rotation angle (e.g. 0.5°), test affine alignment, and configure contrast, sharpness, and AutoContrast preprocessing.",
                                ),
                                (
                                    "5",
                                    "Digital ROIs",
                                    "pin",
                                    "Draw tight bounding boxes around mechanical roller digits (D1-D5), select CNN models, and test classification inference.",
                                ),
                                (
                                    "6",
                                    "Analog ROIs",
                                    "query_builder",
                                    "Draw bounding boxes around circular needle dials (A1-A4), select CNN models, and test continuous angle detection.",
                                ),
                                (
                                    "7",
                                    "Meters Definition",
                                    "speed",
                                    "Define composite meters (e.g. total = {D1}{D2}{D3}.{A1}{A2}{A3}{A4}), physical flow rate limits, and starting baseline values.",
                                ),
                                (
                                    "8",
                                    "Services & Poller",
                                    "settings_suggest",
                                    "Configure background poller interval, MQTT telemetry topics, Home Assistant auto-discovery, and zero-flow leak tracker.",
                                ),
                                (
                                    "9",
                                    "Final Review & Save",
                                    "check_circle",
                                    "Inspect compiled INI configuration, save reference template images, and apply settings live to the running digitizer.",
                                ),
                            ]

                            for (
                                step_num,
                                step_title,
                                step_icon,
                                step_desc,
                            ) in wizard_steps:
                                with ui.element("div").classes(
                                    "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex gap-3 items-start"
                                ):
                                    with ui.element("div").classes(
                                        "w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 "
                                        "flex items-center justify-center shrink-0 font-bold text-xs text-cyan-300"
                                    ):
                                        ui.label(step_num)
                                    with ui.column().classes("gap-0.5 flex-1"):
                                        with ui.row().classes("items-center gap-1.5"):
                                            ui.icon(step_icon, color="cyan").classes(
                                                "text-sm"
                                            )
                                            ui.label(
                                                f"Step {step_num}: {step_title}"
                                            ).classes(
                                                "font-semibold text-sm text-white"
                                            )
                                        ui.label(step_desc).classes(
                                            "text-xs text-gray-400 leading-relaxed"
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
                                    ui.label("Marker Rules (Step 3)").classes(
                                        "text-xs font-bold text-emerald-400 uppercase tracking-wider"
                                    )
                                rules = [
                                    "Exactly 3 reference points required",
                                    "Form a wide non-collinear triangle",
                                    "Choose static screws or dial center pins",
                                    "Never use moving digits or dials",
                                    "Avoid reflective glare hotspots",
                                ]
                                for rule in rules:
                                    with ui.row().classes("items-center gap-2"):
                                        ui.icon(
                                            "fiber_manual_record", color="emerald"
                                        ).classes("text-[8px]")
                                        ui.label(rule).classes("text-xs text-gray-300")

                            # Cheat Sheet Card 2: Canvas Shortcuts
                            with ui.card().classes(
                                "w-full p-4 bg-slate-900/80 border border-purple-500/20 rounded-xl flex flex-col gap-2.5"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("touch_app", color="purple").classes(
                                        "text-base"
                                    )
                                    ui.label("Canvas Shortcuts").classes(
                                        "text-xs font-bold text-purple-400 uppercase tracking-wider"
                                    )
                                shortcuts = [
                                    ("Drag", "Draw new bounding box"),
                                    ("Click Box", "Select for editing"),
                                    ("Arrow Keys", "Nudge position by 1px"),
                                    ("Shift + Arrow", "Fast nudge by 10px"),
                                    ("Align Buttons", "Equalize left/top/size"),
                                ]
                                for key_comb, action in shortcuts:
                                    with ui.row().classes(
                                        "items-center justify-between w-full text-xs"
                                    ):
                                        ui.label(key_comb).classes(
                                            "font-mono px-1.5 py-0.5 rounded bg-white/10 text-purple-300 font-semibold text-[11px]"
                                        )
                                        ui.label(action).classes(
                                            "text-gray-400 text-right"
                                        )

                            # Cheat Sheet Card 3: Deep Documentation Links
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
                            ui.label(
                                "Reference Marker Alignment Best Practices"
                            ).classes("text-base font-bold text-white font-['Outfit']")

                        practices = [
                            (
                                "Static & Rigid Landmarks",
                                "lock",
                                "Select permanent meter landmarks such as dial screws, casing rivets, or fixed logo corners. Never use moving dials or rotating needles.",
                            ),
                            (
                                "Wide Non-Collinear Triangle",
                                "change_history",
                                "Spread the 3 points widely across the image (top-left, top-right, bottom-center). A wide triangle maximizes affine alignment stability.",
                            ),
                            (
                                "Consistent Illumination",
                                "wb_sunny",
                                "Avoid placing reference markers inside regions prone to specular LED glare or flash hotspots that shift pixel centroids.",
                            ),
                            (
                                "Subpixel Stability Inspection",
                                "zoom_in",
                                "Use the 200% zoom crop view in Step 4 to verify that reference crosshairs remain aligned across repeated snapshots.",
                            ),
                        ]

                        for title, icon, desc in practices:
                            with ui.element("div").classes(
                                "p-3 rounded-xl bg-slate-800/50 border border-white/5 flex gap-3 items-start"
                            ):
                                with ui.element("div").classes(
                                    "w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 "
                                    "flex items-center justify-center shrink-0 mt-0.5"
                                ):
                                    ui.icon(icon, color="emerald").classes("text-base")
                                with ui.column().classes("gap-0.5 flex-1"):
                                    ui.label(title).classes(
                                        "font-semibold text-sm text-white"
                                    )
                                    ui.label(desc).classes(
                                        "text-xs text-gray-400 leading-relaxed"
                                    )

                    # Right Column: Canvas Controls & Model Guide
                    with ui.column().classes("w-full gap-4"):
                        with ui.card().classes(
                            "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("touch_app", color="purple").classes("text-xl")
                                ui.label("Interactive Canvas & ROI Controls").classes(
                                    "text-base font-bold text-white font-['Outfit']"
                                )

                            controls = [
                                (
                                    "Draw Bounding Box",
                                    "crop",
                                    "Click and drag on the interactive image canvas to define a new ROI box.",
                                ),
                                (
                                    "Select & Move",
                                    "open_with",
                                    "Click inside an existing box to select it. Drag or use Arrow keys to nudge position.",
                                ),
                                (
                                    "Batch Alignment",
                                    "align_horizontal_left",
                                    "Use the Align Left, Top, Width, and Height toolbar buttons to standardize ROIs across multiple digits.",
                                ),
                                (
                                    "Real-time Coordinates",
                                    "pin_drop",
                                    "Hovering over the canvas displays real-time pixel X and Y coordinates in the status footer.",
                                ),
                            ]

                            for title, icon, desc in controls:
                                with ui.element("div").classes(
                                    "p-3 rounded-xl bg-slate-800/50 border border-white/5 flex gap-3 items-start"
                                ):
                                    with ui.element("div").classes(
                                        "w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 "
                                        "flex items-center justify-center shrink-0 mt-0.5"
                                    ):
                                        ui.icon(icon, color="purple").classes(
                                            "text-base"
                                        )
                                    with ui.column().classes("gap-0.5 flex-1"):
                                        ui.label(title).classes(
                                            "font-semibold text-sm text-white"
                                        )
                                        ui.label(desc).classes(
                                            "text-xs text-gray-400 leading-relaxed"
                                        )

                        with ui.card().classes(
                            "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-2.5"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("memory", color="cyan").classes("text-base")
                                ui.label("Neural Network Model Types").classes(
                                    "text-xs font-bold text-cyan-400 uppercase tracking-wider"
                                )
                            model_types = [
                                (
                                    "auto",
                                    "Automatically selects between digital drum and analog dial classification based on step context.",
                                ),
                                (
                                    "digital / digital100",
                                    "Quantized CNN for mechanical drum odometer digits (0-9) and 100-class fractional transitions.",
                                ),
                                (
                                    "analog",
                                    "CNN interpreter predicting continuous needle angles (0.0-9.9) for circular dials.",
                                ),
                            ]
                            for m_type, m_desc in model_types:
                                with ui.row().classes("items-start gap-2 text-xs"):
                                    ui.label(m_type).classes(
                                        "font-mono font-bold text-cyan-300 min-w-[80px]"
                                    )
                                    ui.label(m_desc).classes("text-gray-400 flex-1")

                # -------------------------------------------------------------
                # TAB 3: Integrations & API Specs
                # -------------------------------------------------------------
                with ui.tab_panel(tab_integrations).classes(
                    "w-full h-full p-0 flex flex-col gap-4"
                ):
                    # 4 Top Feature Cards
                    with ui.element("div").classes(
                        "grid grid-cols-1 md:grid-cols-2 gap-3"
                    ):
                        integrations = [
                            (
                                "Home Assistant Auto-Discovery",
                                "home",
                                "amber",
                                "Publishes MQTT sensor discovery topics under homeassistant/sensor/watermeter/. Emits state, unit (m³), and diagnostic entities.",
                            ),
                            (
                                "MQTT Live Telemetry",
                                "sensors",
                                "cyan",
                                "Streams real-time meter readings, raw readouts, operational health status, flow rates, and zero-flow leak alarms.",
                            ),
                            (
                                "Consumption History & Analytics",
                                "analytics",
                                "purple",
                                "Query aggregated hourly, daily, and weekly water usage intervals via /history/consumption, /history/readings, or /meter.",
                            ),
                            (
                                "REST API Triggers & Controls",
                                "api",
                                "emerald",
                                "Trigger instant digitizations via POST /readout, force scheduled poller cycles via POST /poller/trigger, or reset leaks via POST /leak/reset.",
                            ),
                        ]

                        for title, icon, color, desc in integrations:
                            with ui.element("div").classes(
                                "p-3 rounded-xl bg-slate-900/60 border border-white/10 flex gap-3 items-start"
                            ):
                                with ui.element("div").classes(
                                    f"w-8 h-8 rounded-lg bg-{color}-500/10 border border-{color}-500/20 "
                                    f"flex items-center justify-center shrink-0 mt-0.5"
                                ):
                                    ui.icon(icon, color=color).classes("text-base")
                                with ui.column().classes("gap-0.5 flex-1"):
                                    ui.label(title).classes(
                                        "font-semibold text-sm text-white"
                                    )
                                    ui.label(desc).classes(
                                        "text-xs text-gray-400 leading-relaxed"
                                    )

                    # MQTT Schema Reference Table Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("hub", color="cyan").classes("text-lg")
                                ui.label("MQTT Topics & Telemetry Schema").classes(
                                    "text-sm font-bold text-white font-['Outfit']"
                                )
                            ui.label("Prefix configured in [MQTT] section").classes(
                                "text-xs text-gray-400"
                            )

                        mqtt_rows = [
                            (
                                "&lt;prefix&gt;/value",
                                "Float string",
                                "Processed & validated meter reading",
                                "00442.0134",
                            ),
                            (
                                "&lt;prefix&gt;/raw",
                                "String",
                                "Raw uncorrected digit readout",
                                "00442.0134",
                            ),
                            (
                                "&lt;prefix&gt;/status",
                                "String",
                                "Processing status and outcome",
                                "Success",
                            ),
                            (
                                "&lt;prefix&gt;/leak_detected",
                                "Boolean string",
                                "Zero-flow continuous leak flag",
                                "false",
                            ),
                            (
                                "&lt;prefix&gt;/rate",
                                "Float string",
                                "Computed flow rate per time delta",
                                "0.0025",
                            ),
                        ]
                        rows_html = "".join(
                            f'<tr class="hover:bg-white/5 transition-colors border-b border-white/5">'
                            f'<td class="p-2 font-mono text-cyan-400 font-bold">{topic}</td>'
                            f'<td class="p-2 text-gray-300">{p_type}</td>'
                            f'<td class="p-2 text-gray-400">{desc}</td>'
                            f'<td class="p-2 font-mono text-emerald-400">{ex}</td>'
                            f"</tr>"
                            for topic, p_type, desc, ex in mqtt_rows
                        )
                        ui.html(
                            f'<div class="overflow-x-auto w-full">'
                            f'<table class="w-full text-xs text-left border-collapse">'
                            f'<thead><tr class="border-b border-white/10 text-gray-400 font-semibold">'
                            f'<th class="p-2">Topic Suffix</th>'
                            f'<th class="p-2">Payload Type</th>'
                            f'<th class="p-2">Description</th>'
                            f'<th class="p-2">Example Value</th>'
                            f"</tr></thead>"
                            f"<tbody>{rows_html}</tbody>"
                            f"</table></div>"
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

                        rest_rows = [
                            (
                                "POST /readout",
                                "Trigger immediate image acquisition and digitization pipeline",
                                '{"value": "00442.0134", "status": "Success"}',
                            ),
                            (
                                "GET /meter",
                                "Retrieve current meter readout and neural confidence breakdown",
                                '{"main": "00442.0134", "confidence": 98.4}',
                            ),
                            (
                                "POST /poller/trigger",
                                "Force immediate poller cycle execution in background",
                                '{"status": "triggered"}',
                            ),
                            (
                                "POST /leak/reset",
                                "Acknowledge and reset zero-flow leak state",
                                '{"enabled": true, "state": "OK"}',
                            ),
                            (
                                "GET /healthcheck",
                                "Lightweight system diagnostics probe for Docker & orchestrators",
                                '{"status": "healthy"}',
                            ),
                        ]
                        rest_rows_html = "".join(
                            f'<tr class="hover:bg-white/5 transition-colors border-b border-white/5">'
                            f'<td class="p-2 font-mono text-emerald-400 font-bold">{ep}</td>'
                            f'<td class="p-2 text-gray-300">{desc}</td>'
                            f'<td class="p-2 font-mono text-gray-400 truncate max-w-xs">{resp}</td>'
                            f"</tr>"
                            for ep, desc, resp in rest_rows
                        )
                        ui.html(
                            f'<div class="overflow-x-auto w-full">'
                            f'<table class="w-full text-xs text-left border-collapse">'
                            f'<thead><tr class="border-b border-white/10 text-gray-400 font-semibold">'
                            f'<th class="p-2">Method & Endpoint</th>'
                            f'<th class="p-2">Function</th>'
                            f'<th class="p-2">Sample Response</th>'
                            f"</tr></thead>"
                            f"<tbody>{rest_rows_html}</tbody>"
                            f"</table></div>"
                        )
