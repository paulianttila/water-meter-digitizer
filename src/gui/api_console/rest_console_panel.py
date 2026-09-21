"""REST API Endpoints Console Panel for NiceGUI."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any

import requests
from nicegui import ui

from gui.api_console.registry import ENDPOINTS, generate_curl_command
from gui.components.base_component import BaseComponent
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
    CARD_PANEL,
    ROW_ACTIONS,
    ROW_HEADER,
)

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)


class RestConsolePanel(BaseComponent):
    """Component for interactively testing and debugging backend REST endpoints."""

    def __init__(self, callbacks: Callbacks | None = None, port: int = 3000) -> None:
        super().__init__(callbacks)
        self.port = port
        self.selected_endpoint = ENDPOINTS[0]["url"]
        self.selected_method = ENDPOINTS[0]["method"]
        self.status_badge: ui.element | None = None
        self.status_label: ui.label | None = None
        self.latency_label: ui.label | None = None
        self.size_label: ui.label | None = None
        self.viewer_container: ui.column | None = None
        self.response_viewer: ui.code | None = None
        self.last_response_text: str = ""
        self.last_response_headers: dict[str, str] = {}
        self.last_curl_cmd: str = ""
        self.request_history: list[dict[str, Any]] = []
        self.url_input: ui.input | None = None
        self.method_select: ui.select | None = None
        self.body_input: ui.textarea | None = None
        self.spinner: ui.spinner | None = None

        # Multi-view response tab references
        self.resp_tabs: ui.tabs | None = None
        self.resp_tab_body: ui.tab | None = None
        self.resp_tab_headers: ui.tab | None = None
        self.resp_tab_curl: ui.tab | None = None
        self.resp_tab_history: ui.tab | None = None
        self.headers_container: ui.column | None = None
        self.curl_viewer: ui.code | None = None
        self.history_container: ui.column | None = None

    def _get_base_url(self) -> str:
        """Get base server URL honoring active client session port."""
        with contextlib.suppress(Exception):
            client = ui.context.client
            if (
                client
                and client.request
                and client.request.url
                and client.request.url.port
            ):
                return f"http://127.0.0.1:{client.request.url.port}"
        return f"http://127.0.0.1:{self.port}"

    def _on_endpoint_change(self, e: Any) -> None:
        """Handle preset endpoint dropdown selection."""
        target_url = getattr(e, "value", str(e))
        for ep in ENDPOINTS:
            if ep["url"] == target_url:
                self.selected_method = ep["method"]
                if self.method_select:
                    self.method_select.value = ep["method"]
                if self.url_input:
                    self.url_input.value = target_url
                break

    async def _execute_request(self) -> None:
        """Execute HTTP request against the selected API endpoint and render response."""
        if not self.url_input or not self.url_input.value:
            return

        endpoint = self.url_input.value.strip()
        method = self.selected_method
        body_data = (
            self.body_input.value.strip()
            if self.body_input and self.body_input.value
            else None
        )

        if self.spinner:
            self.spinner.visible = True
        if self.status_label:
            self.status_label.text = "Sending..."
        if self.latency_label:
            self.latency_label.text = ""

        full_url = f"{self._get_base_url()}{endpoint}"
        self.last_curl_cmd = generate_curl_command(method, full_url, body=body_data)
        if self.curl_viewer:
            self.curl_viewer.content = self.last_curl_cmd

        start_time = time.perf_counter()

        def _do_req() -> dict[str, Any]:
            try:
                if method == "POST":
                    resp = requests.post(full_url, data=body_data, timeout=10.0)
                elif method == "PUT":
                    resp = requests.put(full_url, data=body_data, timeout=10.0)
                elif method == "DELETE":
                    resp = requests.delete(full_url, timeout=10.0)
                else:
                    resp = requests.get(full_url, timeout=10.0)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                content_type = resp.headers.get("Content-Type", "")
                is_image = content_type.startswith("image/")
                is_json = False
                headers = dict(resp.headers)

                if is_image:
                    b64_data = base64.b64encode(resp.content).decode("ascii")
                    formatted = f"data:{content_type};base64,{b64_data}"
                else:
                    try:
                        data = resp.json()
                        formatted = json.dumps(data, indent=2)
                        is_json = True
                    except Exception:
                        logger.debug(
                            "Response body is not JSON, displaying as text",
                            exc_info=True,
                        )
                        formatted = resp.text

                return {
                    "ok": resp.ok,
                    "status_code": resp.status_code,
                    "latency": latency,
                    "body": formatted,
                    "is_json": is_json,
                    "is_image": is_image,
                    "headers": headers,
                    "raw_len": len(resp.content),
                }
            except Exception as ex:
                return {
                    "ok": False,
                    "status_code": 0,
                    "latency": 0.0,
                    "body": f"Error: {ex}",
                    "is_json": False,
                    "is_image": False,
                    "headers": {},
                    "raw_len": 0,
                }

        result = await asyncio.to_thread(_do_req)

        if self.spinner:
            self.spinner.visible = False

        status_code = result["status_code"]
        latency = result["latency"]
        body = result["body"]
        is_json = result["is_json"]
        is_image = result["is_image"]
        headers = result["headers"]
        self.last_response_text = body
        self.last_response_headers = headers

        # Save to history
        self.request_history.insert(
            0,
            {
                "time": time.strftime("%H:%M:%S"),
                "method": method,
                "url": endpoint,
                "status": status_code,
                "latency": latency,
            },
        )
        if len(self.request_history) > 20:
            self.request_history.pop()

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

        if self.size_label:
            size_kb = round(result["raw_len"] / 1024.0, 1)
            self.size_label.text = f"{size_kb} KB"

        # Ensure Body tab is active
        if self.resp_tabs and self.resp_tab_body:
            self.resp_tabs.value = self.resp_tab_body

        # Update Body Viewer
        if self.viewer_container:
            self.viewer_container.clear()
            with self.viewer_container:
                if is_image:
                    with ui.column().classes(
                        "w-full items-center gap-3 p-4 bg-slate-900/80 rounded-xl border border-white/10"
                    ):
                        with ui.row().classes(ROW_HEADER):
                            ui.label("Rendered Camera Picture").classes(
                                "text-sm font-semibold text-cyan-300"
                            )
                            with ui.row().classes(ROW_ACTIONS):
                                if "x-mock-meter-value" in headers:
                                    ui.badge(
                                        f"Value: {headers['x-mock-meter-value']}",
                                        color="cyan",
                                    )
                                size_kb = round(result["raw_len"] / 1024.0, 1)
                                ui.badge(f"{size_kb} KB", color="blue-grey")

                        ui.image(body).props(
                            'fit="contain" style="max-width: 100%; max-height: 380px; width: 100%; height: 100%;"'
                        ).classes(
                            "w-full h-full max-h-[380px] object-contain rounded-lg border border-white/10 shadow-lg"
                        )
                elif is_json:
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

        # Update Headers Container
        if self.headers_container:
            self.headers_container.clear()
            with self.headers_container:
                if not headers:
                    ui.label("No headers returned").classes(
                        "text-xs text-slate-400 italic p-3"
                    )
                else:
                    for k, v in headers.items():
                        with ui.row().classes(
                            f"{ROW_HEADER} py-1.5 px-3 bg-slate-950/70 border-b border-white/5 font-mono text-xs"
                        ):
                            ui.label(k).classes("text-cyan-300 font-semibold")
                            ui.label(str(v)).classes(
                                "text-slate-300 truncate max-w-md select-all"
                            )

        # Update History Container
        if self.history_container:
            self.history_container.clear()
            with self.history_container:
                for item in self.request_history:
                    with ui.row().classes(
                        f"{ROW_HEADER} p-2 rounded-lg bg-slate-950/60 border border-white/5 text-xs font-mono"
                    ):
                        with ui.row().classes(ROW_ACTIONS):
                            ui.label(item["time"]).classes("text-slate-400")
                            ui.badge(item["method"], color="indigo")
                            ui.label(item["url"]).classes(
                                "text-slate-200 truncate max-w-xs"
                            )
                        with ui.row().classes(ROW_ACTIONS):
                            status_c = (
                                "text-emerald-400"
                                if item["status"] < 400
                                else "text-rose-400"
                            )
                            ui.label(f"HTTP {item['status']}").classes(
                                f"font-bold {status_c}"
                            )
                            ui.label(f"{item['latency']}ms").classes("text-slate-400")

    def _copy_response(self) -> None:
        """Copy response body to clipboard."""
        if self.last_response_text:
            ui.run_javascript(
                f"navigator.clipboard.writeText({self.last_response_text!r});"
            )
            ui.notify("Response copied to clipboard!", type="positive")

    def _copy_curl(self) -> None:
        """Copy generated cURL command to clipboard."""
        if self.last_curl_cmd:
            ui.run_javascript(f"navigator.clipboard.writeText({self.last_curl_cmd!r});")
            ui.notify("cURL command copied to clipboard!", type="positive")

    def render(self, container: ui.element | None = None) -> None:
        """Render the REST API Endpoints Explorer tab content."""
        super().render(container)
        if container is not None:
            self.container = container
            with self.container:
                self._render_content()
        else:
            self._render_content()

    def _render_content(self) -> None:
        with ui.card().classes(
            "w-full flex-1 min-h-[500px] flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3"
        ):
            # Preset Selector Row
            with ui.row().classes("w-full gap-3 items-center shrink-0"):
                ui.select(
                    options={ep["url"]: ep["label"] for ep in ENDPOINTS},
                    value=self.selected_endpoint,
                    on_change=self._on_endpoint_change,
                    label="Select Preset Endpoint",
                ).props("outlined dense options-dense").classes(
                    "flex-1 text-sm bg-slate-950/60"
                )

            # Endpoint input & execute button row
            with ui.row().classes("w-full gap-2 items-center shrink-0"):
                self.method_select = (
                    ui.select(
                        options=["GET", "POST", "PUT", "DELETE"],
                        value=self.selected_method,
                        on_change=lambda e: setattr(self, "selected_method", e.value),
                    )
                    .props("outlined dense options-dense")
                    .classes("w-28 font-mono text-sm bg-slate-950/60")
                )

                self.url_input = (
                    ui.input(
                        value=self.selected_endpoint,
                        label="Request Path",
                    )
                    .props("outlined dense")
                    .classes("flex-1 font-mono text-sm bg-slate-950/60")
                )

                ui.button(
                    "Execute",
                    icon="send",
                    on_click=self._execute_request,
                ).props("unelevated color=primary").classes(
                    "px-4 font-semibold shadow-md shadow-blue-500/20"
                )

            # Telemetry Status Bar & Action Strip
            with ui.row().classes(
                f"{ROW_HEADER} px-1 shrink-0 bg-slate-950/60 p-2 rounded-xl border border-white/5"
            ):
                with ui.row().classes("items-center gap-3"):
                    self.spinner = ui.spinner("dots", size="sm", color="cyan")
                    self.spinner.visible = False
                    with ui.element("span").classes(BADGE_INFO) as self.status_badge:
                        self.status_label = ui.label("Ready")
                    self.latency_label = ui.label("").classes(
                        "text-xs font-mono text-gray-400"
                    )
                    self.size_label = ui.label("").classes(
                        "text-xs font-mono text-cyan-400/80"
                    )

                with ui.row().classes(ROW_ACTIONS):
                    ui.button(
                        "Copy cURL",
                        icon="terminal",
                        on_click=self._copy_curl,
                    ).props("flat dense size=sm color=indigo").tooltip(
                        "Copy request as cURL command"
                    )
                    ui.button(
                        "Copy Output",
                        icon="content_copy",
                        on_click=self._copy_response,
                    ).props("flat dense size=sm color=cyan")

            # Multi-View Response Inspector Sub-Tabs
            with (
                ui.tabs().classes(
                    "w-full bg-slate-950/80 border border-white/5 rounded-lg p-0.5 shrink-0"
                ) as self.resp_tabs,
                ui.row().classes("w-full gap-1"),
            ):
                self.resp_tab_body = ui.tab(
                    "Response Body", icon="data_object"
                ).classes("text-xs")
                self.resp_tab_headers = ui.tab(
                    "Response Headers", icon="view_list"
                ).classes("text-xs")
                self.resp_tab_curl = ui.tab("cURL Command", icon="terminal").classes(
                    "text-xs"
                )
                self.resp_tab_history = ui.tab(
                    "Request History", icon="history"
                ).classes("text-xs")

            # Response Sub-Panels
            with ui.tab_panels(self.resp_tabs, value=self.resp_tab_body).classes(
                "w-full flex-1 min-h-[250px] bg-transparent p-0 overflow-hidden flex flex-col"
            ):
                # Panel 1: Body
                with (
                    ui.tab_panel(self.resp_tab_body).classes(
                        "w-full h-full min-h-[220px] p-0 overflow-y-auto"
                    ),
                    ui.element("div").classes(
                        f"{CARD_PANEL} h-full min-h-[220px] overflow-y-auto"
                    ),
                ):
                    self.viewer_container = ui.column().classes(
                        "w-full p-0 gap-0 min-h-0"
                    )
                    with self.viewer_container:
                        self.response_viewer = ui.code(
                            "// Select an endpoint above and click Execute to test API responses.",
                            language="json",
                        ).classes("w-full text-xs font-mono text-emerald-400")

                # Panel 2: Headers
                with (
                    ui.tab_panel(self.resp_tab_headers).classes(
                        "w-full h-full min-h-[220px] p-0 overflow-y-auto"
                    ),
                    ui.element("div").classes(
                        f"{CARD_PANEL} h-full min-h-[220px] overflow-y-auto"
                    ),
                ):
                    self.headers_container = ui.column().classes("w-full gap-1")
                    with self.headers_container:
                        ui.label("No headers available yet. Click Execute.").classes(
                            "text-xs text-slate-400 italic p-3"
                        )

                # Panel 3: cURL
                with (
                    ui.tab_panel(self.resp_tab_curl).classes(
                        "w-full h-full min-h-[220px] p-0 overflow-y-auto"
                    ),
                    ui.element("div").classes(
                        f"{CARD_PANEL} h-full min-h-[220px] overflow-y-auto"
                    ),
                ):
                    self.curl_viewer = ui.code(
                        "curl -X GET 'http://localhost:3000/health'",
                        language="bash",
                    ).classes("w-full text-xs font-mono text-cyan-300")

                # Panel 4: History
                with (
                    ui.tab_panel(self.resp_tab_history).classes(
                        "w-full h-full min-h-[220px] p-0 overflow-y-auto"
                    ),
                    ui.element("div").classes(
                        f"{CARD_PANEL} h-full min-h-[220px] overflow-y-auto"
                    ),
                ):
                    self.history_container = ui.column().classes("w-full gap-2")
                    with self.history_container:
                        ui.label("No request history recorded yet.").classes(
                            "text-xs text-slate-400 italic p-3"
                        )
