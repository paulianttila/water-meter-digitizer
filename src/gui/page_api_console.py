"""Interactive REST API Console & Mock Camera Studio Page for NiceGUI."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import time
import urllib.parse
from typing import TYPE_CHECKING, Any

import requests
from nicegui import ui

from api.routes_mock_camera import render_mock_camera_frame
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
)

if TYPE_CHECKING:
    from callbacks import Callbacks

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
        "label": "GET /api/mock_camera (Mock Camera Generator Feed)",
        "url": "/api/mock_camera?value=00452.91241",
        "method": "GET",
    },
    {
        "label": "POST /api/mock_camera/reset (Reset Mock Ticker)",
        "url": "/api/mock_camera/reset?start_value=100.0",
        "method": "POST",
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


class ApiConsolePage:
    """Page allowing users to interactively test REST endpoints and studio mock camera feeds."""

    def __init__(self, callbacks: Callbacks | None = None, port: int = 3000) -> None:
        self.callbacks = callbacks
        self.port = port
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

        # --- Mock Camera Studio State ---
        self.mock_mode = "fixed"
        self.mock_value = "00452.91241"
        self.mock_rate = 0.005
        self.mock_rotate = 0.0
        self.mock_glare = False
        self.mock_glare_pos = "320,240"
        self.mock_glare_intensity = 1.0
        self.mock_noise = 0.0
        self.mock_blur = 0.0
        self.mock_brightness = 1.0
        self.mock_contrast = 1.0
        self.mock_lcd_color = "black"
        self.mock_lcd_bg = "grey"
        self.mock_needle_color = "red"
        self.mock_width = 640
        self.mock_height = 480
        self.mock_digit_overrides: list[str] = ["", "", "", "", ""]
        self.mock_analog_overrides: list[str] = ["", "", "", ""]
        self.mock_auto_refresh = True
        self.mock_streaming = False
        self.mock_stream_timer: ui.timer | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()

        # Mock UI Element references
        self.mock_img_elem: ui.image | None = None
        self.mock_img_src: str = ""
        self.mock_url_display: ui.input | None = None
        self.mock_meta_meter_val: ui.label | None = None
        self.mock_meta_dig_val: ui.label | None = None
        self.mock_meta_ana_val: ui.label | None = None
        self.mock_meta_size_badge: ui.label | None = None
        self.mock_spinner: ui.spinner | None = None
        self.mock_mode_select: ui.select | None = None
        self.mock_value_input: ui.input | None = None
        self.mock_rate_input: ui.number | None = None
        self.mock_rot_badge: ui.badge | None = None
        self.mock_rot_slider: ui.slider | None = None
        self.mock_glare_switch: ui.switch | None = None
        self.mock_glare_pos_input: ui.input | None = None
        self.mock_noise_slider: ui.slider | None = None
        self.mock_blur_slider: ui.slider | None = None
        self.mock_bright_slider: ui.slider | None = None
        self.mock_contrast_slider: ui.slider | None = None
        self.mock_lcd_color_select: ui.select | None = None
        self.mock_lcd_bg_select: ui.select | None = None
        self.mock_needle_color_select: ui.select | None = None
        self.mock_width_input: ui.number | None = None
        self.mock_height_input: ui.number | None = None
        self.mock_digit_inputs: list[ui.input] = []
        self.mock_analog_inputs: list[ui.input] = []

        # Generate initial frame synchronously so picture is immediately available on mount
        try:
            jpeg_bytes, _ = render_mock_camera_frame(
                value=self.mock_value,
                mode=self.mock_mode,
                width=self.mock_width,
                height=self.mock_height,
            )
            b64 = base64.b64encode(jpeg_bytes).decode("ascii")
            self.mock_img_src = f"data:image/jpeg;base64,{b64}"
        except Exception:
            self.mock_img_src = ""

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

        full_url = f"{self._get_base_url()}{endpoint}"
        start_time = time.perf_counter()

        def _do_req() -> dict[str, Any]:
            try:
                if method == "POST":
                    resp = requests.post(full_url, timeout=10.0)
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
                if is_image:
                    with ui.column().classes(
                        "w-full items-center gap-3 p-4 bg-slate-900/80 rounded-xl border border-white/10"
                    ):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label("Rendered Camera Picture").classes(
                                "text-sm font-semibold text-cyan-300"
                            )
                            with ui.row().classes("gap-2 items-center"):
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

    def _copy_response(self) -> None:
        if self.last_response_text:
            ui.run_javascript(
                f"navigator.clipboard.writeText({json.dumps(self.last_response_text)});"
            )
            ui.notify("Response copied to clipboard!", type="positive")

    # --- Mock Camera Studio Helpers ---
    def build_mock_query_string(self) -> str:
        """Construct query parameter string from active mock camera state."""
        params: dict[str, Any] = {}
        if self.mock_mode != "fixed":
            params["mode"] = self.mock_mode
        if self.mock_mode == "fixed" and self.mock_value:
            params["value"] = self.mock_value
        elif self.mock_mode in ("ticker", "flow") and self.mock_rate != 0.005:
            params["rate"] = round(self.mock_rate, 4)

        if self.mock_rotate != 0.0:
            params["rotate"] = round(self.mock_rotate, 1)
        if self.mock_glare:
            params["glare"] = "true"
            if self.mock_glare_intensity != 1.0:
                params["glare_intensity"] = round(self.mock_glare_intensity, 2)
            if self.mock_glare_pos and self.mock_glare_pos != "320,240":
                params["glare_pos"] = self.mock_glare_pos

        if self.mock_noise > 0.0:
            params["noise"] = round(self.mock_noise, 1)
        if self.mock_blur > 0.0:
            params["blur"] = round(self.mock_blur, 1)
        if self.mock_brightness != 1.0:
            params["brightness"] = round(self.mock_brightness, 2)
        if self.mock_contrast != 1.0:
            params["contrast"] = round(self.mock_contrast, 2)

        if self.mock_lcd_color != "black":
            params["lcd_color"] = self.mock_lcd_color
        if self.mock_lcd_bg != "grey":
            params["lcd_bg"] = self.mock_lcd_bg
        if self.mock_needle_color != "red":
            params["needle_color"] = self.mock_needle_color
        if self.mock_width != 640:
            params["width"] = self.mock_width
        if self.mock_height != 480:
            params["height"] = self.mock_height

        for idx, val in enumerate(self.mock_digit_overrides, start=1):
            if val.strip():
                with contextlib.suppress(ValueError):
                    params[f"digit{idx}"] = float(val)

        for idx, val in enumerate(self.mock_analog_overrides, start=1):
            if val.strip():
                with contextlib.suppress(ValueError):
                    params[f"analog{idx}"] = float(val)

        return urllib.parse.urlencode(params)

    def get_mock_url(self, relative: bool = True) -> str:
        """Get full or relative mock camera URL with query parameters."""
        qs = self.build_mock_query_string()
        path = f"/api/mock_camera?{qs}" if qs else "/api/mock_camera"
        if relative:
            return path
        return f"{self._get_base_url()}{path}"

    async def _generate_mock_frame(self) -> None:
        """Render mock camera snapshot in-process and update UI elements immediately."""
        if self.mock_spinner:
            self.mock_spinner.visible = True

        if self.mock_url_display:
            self.mock_url_display.value = self.get_mock_url(relative=True)

        d_vals: list[float | None] = []
        for val in self.mock_digit_overrides:
            if val.strip():
                try:
                    d_vals.append(float(val))
                    continue
                except ValueError:
                    pass
            d_vals.append(None)

        a_vals: list[float | None] = []
        for val in self.mock_analog_overrides:
            if val.strip():
                try:
                    a_vals.append(float(val))
                    continue
                except ValueError:
                    pass
            a_vals.append(None)

        g_pos = self.mock_glare_pos if self.mock_glare and self.mock_glare_pos else None

        def _do_render() -> dict[str, Any]:
            try:
                jpeg_bytes, headers = render_mock_camera_frame(
                    value=self.mock_value if self.mock_mode == "fixed" else None,
                    mode=self.mock_mode,
                    rate=self.mock_rate,
                    rotate=self.mock_rotate,
                    glare=self.mock_glare,
                    glare_pos=g_pos,
                    glare_intensity=self.mock_glare_intensity,
                    noise=self.mock_noise,
                    blur=self.mock_blur,
                    brightness=self.mock_brightness,
                    contrast=self.mock_contrast,
                    lcd_color=self.mock_lcd_color,
                    lcd_bg=self.mock_lcd_bg,
                    needle_color=self.mock_needle_color,
                    width=self.mock_width,
                    height=self.mock_height,
                    digit1=d_vals[0] if len(d_vals) > 0 else None,
                    digit2=d_vals[1] if len(d_vals) > 1 else None,
                    digit3=d_vals[2] if len(d_vals) > 2 else None,
                    digit4=d_vals[3] if len(d_vals) > 3 else None,
                    digit5=d_vals[4] if len(d_vals) > 4 else None,
                    analog1=a_vals[0] if len(a_vals) > 0 else None,
                    analog2=a_vals[1] if len(a_vals) > 1 else None,
                    analog3=a_vals[2] if len(a_vals) > 2 else None,
                    analog4=a_vals[3] if len(a_vals) > 3 else None,
                )
                b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                return {
                    "ok": True,
                    "data_uri": f"data:image/jpeg;base64,{b64}",
                    "meter_val": headers.get("X-Mock-Meter-Value", "N/A"),
                    "dig_val": headers.get("X-Mock-Digital-Value", "N/A"),
                    "ana_val": headers.get("X-Mock-Analog-Value", "N/A"),
                    "size_kb": round(len(jpeg_bytes) / 1024.0, 1),
                }
            except Exception as ex:
                return {
                    "ok": False,
                    "data_uri": "",
                    "meter_val": "Err",
                    "dig_val": "",
                    "ana_val": "",
                    "size_kb": 0.0,
                    "err": str(ex),
                }

        res = await asyncio.to_thread(_do_render)

        if self.mock_spinner:
            self.mock_spinner.visible = False

        if res["ok"]:
            self.mock_img_src = res["data_uri"]
            if self.mock_img_elem:
                self.mock_img_elem.set_source(self.mock_img_src)
            if self.mock_meta_meter_val:
                self.mock_meta_meter_val.text = res["meter_val"]
            if self.mock_meta_dig_val:
                self.mock_meta_dig_val.text = res["dig_val"]
            if self.mock_meta_ana_val:
                self.mock_meta_ana_val.text = res["ana_val"]
            if self.mock_meta_size_badge:
                self.mock_meta_size_badge.text = (
                    f"{self.mock_width}x{self.mock_height} ({res['size_kb']} KB)"
                )

    def sync_state_from_url(self, url: str) -> None:
        """Parse mock camera URL query parameters and synchronize state and UI controls."""
        with contextlib.suppress(Exception):
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)

            if qs.get("mode"):
                self.mock_mode = qs["mode"][0]
                if self.mock_mode_select:
                    self.mock_mode_select.value = self.mock_mode
            if qs.get("value"):
                self.mock_value = qs["value"][0]
                if self.mock_value_input:
                    self.mock_value_input.value = self.mock_value
            if qs.get("rate"):
                with contextlib.suppress(ValueError):
                    self.mock_rate = float(qs["rate"][0])
                    if self.mock_rate_input:
                        self.mock_rate_input.value = self.mock_rate
            if qs.get("rotate"):
                with contextlib.suppress(ValueError):
                    self.mock_rotate = float(qs["rotate"][0])
                    if self.mock_rot_slider:
                        self.mock_rot_slider.value = self.mock_rotate
                    if self.mock_rot_badge:
                        self.mock_rot_badge.text = f"{self.mock_rotate:.0f}°"
            if qs.get("glare"):
                self.mock_glare = qs["glare"][0].lower() in ("true", "1", "yes")
                if self.mock_glare_switch:
                    self.mock_glare_switch.value = self.mock_glare
            if qs.get("glare_pos"):
                self.mock_glare_pos = qs["glare_pos"][0]
                if self.mock_glare_pos_input:
                    self.mock_glare_pos_input.value = self.mock_glare_pos
            if qs.get("noise"):
                with contextlib.suppress(ValueError):
                    self.mock_noise = float(qs["noise"][0])
                    if self.mock_noise_slider:
                        self.mock_noise_slider.value = self.mock_noise
            if qs.get("blur"):
                with contextlib.suppress(ValueError):
                    self.mock_blur = float(qs["blur"][0])
                    if self.mock_blur_slider:
                        self.mock_blur_slider.value = self.mock_blur
            if qs.get("brightness"):
                with contextlib.suppress(ValueError):
                    self.mock_brightness = float(qs["brightness"][0])
                    if self.mock_bright_slider:
                        self.mock_bright_slider.value = self.mock_brightness
            if qs.get("contrast"):
                with contextlib.suppress(ValueError):
                    self.mock_contrast = float(qs["contrast"][0])
                    if self.mock_contrast_slider:
                        self.mock_contrast_slider.value = self.mock_contrast
            if qs.get("lcd_color"):
                self.mock_lcd_color = qs["lcd_color"][0]
                if self.mock_lcd_color_select:
                    self.mock_lcd_color_select.value = self.mock_lcd_color
            if qs.get("lcd_bg"):
                self.mock_lcd_bg = qs["lcd_bg"][0]
                if self.mock_lcd_bg_select:
                    self.mock_lcd_bg_select.value = self.mock_lcd_bg
            if qs.get("needle_color"):
                self.mock_needle_color = qs["needle_color"][0]
                if self.mock_needle_color_select:
                    self.mock_needle_color_select.value = self.mock_needle_color
            if qs.get("width"):
                with contextlib.suppress(ValueError):
                    self.mock_width = int(qs["width"][0])
                    if self.mock_width_input:
                        self.mock_width_input.value = self.mock_width
            if qs.get("height"):
                with contextlib.suppress(ValueError):
                    self.mock_height = int(qs["height"][0])
                    if self.mock_height_input:
                        self.mock_height_input.value = self.mock_height
            for i in range(5):
                key = f"digit{i+1}"
                if qs.get(key):
                    self.mock_digit_overrides[i] = qs[key][0]
                    if i < len(self.mock_digit_inputs) and self.mock_digit_inputs[i]:
                        self.mock_digit_inputs[i].value = qs[key][0]
            for i in range(4):
                key = f"analog{i+1}"
                if qs.get(key):
                    self.mock_analog_overrides[i] = qs[key][0]
                    if i < len(self.mock_analog_inputs) and self.mock_analog_inputs[i]:
                        self.mock_analog_inputs[i].value = qs[key][0]

    async def _execute_mock_query(self) -> None:
        """Execute mock camera query button action: syncs from URL display input if present, renders frame, and notifies."""
        if self.mock_url_display and self.mock_url_display.value:
            self.sync_state_from_url(self.mock_url_display.value)
        await self._generate_mock_frame()
        ui.notify("Camera snapshot updated from query parameters", type="positive")

    async def _on_mock_param_change(self) -> None:
        """Trigger update when any mock parameter input changes."""
        if self.mock_url_display:
            self.mock_url_display.value = self.get_mock_url(relative=True)
        if self.mock_auto_refresh:
            await self._generate_mock_frame()

    def _toggle_mock_streaming(self, e: Any) -> None:
        """Toggle live periodic ticker stream timer."""
        self.mock_streaming = bool(e.value)
        if self.mock_stream_timer:
            self.mock_stream_timer.active = self.mock_streaming
        if self.mock_streaming:
            ui.notify("Live Mock Stream Active (1 frame/sec)", type="info")

    async def _reset_to_defaults(self) -> None:
        """Reset all mock camera studio parameters and UI controls to default values."""
        self.mock_mode = "fixed"
        self.mock_value = "00452.91241"
        self.mock_rate = 0.005
        self.mock_rotate = 0.0
        self.mock_glare = False
        self.mock_glare_pos = "320,240"
        self.mock_glare_intensity = 1.0
        self.mock_noise = 0.0
        self.mock_blur = 0.0
        self.mock_brightness = 1.0
        self.mock_contrast = 1.0
        self.mock_lcd_color = "black"
        self.mock_lcd_bg = "grey"
        self.mock_needle_color = "red"
        self.mock_width = 640
        self.mock_height = 480
        self.mock_digit_overrides = ["", "", "", "", ""]
        self.mock_analog_overrides = ["", "", "", ""]

        if self.mock_mode_select:
            self.mock_mode_select.value = "fixed"
        if self.mock_value_input:
            self.mock_value_input.value = "00452.91241"
            self.mock_value_input.enabled = True
        if self.mock_rate_input:
            self.mock_rate_input.value = 0.005
            self.mock_rate_input.enabled = False
        if self.mock_rot_slider:
            self.mock_rot_slider.value = 0.0
        if self.mock_rot_badge:
            self.mock_rot_badge.text = "0°"
        if self.mock_glare_switch:
            self.mock_glare_switch.value = False
        if self.mock_glare_pos_input:
            self.mock_glare_pos_input.value = "320,240"
        if self.mock_noise_slider:
            self.mock_noise_slider.value = 0.0
        if self.mock_blur_slider:
            self.mock_blur_slider.value = 0.0
        if self.mock_bright_slider:
            self.mock_bright_slider.value = 1.0
        if self.mock_contrast_slider:
            self.mock_contrast_slider.value = 1.0
        if self.mock_lcd_color_select:
            self.mock_lcd_color_select.value = "black"
        if self.mock_lcd_bg_select:
            self.mock_lcd_bg_select.value = "grey"
        if self.mock_needle_color_select:
            self.mock_needle_color_select.value = "red"
        if self.mock_width_input:
            self.mock_width_input.value = 640
        if self.mock_height_input:
            self.mock_height_input.value = 480
        for inp in self.mock_digit_inputs:
            if inp:
                inp.value = ""
        for inp in self.mock_analog_inputs:
            if inp:
                inp.value = ""

        if self.mock_url_display:
            self.mock_url_display.value = self.get_mock_url(relative=True)

        await self._generate_mock_frame()
        ui.notify("Mock camera parameters reset to default values", type="positive")

    async def _reset_mock_ticker(self) -> None:
        """Send reset request to mock camera ticker endpoint."""
        reset_url = f"{self._get_base_url()}/api/mock_camera/reset?start_value=100.0"
        try:
            resp = await asyncio.to_thread(requests.post, reset_url, timeout=5.0)
            if resp.ok:
                ui.notify("Mock camera ticker reset to 100.0", type="positive")
                await self._generate_mock_frame()
            else:
                ui.notify(f"Reset failed: HTTP {resp.status_code}", type="warning")
        except Exception as ex:
            ui.notify(f"Reset error: {ex}", type="negative")

    def _copy_mock_url(self) -> None:
        """Copy the mock camera relative or full URL to clipboard."""
        url = self.get_mock_url(relative=True)
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(url)});")
        ui.notify("Mock camera URL copied to clipboard!", type="positive")

    def _apply_as_active_image_source(self) -> None:
        """Set current mock camera URL as the active [ImageSource] URL in configuration."""
        if not self.callbacks:
            ui.notify(
                "Configuration callbacks unavailable in standalone mode",
                type="warning",
            )
            return

        mock_url = f"{self._get_base_url()}{self.get_mock_url(relative=True)}"
        try:
            cfg = self.callbacks.get_config()
            cfg.image_source.url = mock_url
            saved_str = cfg.save_to_string()
            self.callbacks.save_config_file(saved_str)
            self.callbacks.use_config()
            ui.notify(f"Applied to [ImageSource] URL: {mock_url}", type="positive")
        except Exception as ex:
            ui.notify(f"Failed to update [ImageSource] URL: {ex}", type="negative")

    def show(self) -> None:
        with ui.column().classes(
            "w-full h-full flex flex-col gap-3 p-4 overflow-hidden"
        ):
            # Header
            with (
                ui.row().classes("w-full justify-between items-center shrink-0 mb-1"),
                ui.row().classes("items-center gap-3"),
            ):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 "
                    "flex items-center justify-center shadow-lg shadow-cyan-500/10"
                ):
                    ui.icon("terminal", color="cyan").classes("text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("REST API Console & Studio").classes("text-h4")
                    ui.label(
                        "Interactive endpoint debugger, REST tester & procedural mock camera studio"
                    ).classes("text-xs text-gray-400")

            # Main Tabs Container (Fills full view)
            with (
                ui.tabs().classes(
                    "w-full bg-slate-900/90 border border-white/10 rounded-xl p-1 shrink-0"
                ) as tabs,
                ui.row().classes("w-full gap-2"),
            ):
                tab_rest = ui.tab("REST Endpoints", icon="api").classes(
                    "font-semibold text-sm"
                )
                tab_mock = ui.tab("Mock Camera Studio", icon="photo_camera").classes(
                    "font-semibold text-sm"
                )
                tab_swagger = ui.tab("Swagger UI", icon="auto_stories").classes(
                    "font-semibold text-sm"
                )

            async def _on_tab_panel_change(e: Any) -> None:
                if e.value == tab_mock:
                    await self._generate_mock_frame()

            with ui.tab_panels(
                tabs, value=tab_rest, on_change=_on_tab_panel_change
            ).classes("w-full flex-1 min-h-0 bg-transparent p-0 overflow-hidden"):
                # =========================================================================
                # TAB 1: REST Endpoints Explorer
                # =========================================================================
                with (
                    ui.tab_panel(tab_rest).classes(
                        "w-full h-full flex flex-col p-0 gap-3 overflow-hidden"
                    ),
                    ui.card().classes(
                        "w-full flex-1 min-h-0 flex flex-col p-5 bg-slate-900 border border-white/10 rounded-2xl gap-4 overflow-hidden"
                    ),
                ):
                    # Selector Row
                    with ui.row().classes("w-full gap-3 items-center shrink-0"):
                        ui.select(
                            options={ep["url"]: ep["label"] for ep in ENDPOINTS},
                            value=self.selected_endpoint,
                            on_change=self._on_endpoint_change,
                            label="Select Preset Endpoint",
                        ).props("outlined dense options-dense").classes(
                            "flex-1 text-sm bg-slate-950/60"
                        )

                    # Endpoint input & execute button
                    with ui.row().classes("w-full gap-2 items-center shrink-0"):
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

                    # Status Bar
                    with ui.row().classes(
                        "w-full justify-between items-center px-1 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            self.spinner = ui.spinner("dots", size="sm", color="cyan")
                            self.spinner.visible = False
                            with ui.element("span").classes(
                                BADGE_INFO
                            ) as self.status_badge:
                                self.status_label = ui.label("Ready")
                            self.latency_label = ui.label("").classes(
                                "text-xs font-mono text-gray-400"
                            )

                        ui.button(
                            "Copy Output",
                            icon="content_copy",
                            on_click=self._copy_response,
                        ).props("flat dense size=sm color=cyan")

                    # Response Viewer
                    with ui.element("div").classes(
                        "w-full flex-1 min-h-0 rounded-xl bg-slate-950 p-4 border border-white/10 overflow-y-auto"
                    ):
                        self.viewer_container = ui.column().classes("w-full p-0 gap-0")
                        with self.viewer_container:
                            self.response_viewer = ui.code(
                                "// Select an endpoint above and click Execute to test API responses.",
                                language="json",
                            ).classes("w-full text-xs font-mono text-emerald-400")

                # =========================================================================
                # TAB 2: Mock Camera Studio (Dedicated Simulator & Generator)
                # =========================================================================
                with ui.tab_panel(tab_mock).classes(
                    "w-full h-full flex flex-col gap-3 p-0 overflow-hidden"
                ):
                    # TOP QUERY & ACTION BAR
                    with ui.card().classes(
                        "w-full p-3 bg-slate-900 border border-white/10 rounded-2xl shrink-0 gap-2"
                    ):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-3"
                        ):
                            with ui.row().classes("flex-1 items-center gap-2 min-w-0"):
                                ui.icon("travel_explore", color="cyan").classes(
                                    "text-lg"
                                )
                                self.mock_url_display = (
                                    ui.input(
                                        value=self.get_mock_url(relative=True),
                                        label="Mock Camera Query URL",
                                    )
                                    .props("outlined dense")
                                    .classes(
                                        "flex-1 font-mono text-xs bg-slate-950 text-cyan-300"
                                    )
                                )
                                self.mock_url_display.on(
                                    "keydown.enter", self._execute_mock_query
                                )

                            ui.button(
                                "Make Query / Update Snapshot",
                                icon="photo_camera",
                                on_click=self._execute_mock_query,
                            ).props("unelevated color=primary").classes(
                                "px-4 font-bold text-xs shadow-md shadow-blue-500/20"
                            )

                        with ui.row().classes(
                            "w-full items-center justify-between gap-3 pt-1 border-t border-white/5"
                        ):
                            with ui.row().classes("items-center gap-4"):
                                ui.switch(
                                    "Auto-Update on Change",
                                    value=self.mock_auto_refresh,
                                    on_change=lambda e: setattr(
                                        self, "mock_auto_refresh", e.value
                                    ),
                                ).props("dense size=sm color=cyan").classes(
                                    "text-xs font-semibold text-gray-300"
                                )

                                ui.switch(
                                    "Live Stream Ticker (1s)",
                                    value=self.mock_streaming,
                                    on_change=self._toggle_mock_streaming,
                                ).props("dense size=sm color=emerald").classes(
                                    "text-xs font-semibold text-gray-300"
                                )

                            with ui.row().classes("items-center gap-2"):
                                ui.button(
                                    "Reset Defaults",
                                    icon="settings_backup_restore",
                                    on_click=self._reset_to_defaults,
                                ).props("outline dense size=sm color=purple").classes(
                                    "text-xs font-semibold"
                                )

                                ui.button(
                                    "Reset Ticker",
                                    icon="restart_alt",
                                    on_click=self._reset_mock_ticker,
                                ).props("outline dense size=sm color=amber").classes(
                                    "text-xs font-semibold"
                                )

                                ui.button(
                                    "Copy Mock URL",
                                    icon="content_copy",
                                    on_click=self._copy_mock_url,
                                ).props("outline dense size=sm color=cyan").classes(
                                    "text-xs font-semibold"
                                )

                                ui.button(
                                    "Set as [ImageSource] URL",
                                    icon="download_done",
                                    on_click=self._apply_as_active_image_source,
                                ).props(
                                    "unelevated dense size=sm color=emerald"
                                ).classes(
                                    "text-xs font-semibold"
                                )

                    # LOWER WORKSPACE: Two-Column Split (Parameters Left, Snapshot Right)
                    with ui.element("div").classes(
                        "w-full flex-1 min-h-0 grid grid-cols-2 gap-4 overflow-hidden"
                    ):
                        # LEFT COLUMN: Parameters Controls (Scrollable)
                        with ui.card().classes(
                            "w-full h-full flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3 overflow-y-auto"
                        ):
                            with ui.row().classes(
                                "w-full items-center gap-2 shrink-0 border-b border-white/5 pb-2"
                            ):
                                ui.icon("tune", color="cyan").classes("text-lg")
                                ui.label("Procedural Mock Camera Parameters").classes(
                                    "text-sm font-bold text-white"
                                )

                            # --- Section 1: Mode & Value ---
                            with ui.column().classes(
                                "w-full gap-2 p-3 bg-slate-950/60 rounded-xl border border-white/5"
                            ):
                                ui.label("Feed Mode & Target Reading").classes(
                                    "text-xs font-semibold text-cyan-400 uppercase tracking-wide"
                                )
                                with ui.grid(columns=2).classes("w-full gap-2"):

                                    async def _on_mode_change(e: Any) -> None:
                                        self.mock_mode = e.value
                                        if self.mock_value_input:
                                            self.mock_value_input.enabled = (
                                                self.mock_mode == "fixed"
                                            )
                                        if self.mock_rate_input:
                                            self.mock_rate_input.enabled = (
                                                self.mock_mode in ("ticker", "flow")
                                            )
                                        await self._on_mock_param_change()

                                    self.mock_mode_select = (
                                        ui.select(
                                            options=[
                                                "fixed",
                                                "ticker",
                                                "random",
                                                "flow",
                                            ],
                                            value=self.mock_mode,
                                            on_change=_on_mode_change,
                                            label="Mode",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_val_change(e: Any) -> None:
                                        self.mock_value = e.value
                                        await self._on_mock_param_change()

                                    self.mock_value_input = (
                                        ui.input(
                                            label="Meter Value",
                                            value=self.mock_value,
                                            on_change=_on_val_change,
                                        )
                                        .props("outlined dense")
                                        .classes("font-mono text-xs")
                                    )

                                with ui.row().classes(
                                    "w-full items-center justify-between gap-2"
                                ):

                                    async def _on_rate_change(e: Any) -> None:
                                        self.mock_rate = (
                                            float(e.value)
                                            if e.value is not None
                                            else 0.005
                                        )
                                        await self._on_mock_param_change()

                                    self.mock_rate_input = (
                                        ui.number(
                                            label="Ticker Rate / Frame",
                                            value=self.mock_rate,
                                            step=0.001,
                                            on_change=_on_rate_change,
                                        )
                                        .props("outlined dense")
                                        .classes("w-44 text-xs")
                                    )
                                    self.mock_rate_input.enabled = self.mock_mode in (
                                        "ticker",
                                        "flow",
                                    )

                            # --- Section 2: Optical Effects & Distortions ---
                            with (
                                ui.expansion(
                                    "Optical Effects, Glare & Noise",
                                    icon="blur_on",
                                    value=True,
                                ).classes(
                                    "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
                                ),
                                ui.column().classes("w-full gap-3 p-1"),
                            ):
                                # Rotation
                                with ui.row().classes(
                                    "w-full items-center justify-between"
                                ):
                                    ui.label("Rotation Angle").classes(
                                        "text-xs text-gray-300"
                                    )
                                    self.mock_rot_badge = ui.badge(
                                        f"{self.mock_rotate:.0f}°", color="cyan"
                                    )

                                async def _on_rot_change(e: Any) -> None:
                                    self.mock_rotate = float(e.value)
                                    if self.mock_rot_badge:
                                        self.mock_rot_badge.text = (
                                            f"{self.mock_rotate:.0f}°"
                                        )
                                    await self._on_mock_param_change()

                                self.mock_rot_slider = (
                                    ui.slider(
                                        min=-180.0,
                                        max=180.0,
                                        step=1.0,
                                        value=self.mock_rotate,
                                        on_change=_on_rot_change,
                                    )
                                    .props("color=cyan dense")
                                    .classes("w-full")
                                )

                                # Glare & Glare Intensity
                                with ui.row().classes(
                                    "w-full items-center justify-between gap-2"
                                ):

                                    async def _on_glare_change(e: Any) -> None:
                                        self.mock_glare = e.value
                                        await self._on_mock_param_change()

                                    self.mock_glare_switch = (
                                        ui.switch(
                                            "Enable Glare Hotspot",
                                            value=self.mock_glare,
                                            on_change=_on_glare_change,
                                        )
                                        .props("dense size=sm color=cyan")
                                        .classes("text-xs text-gray-300")
                                    )

                                    async def _on_gpos_change(e: Any) -> None:
                                        self.mock_glare_pos = e.value
                                        await self._on_mock_param_change()

                                    self.mock_glare_pos_input = (
                                        ui.input(
                                            label="Glare Center (X,Y)",
                                            value=self.mock_glare_pos,
                                            on_change=_on_gpos_change,
                                        )
                                        .props("outlined dense")
                                        .classes("w-36 text-xs")
                                    )

                                # Noise & Blur
                                with ui.grid(columns=2).classes("w-full gap-3"):
                                    with ui.column().classes("gap-1"):
                                        ui.label("Gaussian Noise").classes(
                                            "text-xs text-gray-300"
                                        )

                                        async def _on_noise_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_noise = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_noise_slider = ui.slider(
                                            min=0.0,
                                            max=30.0,
                                            step=0.5,
                                            value=self.mock_noise,
                                            on_change=_on_noise_change,
                                        ).props("color=cyan dense")

                                    with ui.column().classes("gap-1"):
                                        ui.label("Gaussian Blur").classes(
                                            "text-xs text-gray-300"
                                        )

                                        async def _on_blur_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_blur = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_blur_slider = ui.slider(
                                            min=0.0,
                                            max=5.0,
                                            step=0.2,
                                            value=self.mock_blur,
                                            on_change=_on_blur_change,
                                        ).props("color=cyan dense")

                                # Brightness & Contrast
                                with ui.grid(columns=2).classes("w-full gap-3"):
                                    with ui.column().classes("gap-1"):
                                        ui.label("Brightness").classes(
                                            "text-xs text-gray-300"
                                        )

                                        async def _on_bright_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_brightness = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_bright_slider = ui.slider(
                                            min=0.2,
                                            max=2.0,
                                            step=0.05,
                                            value=self.mock_brightness,
                                            on_change=_on_bright_change,
                                        ).props("color=cyan dense")

                                    with ui.column().classes("gap-1"):
                                        ui.label("Contrast").classes(
                                            "text-xs text-gray-300"
                                        )

                                        async def _on_contrast_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_contrast = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_contrast_slider = ui.slider(
                                            min=0.2,
                                            max=2.0,
                                            step=0.05,
                                            value=self.mock_contrast,
                                            on_change=_on_contrast_change,
                                        ).props("color=cyan dense")

                            # --- Section 3: Themes & Dimensions ---
                            with ui.expansion(
                                "Theme Colors & Frame Size",
                                icon="palette",
                                value=False,
                            ).classes(
                                "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
                            ):
                                with ui.grid(columns=3).classes("w-full gap-2 p-1"):

                                    async def _on_lcd_col(e: Any) -> None:
                                        self.mock_lcd_color = e.value
                                        await self._on_mock_param_change()

                                    self.mock_lcd_color_select = (
                                        ui.select(
                                            options=[
                                                "black",
                                                "blue",
                                            ],
                                            value=self.mock_lcd_color,
                                            on_change=_on_lcd_col,
                                            label="LCD Text",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_lcd_bg(e: Any) -> None:
                                        self.mock_lcd_bg = e.value
                                        await self._on_mock_param_change()

                                    self.mock_lcd_bg_select = (
                                        ui.select(
                                            options=[
                                                "grey",
                                                "green",
                                            ],
                                            value=self.mock_lcd_bg,
                                            on_change=_on_lcd_bg,
                                            label="LCD BG",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_needle_col(e: Any) -> None:
                                        self.mock_needle_color = e.value
                                        await self._on_mock_param_change()

                                    self.mock_needle_color_select = (
                                        ui.select(
                                            options=[
                                                "red",
                                                "black",
                                            ],
                                            value=self.mock_needle_color,
                                            on_change=_on_needle_col,
                                            label="Needle",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                with ui.grid(columns=2).classes("w-full gap-2 p-1"):

                                    async def _on_w(e: Any) -> None:
                                        self.mock_width = (
                                            int(e.value) if e.value else 640
                                        )
                                        await self._on_mock_param_change()

                                    self.mock_width_input = (
                                        ui.number(
                                            label="Width (px)",
                                            value=self.mock_width,
                                            step=32,
                                            on_change=_on_w,
                                        )
                                        .props("outlined dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_h(e: Any) -> None:
                                        self.mock_height = (
                                            int(e.value) if e.value else 480
                                        )
                                        await self._on_mock_param_change()

                                    self.mock_height_input = (
                                        ui.number(
                                            label="Height (px)",
                                            value=self.mock_height,
                                            step=32,
                                            on_change=_on_h,
                                        )
                                        .props("outlined dense")
                                        .classes("text-xs")
                                    )

                            # --- Section 4: Digit & Dial Overrides ---
                            with (
                                ui.expansion(
                                    "Per-Digit & Dial Direct Overrides",
                                    icon="pin",
                                    value=False,
                                ).classes(
                                    "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
                                ),
                                ui.column().classes("w-full gap-2 p-1"),
                            ):
                                ui.label(
                                    "Digital Digits (0.0 - 9.9, or blank)"
                                ).classes("text-xs text-gray-400 font-semibold")
                                self.mock_digit_inputs = []
                                with ui.grid(columns=5).classes("w-full gap-1"):
                                    for i in range(5):

                                        def _make_dig_cb(idx: int):
                                            async def _cb(e: Any) -> None:
                                                self.mock_digit_overrides[idx] = (
                                                    str(e.value)
                                                    if e.value is not None
                                                    else ""
                                                )
                                                await self._on_mock_param_change()

                                            return _cb

                                        d_inp = (
                                            ui.input(
                                                label=f"D{i+1}",
                                                value=self.mock_digit_overrides[i],
                                                on_change=_make_dig_cb(i),
                                            )
                                            .props("outlined dense")
                                            .classes("font-mono text-xs")
                                        )
                                        self.mock_digit_inputs.append(d_inp)

                                ui.label(
                                    "Analog Needles (0.0 - 9.9, or blank)"
                                ).classes("text-xs text-gray-400 font-semibold")
                                self.mock_analog_inputs = []
                                with ui.grid(columns=4).classes("w-full gap-1"):
                                    for i in range(4):

                                        def _make_ana_cb(idx: int):
                                            async def _cb(e: Any) -> None:
                                                self.mock_analog_overrides[idx] = (
                                                    str(e.value)
                                                    if e.value is not None
                                                    else ""
                                                )
                                                await self._on_mock_param_change()

                                            return _cb

                                        a_inp = (
                                            ui.input(
                                                label=f"A{i+1}",
                                                value=self.mock_analog_overrides[i],
                                                on_change=_make_ana_cb(i),
                                            )
                                            .props("outlined dense")
                                            .classes("font-mono text-xs")
                                        )
                                        self.mock_analog_inputs.append(a_inp)

                        # RIGHT COLUMN: Live Generated Frame & Output Studio
                        with ui.card().classes(
                            "w-full h-full flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3 overflow-y-auto"
                        ):
                            with ui.row().classes(
                                "w-full justify-between items-center shrink-0 border-b border-white/5 pb-2"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    self.mock_spinner = ui.spinner(
                                        "dots", size="sm", color="cyan"
                                    )
                                    self.mock_spinner.visible = False
                                    ui.label("Live Generated Camera Picture").classes(
                                        "text-sm font-bold text-white"
                                    )

                                with ui.row().classes("items-center gap-2"):
                                    self.mock_meta_size_badge = ui.label(
                                        f"{self.mock_width}x{self.mock_height}"
                                    ).classes("text-xs text-gray-400 font-mono")

                            # Live Rendered Image Container
                            with ui.element("div").classes(
                                "w-full flex-1 min-h-[320px] flex items-center justify-center bg-slate-950 rounded-xl border border-white/10 p-2 overflow-hidden relative"
                            ):
                                self.mock_img_elem = (
                                    ui.image(self.mock_img_src)
                                    .props('id="mock-camera-preview-img" fit="contain"')
                                    .classes(
                                        "w-full h-full max-h-[440px] object-contain rounded-lg shadow-md"
                                    )
                                    .style(
                                        "max-width: 100%; max-height: 100%; width: 100%; height: 100%;"
                                    )
                                )

                            # Telemetry Badges
                            with ui.row().classes(
                                "w-full items-center justify-between p-2.5 bg-slate-950/80 rounded-xl border border-white/5"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label("Meter:").classes("text-xs text-gray-400")
                                    self.mock_meta_meter_val = ui.label(
                                        self.mock_value
                                    ).classes(
                                        "text-xs font-mono font-bold text-cyan-300"
                                    )

                                with ui.row().classes("items-center gap-2"):
                                    ui.label("Digital:").classes(
                                        "text-xs text-gray-400"
                                    )
                                    self.mock_meta_dig_val = ui.label("00452").classes(
                                        "text-xs font-mono text-blue-300"
                                    )

                                with ui.row().classes("items-center gap-2"):
                                    ui.label("Analog:").classes("text-xs text-gray-400")
                                    self.mock_meta_ana_val = ui.label("9124").classes(
                                        "text-xs font-mono text-amber-300"
                                    )

                # =========================================================================
                # TAB 3: Interactive Swagger UI (OpenAPI)
                # =========================================================================
                with (
                    ui.tab_panel(tab_swagger).classes(
                        "w-full h-full flex flex-col p-0 gap-3 overflow-hidden"
                    ),
                    ui.card().classes(
                        "w-full flex-1 min-h-0 flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3 overflow-hidden"
                    ),
                ):
                    # Toolbar
                    with ui.row().classes(
                        "w-full justify-between items-center px-1 pb-2 border-b border-white/10 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            with ui.element("div").classes(
                                "w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center"
                            ):
                                ui.icon("api", color="emerald").classes("text-lg")
                            with ui.column().classes("gap-0"):
                                ui.label("Interactive OpenAPI Documentation").classes(
                                    "font-bold text-sm text-white leading-tight"
                                )
                                ui.label(
                                    "Explore, test, and execute REST endpoints directly via interactive Swagger UI and ReDoc"
                                ).classes("text-xs text-gray-400 leading-tight")

                        with ui.row().classes("items-center gap-2"):
                            ui.button(
                                "Open /docs in New Tab",
                                icon="open_in_new",
                                on_click=lambda: ui.navigate.to("/docs", new_tab=True),
                            ).props("flat dense color=primary").classes(
                                "text-xs font-semibold"
                            )

                            ui.button(
                                "Open ReDoc",
                                icon="menu_book",
                                on_click=lambda: ui.navigate.to("/redoc", new_tab=True),
                            ).props("flat dense color=teal").classes(
                                "text-xs font-semibold"
                            )

                            ui.button(
                                "OpenAPI Spec (JSON)",
                                icon="download",
                                on_click=lambda: ui.navigate.to(
                                    "/openapi.json", new_tab=True
                                ),
                            ).props("flat dense color=cyan").classes(
                                "text-xs font-semibold"
                            )

                    # Embedded Swagger UI Frame
                    with ui.element("div").classes(
                        "w-full flex-1 min-h-0 bg-slate-950 rounded-xl border border-white/5 overflow-hidden relative"
                    ):
                        ui.element("iframe").props(
                            'src="/docs" title="Swagger UI Documentation"'
                        ).classes("w-full h-full border-0 rounded-xl").style(
                            "width: 100%; height: 100%; min-height: 550px; background-color: #0f172a;"
                        )

        # Stream timer (1 second interval when active)
        self.mock_stream_timer = ui.timer(
            1.0, callback=self._generate_mock_frame, active=False
        )

        # Trigger initial generation in mock studio
        init_task = asyncio.create_task(self._generate_mock_frame())
        self._background_tasks.add(init_task)
        init_task.add_done_callback(self._background_tasks.discard)
