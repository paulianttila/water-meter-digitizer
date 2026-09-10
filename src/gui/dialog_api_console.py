"""Interactive REST API Console & Explorer Dialog for NiceGUI."""

import asyncio
import json
import time
from typing import Any

import requests
from nicegui import ui

from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
)

ENDPOINTS = [
    {
        "label": "GET /health (Diagnostics & Telemetry)",
        "url": "/health",
        "method": "GET",
    },
    {
        "label": "GET /healthcheck (Liveness Probe)",
        "url": "/healthcheck",
        "method": "GET",
    },
    {"label": "GET /version (App Version)", "url": "/version", "method": "GET"},
    {
        "label": "GET /meter (Raw Meter Deductions as JSON)",
        "url": "/meter?format=json&saveimages=false",
        "method": "GET",
    },
    {
        "label": "GET /leak/status (Zero-Flow Leak Telemetry)",
        "url": "/leak/status",
        "method": "GET",
    },
    {
        "label": "POST /leak/reset (Reset Leak State)",
        "url": "/leak/reset",
        "method": "POST",
    },
    {
        "label": "GET /poller/status (Poller Schedule)",
        "url": "/poller/status",
        "method": "GET",
    },
    {
        "label": "POST /poller/trigger (Trigger Immediate Readout)",
        "url": "/poller/trigger",
        "method": "POST",
    },
    {
        "label": "GET /mqtt/status (MQTT Broker Telemetry)",
        "url": "/mqtt/status",
        "method": "GET",
    },
    {
        "label": "GET /reload (Reload Configuration as JSON)",
        "url": "/reload?format=json",
        "method": "GET",
    },
    {
        "label": "GET /history/consumption (Historical Aggregates)",
        "url": "/history/consumption?meter_name=total&interval=daily&days=7",
        "method": "GET",
    },
]


class ApiConsoleDialog:
    """Modal dialog allowing users to interactively test and explore REST endpoints."""

    def __init__(self, port: int = 3000) -> None:
        self.port = port
        self.dialog = ui.dialog().classes("w-full max-w-4xl")
        self.selected_endpoint = ENDPOINTS[0]["url"]
        self.selected_method = ENDPOINTS[0]["method"]
        self.status_badge: ui.element | None = None
        self.status_label: ui.label | None = None
        self.latency_label: ui.label | None = None
        self.viewer_container: ui.column | None = None
        self.response_viewer: ui.code | None = None
        self.last_response_text: str = ""
        self.url_input: ui.input | None = None
        self.spinner: ui.spinner | None = None
        self._build_ui()

    def open(self) -> None:
        self.dialog.open()

    def close(self) -> None:
        self.dialog.close()

    def _on_endpoint_change(self, e: Any) -> None:
        target_url = e.value
        for ep in ENDPOINTS:
            if ep["url"] == target_url:
                self.selected_method = ep["method"]
                if self.url_input:
                    self.url_input.value = target_url
                break

    async def _execute_request(self) -> None:
        if not self.url_input or not self.url_input.value:
            return

        endpoint = self.url_input.value.strip()
        method = self.selected_method

        if self.spinner:
            self.spinner.visible = True
        if self.status_label:
            self.status_label.text = "Sending..."
        if self.latency_label:
            self.latency_label.text = ""

        # Make local request to backend
        full_url = f"http://127.0.0.1:{self.port}{endpoint}"
        start_time = time.perf_counter()

        def _do_req() -> dict[str, Any]:
            try:
                if method == "POST":
                    resp = requests.post(full_url, timeout=10.0)
                else:
                    resp = requests.get(full_url, timeout=10.0)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                is_json = False
                try:
                    data = resp.json()
                    formatted = json.dumps(data, indent=2)
                    is_json = True
                except Exception:
                    formatted = resp.text

                return {
                    "ok": resp.ok,
                    "status_code": resp.status_code,
                    "latency": latency,
                    "body": formatted,
                    "is_json": is_json,
                }
            except Exception as ex:
                return {
                    "ok": False,
                    "status_code": 0,
                    "latency": 0.0,
                    "body": f"Error: {ex}",
                    "is_json": False,
                }

        result = await asyncio.to_thread(_do_req)

        if self.spinner:
            self.spinner.visible = False

        status_code = result["status_code"]
        latency = result["latency"]
        body = result["body"]
        is_json = result["is_json"]
        self.last_response_text = body

        if self.status_label:
            self.status_label.text = (
                f"HTTP {status_code}" if status_code > 0 else "Connection Error"
            )
        if self.status_badge:
            if result["ok"]:
                self.status_badge.classes(replace=BADGE_SUCCESS)
            elif status_code >= 400:
                self.status_badge.classes(
                    replace=BADGE_WARNING if status_code < 500 else BADGE_ERROR
                )
            else:
                self.status_badge.classes(replace=BADGE_ERROR)

        if self.latency_label:
            self.latency_label.text = f"{latency} ms"

        if self.viewer_container:
            self.viewer_container.clear()
            with self.viewer_container:
                if is_json:
                    self.response_viewer = ui.code(body, language="json").classes(
                        "w-full text-xs font-mono text-emerald-400"
                    )
                elif body.strip().startswith("<") or "<html" in body.lower():
                    self.response_viewer = ui.code(body, language="html").classes(
                        "w-full text-xs font-mono text-cyan-300"
                    )
                else:
                    self.response_viewer = ui.code(body, language="text").classes(
                        "w-full text-xs font-mono text-emerald-300"
                    )
        elif self.response_viewer:
            self.response_viewer.content = body

    def _copy_response(self) -> None:
        if self.last_response_text:
            ui.run_javascript(
                f"navigator.clipboard.writeText({json.dumps(self.last_response_text)});"
            )
            ui.notify("Response copied to clipboard!", type="positive")

    def _build_ui(self) -> None:
        with (
            self.dialog,
            ui.card().classes(
                "w-full max-w-4xl p-6 bg-slate-900 border border-white/10 rounded-2xl gap-4"
            ),
        ):
            # Header
            with ui.row().classes(
                "w-full justify-between items-center pb-3 border-b border-white/10"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("terminal", color="cyan").classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label("REST API Console & Explorer").classes(
                            "font-['Outfit'] font-bold text-lg text-white"
                        )
                        ui.label(
                            "Interactive live endpoint debugger and tester"
                        ).classes("text-xs text-gray-400")
                ui.button(icon="close", on_click=self.close).props(
                    "flat round dense color=gray"
                )

            # Selector Row
            with ui.row().classes("w-full gap-3 items-center"):
                ui.select(
                    options={ep["url"]: ep["label"] for ep in ENDPOINTS},
                    value=self.selected_endpoint,
                    on_change=self._on_endpoint_change,
                    label="Select Preset Endpoint",
                ).props("outlined dense options-dense").classes(
                    "flex-1 text-sm bg-slate-950/60"
                )

            # Endpoint input & execute button
            with ui.row().classes("w-full gap-2 items-center"):
                self.url_input = (
                    ui.input(value=self.selected_endpoint, label="Request Path")
                    .props("outlined dense")
                    .classes("flex-1 font-mono text-sm bg-slate-950/60")
                )

                ui.button("Execute", icon="send", on_click=self._execute_request).props(
                    "unelevated color=primary"
                ).classes("px-4 font-semibold shadow-md shadow-blue-500/20")

            # Status Bar
            with ui.row().classes("w-full justify-between items-center px-1"):
                with ui.row().classes("items-center gap-3"):
                    self.spinner = ui.spinner("dots", size="sm", color="cyan")
                    self.spinner.visible = False
                    with ui.element("span").classes(BADGE_INFO) as self.status_badge:
                        self.status_label = ui.label("Ready")
                    self.latency_label = ui.label("").classes(
                        "text-xs font-mono text-gray-400"
                    )

                ui.button(
                    "Copy Output", icon="content_copy", on_click=self._copy_response
                ).props("flat dense size=sm color=cyan")

            # Response Viewer
            with ui.element("div").classes(
                "w-full rounded-xl bg-slate-950 p-4 border border-white/10 max-h-[420px] overflow-y-auto"
            ):
                self.viewer_container = ui.column().classes("w-full p-0 gap-0")
                with self.viewer_container:
                    self.response_viewer = ui.code(
                        "// Select an endpoint above and click Execute to test API responses.",
                        language="json",
                    ).classes("w-full text-xs font-mono text-emerald-400")
