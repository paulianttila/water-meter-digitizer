import json
import logging
from typing import Any

from nicegui import ui

import gui.theme as theme
from callbacks import Callbacks
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
            # Header
            with ui.row().classes("w-full justify-between items-center shrink-0 mb-1"):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 "
                        "flex items-center justify-center shadow-lg shadow-cyan-500/10"
                    ):
                        ui.icon("help_outline", color="cyan").classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label("Help & Documentation").classes(
                            "text-h4 font-['Outfit']"
                        )
                        ui.label(
                            "Guides, best practices, keyboard shortcuts, and troubleshooting"
                        ).classes("text-xs text-gray-400")

                with ui.row().classes("items-center gap-2"):
                    ui.link(
                        "Wiki Documentation",
                        "https://github.com/paulianttila/water-meter-digitizer/wiki",
                        new_tab=True,
                    ).classes(
                        "text-xs font-semibold text-gray-300 hover:text-white px-3 py-1.5 "
                        "rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
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
                        "text-xs font-semibold text-cyan-400 bg-cyan-500/10 "
                        "border border-cyan-500/30 px-3 py-1 rounded-full"
                    )

            # Sub-Tabs for structured knowledge navigation
            with (
                ui.tabs().classes(
                    "w-full bg-slate-900/90 border border-white/10 rounded-xl p-1 shrink-0"
                ) as tabs,
                ui.row().classes("w-full gap-2"),
            ):
                tab_wizard = ui.tab("Setup Wizard (9 Steps)", icon="checklist").classes(
                    "font-semibold text-sm"
                )
                tab_alignment = ui.tab(
                    "Marker Best Practices", icon="center_focus_strong"
                ).classes("font-semibold text-sm")
                tab_controls = ui.tab("Canvas & Shortcuts", icon="touch_app").classes(
                    "font-semibold text-sm"
                )
                tab_integrations = ui.tab(
                    "Integrations & Services", icon="hub"
                ).classes("font-semibold text-sm")
                tab_troubleshooting = ui.tab(
                    "Troubleshooting & FAQ", icon="live_help"
                ).classes("font-semibold text-sm")

            with ui.tab_panels(tabs, value=tab_wizard).classes(
                "w-full flex-1 bg-transparent p-0 overflow-y-auto"
            ):
                # 1. Setup Wizard Guide & Pipeline Architecture
                with ui.tab_panel(tab_wizard).classes(
                    "w-full h-full p-0 flex flex-col gap-3"
                ):
                    # Pipeline Architecture Overview Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("account_tree", color="emerald").classes("text-xl")
                            ui.label("End-to-End Pipeline Architecture").classes(
                                "text-sm font-bold text-white"
                            )

                        pipeline_steps = [
                            (
                                "1. Capture",
                                "camera_alt",
                                "HTTP/RTSP snapshot or local image",
                            ),
                            (
                                "2. Alignment",
                                "transform",
                                "Affine warp via 3 reference markers",
                            ),
                            (
                                "3. Adjustment",
                                "tune",
                                "Contrast, brightness & sharpness prep",
                            ),
                            (
                                "4. Inference",
                                "memory",
                                "LiteRT quantized CNN classification",
                            ),
                            (
                                "5. Consistency",
                                "rule",
                                "Odometer roll & predecessor check",
                            ),
                            (
                                "6. Export",
                                "cloud_upload",
                                "MQTT, Home Assistant, SQLite & REST",
                            ),
                        ]

                        with ui.element("div").classes(
                            "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2"
                        ):
                            for step_title, step_icon, step_desc in pipeline_steps:
                                with ui.element("div").classes(
                                    "p-2.5 rounded-lg bg-slate-800/40 border border-white/5 flex flex-col items-center text-center gap-1"
                                ):
                                    ui.icon(step_icon, color="emerald").classes(
                                        "text-base"
                                    )
                                    ui.label(step_title).classes(
                                        "text-xs font-bold text-white"
                                    )
                                    ui.label(step_desc).classes(
                                        "text-[11px] text-gray-400 leading-tight"
                                    )

                    # 9-Step Wizard Card
                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("checklist", color="cyan").classes("text-xl")
                            ui.label("9-Step Setup Wizard Workflow").classes(
                                "text-base font-bold text-white"
                            )

                        with ui.element("div").classes(
                            "grid grid-cols-1 md:grid-cols-2 gap-3"
                        ):
                            steps = [
                                (
                                    "1. Download Image",
                                    "camera_alt",
                                    "Enter the camera snapshot URL (HTTP, HTTPS, or file://), request timeout, and minimum payload size. Test reachability live.",
                                ),
                                (
                                    "2. Initial Rotate",
                                    "rotate_90_degrees_ccw",
                                    "Rotate coarse 90° increments (0°, 90°, 180°, 270°) so meter numbers and dials are oriented naturally upright.",
                                ),
                                (
                                    "3. Reference Markers",
                                    "add_location_alt",
                                    "Mark exactly 3 high-contrast, rigid visual landmarks (screws, dial centers, fixed logo corners) for affine geometric alignment.",
                                ),
                                (
                                    "4. Image Adjustments",
                                    "tune",
                                    "Fine-tune rotation angle (e.g. 0.5°), test affine alignment, and configure contrast, sharpness, and AutoContrast filters.",
                                ),
                                (
                                    "5. Digital ROIs",
                                    "pin",
                                    "Draw tight bounding boxes around mechanical roller digits (D1-D5), choose CNN models, and test classification inference.",
                                ),
                                (
                                    "6. Analog ROIs",
                                    "query_builder",
                                    "Draw bounding boxes around circular dial needles (A1-A4), choose CNN models, and test circular angle detection.",
                                ),
                                (
                                    "7. Meters Definition",
                                    "speed",
                                    "Define composite meters (e.g. total = {D1}{D2}{D3}.{A1}{A2}{A3}{A4}), rate limits, previous value deduction, and units.",
                                ),
                                (
                                    "8. Services & Poller",
                                    "settings_suggest",
                                    "Configure scheduled background polling interval, MQTT publishing topics, Home Assistant auto-discovery, and leak monitor.",
                                ),
                                (
                                    "9. Final Review & Save",
                                    "check_circle",
                                    "Inspect compiled INI configuration, save reference image landmarks, and apply settings to the live digitizer runtime.",
                                ),
                            ]

                            for title, icon, desc in steps:
                                with ui.element("div").classes(
                                    "p-3 rounded-xl bg-slate-800/50 border border-white/5 flex gap-3 items-start"
                                ):
                                    with ui.element("div").classes(
                                        "w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 "
                                        "flex items-center justify-center shrink-0 mt-0.5"
                                    ):
                                        ui.icon(icon, color="cyan").classes("text-base")
                                    with ui.column().classes("gap-0.5 flex-1"):
                                        ui.label(title).classes(
                                            "font-semibold text-sm text-white"
                                        )
                                        ui.label(desc).classes(
                                            "text-xs text-gray-400 leading-relaxed"
                                        )

                # 2. Marker Alignment Best Practices
                with (
                    ui.tab_panel(tab_alignment).classes(
                        "w-full h-full p-0 flex flex-col gap-3"
                    ),
                    ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ),
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("center_focus_strong", color="emerald").classes(
                            "text-xl"
                        )
                        ui.label("Reference Marker Alignment Best Practices").classes(
                            "text-base font-bold text-white"
                        )

                    with ui.element("div").classes(
                        "grid grid-cols-1 md:grid-cols-2 gap-3"
                    ):
                        practices = [
                            (
                                "Choose Static & Rigid Landmarks",
                                "lock",
                                "Select permanent meter features such as dial center pins, dial screws, or fixed manufacturer badges. Never use moving dials or rotating needles.",
                            ),
                            (
                                "Form a Wide Triangle",
                                "change_history",
                                "Spread the 3 reference points widely across the image (top-left, top-right, bottom-center) to ensure robust affine transformation and prevent skew exaggeration.",
                            ),
                            (
                                "Consistent Lighting & Glare Avoidance",
                                "wb_sunny",
                                "Avoid placing reference points inside regions subject to specular reflections or direct flashlight hotspots that may shift pixel centroids.",
                            ),
                            (
                                "Check Subpixel Stability",
                                "zoom_in",
                                "Use the 200% zoom crop inspection in Step 4 to verify that reference crosshairs remain aligned across repeated camera snapshots.",
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

                # 3. Canvas & Shortcuts
                with (
                    ui.tab_panel(tab_controls).classes(
                        "w-full h-full p-0 flex flex-col gap-3"
                    ),
                    ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ),
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("keyboard", color="purple").classes("text-xl")
                        ui.label("Interactive Canvas & Keyboard Shortcuts").classes(
                            "text-base font-bold text-white"
                        )

                    with ui.element("div").classes(
                        "grid grid-cols-1 md:grid-cols-2 gap-3"
                    ):
                        controls = [
                            (
                                "Draw Bounding Box",
                                "crop",
                                "Click and drag on the interactive image canvas to define a new ROI bounding box.",
                            ),
                            (
                                "Select & Move",
                                "open_with",
                                "Click inside an existing box to select it. Drag or use Arrow keys (Shift + Arrow for 10px) to nudge position.",
                            ),
                            (
                                "Batch Alignment",
                                "align_horizontal_left",
                                "Use the Align Left, Top, Width, and Height toolbar buttons to standardize ROIs across multiple digit positions.",
                            ),
                            (
                                "Coordinate Display",
                                "pin_drop",
                                "Hovering over the canvas shows real-time pixel X and Y coordinates in the status footer.",
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
                                    ui.icon(icon, color="purple").classes("text-base")
                                with ui.column().classes("gap-0.5 flex-1"):
                                    ui.label(title).classes(
                                        "font-semibold text-sm text-white"
                                    )
                                    ui.label(desc).classes(
                                        "text-xs text-gray-400 leading-relaxed"
                                    )

                # 4. Integrations & Services
                with (
                    ui.tab_panel(tab_integrations).classes(
                        "w-full h-full p-0 flex flex-col gap-3"
                    ),
                    ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ),
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("hub", color="amber").classes("text-xl")
                        ui.label("Smart Home & Service Integrations").classes(
                            "text-base font-bold text-white"
                        )

                    with ui.element("div").classes(
                        "grid grid-cols-1 md:grid-cols-2 gap-3"
                    ):
                        integrations = [
                            (
                                "Home Assistant Auto-Discovery",
                                "home",
                                "Enables automatic MQTT sensor discovery under prefix homeassistant/sensor/watermeter/. Transmits state, unit (m³), and diagnostic entity metadata.",
                            ),
                            (
                                "MQTT Live Telemetry",
                                "sensors",
                                "Publishes readings to <prefix>/value, <prefix>/raw, <prefix>/status, <prefix>/leak_detected, and <prefix>/rate.",
                            ),
                            (
                                "Consumption History & Analytics",
                                "analytics",
                                "Query aggregated hourly, daily, and weekly water consumption via /history/consumption, /history/readings, or /meter.",
                            ),
                            (
                                "REST API Triggers",
                                "api",
                                "Trigger instant digitizations via POST /readout, force poller triggers via POST /poller/trigger, or reset leak monitors via POST /leak/reset.",
                            ),
                        ]

                        for title, icon, desc in integrations:
                            with ui.element("div").classes(
                                "p-3 rounded-xl bg-slate-800/50 border border-white/5 flex gap-3 items-start"
                            ):
                                with ui.element("div").classes(
                                    "w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 "
                                    "flex items-center justify-center shrink-0 mt-0.5"
                                ):
                                    ui.icon(icon, color="amber").classes("text-base")
                                with ui.column().classes("gap-0.5 flex-1"):
                                    ui.label(title).classes(
                                        "font-semibold text-sm text-white"
                                    )
                                    ui.label(desc).classes(
                                        "text-xs text-gray-400 leading-relaxed"
                                    )

                # 5. Troubleshooting & FAQ
                with (
                    ui.tab_panel(tab_troubleshooting).classes(
                        "w-full h-full p-0 flex flex-col gap-3"
                    ),
                    ui.card().classes(
                        "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl flex flex-col gap-3"
                    ),
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("live_help", color="rose").classes("text-xl")
                        ui.label(
                            "Troubleshooting & Frequently Asked Questions"
                        ).classes("text-base font-bold text-white")

                    with ui.element("div").classes("flex flex-col gap-2"):
                        faqs = [
                            (
                                "Why does the digitizer return '?' (unreadable digit)?",
                                "Check if the bounding box is cropped too tightly or includes adjacent drum borders. In Step 4, enable AutoContrast or adjust Sharpness. If digits are in mid-roll (transitioning between two numbers), the consistency engine uses predecessor deduction to resolve uncertain digits marked with '?'.",
                            ),
                            (
                                "Why was my reading rejected with 'Decreasing rate rejected'?",
                                "The consistency engine prevents negative flow spikes if a glare or misread occurs. If your physical meter replaced or rolled over, set AllowNegativeRates = true or use the Baselines page to set a new starting baseline.",
                            ),
                            (
                                "Camera shows Offline or timeout errors?",
                                "Verify camera IP reachability, test the URL in the API Console, check network firewall rules, or increase HTTPRequestTimeout in Step 1.",
                            ),
                            (
                                "Reference markers shift over time?",
                                "Ensure the camera mount is rigidly fixed. If lighting conditions change drastically, place reference points on high-contrast black/white features rather than reflective metal edges.",
                            ),
                        ]

                        for q, a in faqs:
                            with ui.expansion(q, icon="help_outline").classes(
                                "w-full bg-slate-800/40 border border-white/5 rounded-xl text-sm font-semibold"
                            ):
                                ui.label(a).classes(
                                    "p-3 text-xs text-gray-300 leading-relaxed font-normal"
                                )
