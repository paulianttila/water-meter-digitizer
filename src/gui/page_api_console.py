"""Interactive REST API Console & Mock Camera Studio Page for NiceGUI."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import logging
import time
import urllib.parse
from typing import TYPE_CHECKING, Any

import PIL.Image
import requests
from nicegui import ui

from api.routes_mock_camera import render_mock_camera_frame
from configuration import Config
from gui.api_console.mock_config_dialog import MockConfigDialog
from gui.api_console.registry import (
    ENDPOINTS,
    SCENARIO_PRESETS,
    STANDARD_RESOLUTIONS,
    generate_curl_command,
)
from gui.base_page import BasePage
from gui.components import render_page_header
from gui.components.engine_test_dialog import run_engine_test_dialog
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
    CARD_PANEL,
    ROW_ACTIONS,
    ROW_HEADER,
)
from processor.image import ImageProcessor
from simulator.meter_generator import MeterImageGenerator

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)


class ApiConsolePage(BasePage):
    """Page allowing users to interactively test REST endpoints and studio mock camera feeds."""

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
        self.mock_meter_bg = "white"
        self.mock_needle_color = "red"
        self.mock_width = 640
        self.mock_height = 480
        self.mock_res_preset = "640x480"
        self.mock_digit_overrides: list[str] = ["", "", "", "", ""]
        self.mock_analog_overrides: list[str] = ["", "", "", ""]
        self.mock_test_config_mode: str = "dedicated"  # "dedicated" or "active"
        self.mock_auto_refresh = True
        self.mock_streaming = False
        self.mock_stream_timer: ui.timer | None = None
        self._raw_mock_bytes: bytes = b""
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
        self.mock_meter_bg_select: ui.select | None = None
        self.mock_needle_color_select: ui.select | None = None
        self.mock_test_config_select: ui.select | None = None
        self.mock_custom_config: Config | None = None
        self.mock_custom_config_active: bool = False
        self.mock_custom_config_badge: ui.badge | None = None
        self.mock_show_rois: bool = False
        self.mock_show_rois_switch: ui.switch | None = None
        self.mock_res_select: ui.select | None = None
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
            self._raw_mock_bytes = jpeg_bytes
            b64 = base64.b64encode(jpeg_bytes).decode("ascii")
            self.mock_img_src = f"data:image/jpeg;base64,{b64}"
        except Exception:
            logger.warning("Failed to render initial mock frame", exc_info=True)
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
        if self.last_response_text:
            ui.run_javascript(
                f"navigator.clipboard.writeText({self.last_response_text!r});"
            )
            ui.notify("Response copied to clipboard!", type="positive")

    def _copy_curl(self) -> None:
        if self.last_curl_cmd:
            ui.run_javascript(f"navigator.clipboard.writeText({self.last_curl_cmd!r});")
            ui.notify("cURL command copied to clipboard!", type="positive")

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
        if self.mock_meter_bg != "white":
            params["meter_bg"] = self.mock_meter_bg
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
                    meter_bg=self.mock_meter_bg,
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
                self._raw_mock_bytes = jpeg_bytes
                if self.mock_show_rois:
                    try:
                        active_cfg = (
                            self.mock_custom_config
                            if (
                                self.mock_custom_config_active
                                and self.mock_custom_config
                            )
                            else MeterImageGenerator.create_mock_meter_config(
                                width=self.mock_width,
                                height=self.mock_height,
                                base_config=(
                                    self.callbacks.get_config()
                                    if self.callbacks
                                    else None
                                ),
                                url=self.get_mock_url(relative=False),
                            )
                        )
                        pil_frame = PIL.Image.open(io.BytesIO(jpeg_bytes)).convert(
                            "RGB"
                        )
                        overlaid = (
                            ImageProcessor()
                            .set_image(pil_frame)
                            .draw_meter_rois(active_cfg)
                            .get_image()
                        )
                        buf = io.BytesIO()
                        overlaid.save(buf, format="JPEG", quality=85)
                        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    except Exception:
                        logger.debug(
                            "Failed to draw meter ROIs on mock frame", exc_info=True
                        )
                        b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                else:
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
                self.mock_glare = qs["glare"][0].lower() in (
                    "true",
                    "1",
                    "yes",
                )
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
            if qs.get("meter_bg"):
                self.mock_meter_bg = qs["meter_bg"][0]
                if self.mock_meter_bg_select:
                    self.mock_meter_bg_select.value = self.mock_meter_bg
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
            res_key = f"{self.mock_width}x{self.mock_height}"
            self.mock_res_preset = (
                res_key if res_key in STANDARD_RESOLUTIONS else "custom"
            )
            if self.mock_res_select:
                self.mock_res_select.value = self.mock_res_preset
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

    async def _apply_scenario_preset(self, preset: dict[str, Any]) -> None:
        """Apply a pre-configured scenario preset to all mock camera controls."""
        cfg = preset["config"]
        self.mock_mode = cfg.get("mode", "fixed")
        self.mock_value = cfg.get("value", "00452.91241")
        self.mock_rate = cfg.get("rate", 0.005)
        self.mock_rotate = cfg.get("rotate", 0.0)
        self.mock_glare = cfg.get("glare", False)
        self.mock_glare_pos = cfg.get("glare_pos", "320,240")
        self.mock_glare_intensity = cfg.get("glare_intensity", 1.0)
        self.mock_noise = cfg.get("noise", 0.0)
        self.mock_blur = cfg.get("blur", 0.0)
        self.mock_brightness = cfg.get("brightness", 1.0)
        self.mock_contrast = cfg.get("contrast", 1.0)
        self.mock_lcd_color = cfg.get("lcd_color", "black")
        self.mock_lcd_bg = cfg.get("lcd_bg", "grey")
        self.mock_meter_bg = cfg.get("meter_bg", "white")
        self.mock_needle_color = cfg.get("needle_color", "red")
        self.mock_width = cfg.get("width", 640)
        self.mock_height = cfg.get("height", 480)
        self.mock_digit_overrides = list(
            cfg.get("digit_overrides", ["", "", "", "", ""])
        )
        self.mock_analog_overrides = list(cfg.get("analog_overrides", ["", "", "", ""]))

        # Update UI controls
        if self.mock_mode_select:
            self.mock_mode_select.value = self.mock_mode
        if self.mock_value_input:
            self.mock_value_input.value = self.mock_value
        if self.mock_rate_input:
            self.mock_rate_input.value = self.mock_rate
        if self.mock_rot_slider:
            self.mock_rot_slider.value = self.mock_rotate
        if self.mock_rot_badge:
            self.mock_rot_badge.text = f"{self.mock_rotate:.0f}°"
        if self.mock_glare_switch:
            self.mock_glare_switch.value = self.mock_glare
        if self.mock_noise_slider:
            self.mock_noise_slider.value = self.mock_noise
        if self.mock_blur_slider:
            self.mock_blur_slider.value = self.mock_blur
        if self.mock_bright_slider:
            self.mock_bright_slider.value = self.mock_brightness
        if self.mock_contrast_slider:
            self.mock_contrast_slider.value = self.mock_contrast
        if self.mock_lcd_color_select:
            self.mock_lcd_color_select.value = self.mock_lcd_color
        if self.mock_lcd_bg_select:
            self.mock_lcd_bg_select.value = self.mock_lcd_bg
        if self.mock_meter_bg_select:
            self.mock_meter_bg_select.value = self.mock_meter_bg
        if self.mock_needle_color_select:
            self.mock_needle_color_select.value = self.mock_needle_color
        for i, val in enumerate(self.mock_digit_overrides):
            if i < len(self.mock_digit_inputs) and self.mock_digit_inputs[i]:
                self.mock_digit_inputs[i].value = val
        for i, val in enumerate(self.mock_analog_overrides):
            if i < len(self.mock_analog_inputs) and self.mock_analog_inputs[i]:
                self.mock_analog_inputs[i].value = val

        await self._generate_mock_frame()
        ui.notify(f"Applied scenario: {preset['name']}", type="positive")

    def _open_mock_config_dialog(self) -> None:
        """Open the modal dialog to view and customize dedicated mock camera configuration."""
        try:
            mock_url = self.get_mock_url(relative=False)

            if self.mock_custom_config_active and self.mock_custom_config:
                cfg_to_edit = self.mock_custom_config
                is_custom = True
            elif self.mock_test_config_mode == "active" and self.callbacks:
                cfg_to_edit = self.callbacks.get_config()
                is_custom = False
            else:
                base_cfg = self.callbacks.get_config() if self.callbacks else None
                cfg_to_edit = MeterImageGenerator.create_mock_meter_config(
                    width=self.mock_width,
                    height=self.mock_height,
                    base_config=base_cfg,
                    url=mock_url,
                )
                is_custom = False

            def on_applied(cfg: Config, is_custom_flag: bool = True) -> None:
                self.mock_custom_config = cfg if is_custom_flag else None
                self.mock_custom_config_active = is_custom_flag
                if self.mock_custom_config_badge:
                    self.mock_custom_config_badge.set_visibility(is_custom_flag)
                if self.mock_test_config_select:
                    self.mock_test_config_select.value = "dedicated"
                    self.mock_test_config_mode = "dedicated"

            dialog = MockConfigDialog(
                current_config=cfg_to_edit,
                width=self.mock_width,
                height=self.mock_height,
                mock_url=mock_url,
                callbacks=self.callbacks,
                on_apply=on_applied,
                is_custom=is_custom,
            )
            dialog.open()
        except Exception as ex:
            logger.exception("Failed to open MockConfigDialog: %s", ex)
            ui.notify(f"Could not open config dialog: {ex}", type="negative")

    async def _test_in_digitizer_engine(self) -> None:
        """Run digitizer engine against the generated mock camera image."""
        if not self.callbacks:
            ui.notify(
                "Callbacks unavailable in standalone testing mode",
                type="warning",
            )
            return

        mock_url = self.get_mock_url(relative=False)
        test_config = None
        if self.mock_test_config_mode == "dedicated":
            if self.mock_custom_config_active and self.mock_custom_config:
                test_config = self.mock_custom_config
                title_tag = "🤖 Dedicated (Customized)"
            else:
                base_cfg = self.callbacks.get_config()
                test_config = MeterImageGenerator.create_mock_meter_config(
                    width=self.mock_width,
                    height=self.mock_height,
                    base_config=base_cfg,
                    url=mock_url,
                )
                title_tag = "🤖 Dedicated Mock Config"
        else:
            test_config = self.callbacks.get_config()
            title_tag = "⚙️ Active config.ini"

        await run_engine_test_dialog(
            config=test_config,
            callbacks=self.callbacks,
            image_bytes=self._raw_mock_bytes,
            url=mock_url,
            title_tag=title_tag,
            parent_spinner=self.mock_spinner,
        )

    async def _toggle_mock_show_rois(self, e: Any) -> None:
        """Toggle visual ROI overlay on mock preview canvas."""
        self.mock_show_rois = bool(e.value)
        await self._generate_mock_frame()

    def _download_mock_image(self) -> None:
        """Download current generated mock image frame."""
        if self._raw_mock_bytes:
            ui.download(self._raw_mock_bytes, filename="mock_meter_frame.jpg")
            ui.notify("Downloading mock_meter_frame.jpg", type="info")

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
        self.mock_streaming = bool(getattr(e, "value", e))
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
        self.mock_meter_bg = "white"
        self.mock_needle_color = "red"
        self.mock_width = 640
        self.mock_height = 480
        self.mock_res_preset = "640x480"
        self.mock_digit_overrides = ["", "", "", "", ""]
        self.mock_analog_overrides = ["", "", "", ""]
        self.mock_auto_refresh = True

        if self.mock_mode_select:
            self.mock_mode_select.value = "fixed"
        if self.mock_value_input:
            self.mock_value_input.value = "00452.91241"
        if self.mock_rate_input:
            self.mock_rate_input.value = 0.005
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
        if self.mock_meter_bg_select:
            self.mock_meter_bg_select.value = "white"
        if self.mock_needle_color_select:
            self.mock_needle_color_select.value = "red"
        if self.mock_res_select:
            self.mock_res_select.value = "640x480"
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

        await self._generate_mock_frame()
        ui.notify("Mock camera parameters reset to default values", type="positive")

    async def _reset_mock_ticker(self) -> None:
        """Reset the server-side mock camera ticker start value."""
        base = self._get_base_url()
        url = f"{base}/api/mock_camera/reset?start_value=100.0"
        try:
            resp = await asyncio.to_thread(requests.post, url, timeout=5.0)
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
        ui.run_javascript(f"navigator.clipboard.writeText({url!r});")
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

    async def show(self) -> None:
        with ui.column().classes(
            "w-full h-full flex flex-col gap-3 p-4 overflow-hidden"
        ):
            render_page_header(
                title="REST API Console & Studio",
                subtitle="Interactive endpoint debugger, REST tester & procedural mock camera studio",
                icon="terminal",
                color="cyan",
                classes="w-full justify-between items-center shrink-0 mb-1",
            )

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
                        "w-full flex-1 min-h-0 flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3 overflow-hidden"
                    ),
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
                                on_change=lambda e: setattr(
                                    self, "selected_method", e.value
                                ),
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
                            with ui.element("span").classes(
                                BADGE_INFO
                            ) as self.status_badge:
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
                        ) as resp_subtabs,
                        ui.row().classes("w-full gap-1"),
                    ):
                        self.resp_tab_body = ui.tab(
                            "Response Body", icon="data_object"
                        ).classes("text-xs")
                        self.resp_tab_headers = ui.tab(
                            "Response Headers", icon="view_list"
                        ).classes("text-xs")
                        self.resp_tab_curl = ui.tab(
                            "cURL Command", icon="terminal"
                        ).classes("text-xs")
                        self.resp_tab_history = ui.tab(
                            "Request History", icon="history"
                        ).classes("text-xs")

                    # Response Sub-Panels
                    with ui.tab_panels(resp_subtabs, value=self.resp_tab_body).classes(
                        "w-full flex-1 min-h-0 bg-transparent p-0 overflow-hidden"
                    ):
                        # Panel 1: Body
                        with (
                            ui.tab_panel(self.resp_tab_body).classes(
                                "w-full h-full p-0 overflow-y-auto"
                            ),
                            ui.element("div").classes(
                                f"{CARD_PANEL} h-full overflow-y-auto"
                            ),
                        ):
                            self.viewer_container = ui.column().classes(
                                "w-full p-0 gap-0"
                            )
                            with self.viewer_container:
                                self.response_viewer = ui.code(
                                    "// Select an endpoint above and click Execute to test API responses.",
                                    language="json",
                                ).classes("w-full text-xs font-mono text-emerald-400")

                        # Panel 2: Headers
                        with (
                            ui.tab_panel(self.resp_tab_headers).classes(
                                "w-full h-full p-0 overflow-y-auto"
                            ),
                            ui.element("div").classes(
                                f"{CARD_PANEL} h-full overflow-y-auto"
                            ),
                        ):
                            self.headers_container = ui.column().classes("w-full gap-1")
                            with self.headers_container:
                                ui.label(
                                    "No headers available yet. Click Execute."
                                ).classes("text-xs text-slate-400 italic p-3")

                        # Panel 3: cURL
                        with (
                            ui.tab_panel(self.resp_tab_curl).classes(
                                "w-full h-full p-0 overflow-y-auto"
                            ),
                            ui.element("div").classes(
                                f"{CARD_PANEL} h-full overflow-y-auto"
                            ),
                        ):
                            self.curl_viewer = ui.code(
                                "curl -X GET 'http://localhost:3000/health'",
                                language="bash",
                            ).classes("w-full text-xs font-mono text-cyan-300")

                        # Panel 4: History
                        with (
                            ui.tab_panel(self.resp_tab_history).classes(
                                "w-full h-full p-0 overflow-y-auto"
                            ),
                            ui.element("div").classes(
                                f"{CARD_PANEL} h-full overflow-y-auto"
                            ),
                        ):
                            self.history_container = ui.column().classes("w-full gap-2")
                            with self.history_container:
                                ui.label("No request history recorded yet.").classes(
                                    "text-xs text-slate-400 italic p-3"
                                )

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
                        with ui.row().classes(f"{ROW_HEADER} gap-3"):
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
                            f"{ROW_HEADER} gap-3 pt-1 border-t border-white/5"
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

                            with ui.row().classes(f"{ROW_ACTIONS} flex-wrap"):
                                ui.button(
                                    "Download JPG",
                                    icon="download",
                                    on_click=self._download_mock_image,
                                ).props("flat dense size=sm color=grey-4").classes(
                                    "text-xs font-semibold"
                                )

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

                    # Scenario Presets Quick Strip
                    with ui.row().classes(
                        "w-full items-center gap-2 px-3 py-2 bg-slate-900/80 rounded-xl border border-white/10 shrink-0 overflow-x-auto"
                    ):
                        ui.label("Scenario Presets:").classes(
                            "text-xs font-bold text-cyan-400 shrink-0"
                        )
                        for preset in SCENARIO_PRESETS:

                            def make_preset_cb(p: dict[str, Any]):
                                return lambda: asyncio.create_task(
                                    self._apply_scenario_preset(p)
                                )

                            p_name = str(preset["name"])
                            p_icon = str(preset["icon"])
                            p_desc = str(preset["desc"])
                            ui.button(
                                p_name,
                                icon=p_icon,
                                on_click=make_preset_cb(preset),
                            ).props("outline dense size=xs color=cyan").classes(
                                "text-[11px] font-semibold"
                            ).tooltip(
                                p_desc
                            )

                    # DEDICATED CARD: Digitizer Engine Testing & ROI Inspection
                    with ui.card().classes(
                        "w-full p-3 bg-slate-900 border border-white/10 rounded-2xl shrink-0 flex flex-row items-center justify-between gap-3 flex-wrap"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            with ui.element("div").classes(
                                "w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0"
                            ):
                                ui.icon("analytics", color="cyan").classes("text-lg")
                            with ui.column().classes("gap-0"):
                                ui.label("Digitizer Engine & ROI Inspection").classes(
                                    "font-bold text-xs text-white leading-tight"
                                )
                                ui.label(
                                    "Overlay ROIs, tune dedicated configuration, and test CNN recognition on mock frames"
                                ).classes("text-[10px] text-gray-400 leading-tight")

                        with ui.row().classes("items-center gap-3 flex-wrap"):
                            self.mock_show_rois_switch = (
                                ui.switch(
                                    "Overlay ROIs",
                                    value=self.mock_show_rois,
                                    on_change=self._toggle_mock_show_rois,
                                )
                                .props("dense size=sm color=amber")
                                .classes("text-xs font-semibold text-amber-300")
                                .tooltip(
                                    "Draw Digital (blue) and Analog (orange) ROI bounding boxes on the preview canvas"
                                )
                            )

                            async def _on_test_cfg_change(e: Any) -> None:
                                self.mock_test_config_mode = e.value

                            self.mock_test_config_select = (
                                ui.select(
                                    options={
                                        "dedicated": "Dedicated Mock Config",
                                        "active": "Active config.ini",
                                    },
                                    value=self.mock_test_config_mode,
                                    on_change=_on_test_cfg_change,
                                    label="Engine Config",
                                )
                                .props("outlined dense options-dense")
                                .classes("text-xs min-w-[190px]")
                                .tooltip(
                                    "Choose whether to test against an auto-generated config matching the mock meter geometry or current active config.ini"
                                )
                            )

                            ui.button(
                                "Tune Config",
                                icon="tune",
                                on_click=self._open_mock_config_dialog,
                            ).props("outline dense size=sm color=cyan-4").classes(
                                "text-xs font-semibold text-cyan-200"
                            ).tooltip(
                                "View and customize the dedicated mock camera configuration (CNN models, formulas, filters, ROIs)"
                            )

                            self.mock_custom_config_badge = ui.badge(
                                "Customized", color="teal"
                            ).classes("text-[10px] font-bold tracking-wide")
                            self.mock_custom_config_badge.set_visibility(
                                self.mock_custom_config_active
                            )

                            ui.button(
                                "Test in Engine",
                                icon="speed",
                                on_click=self._test_in_digitizer_engine,
                            ).props("unelevated dense size=sm color=cyan-8").classes(
                                "text-xs font-semibold text-white px-3"
                            ).tooltip(
                                "Run digitizer engine recognition cycle on this mock frame using selected config"
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
                                        .props("outlined dense debounce=300")
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
                                        .props("outlined dense debounce=500")
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
                                    .props("color=cyan dense debounce=500")
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
                                            label="Glare Pos (X,Y)",
                                            value=self.mock_glare_pos,
                                            on_change=_on_gpos_change,
                                        )
                                        .props("outlined dense debounce=300")
                                        .classes("w-32 font-mono text-xs")
                                    )

                                # Noise & Blur
                                with ui.grid(columns=2).classes("w-full gap-3"):
                                    with ui.column().classes("gap-1"):
                                        ui.label("Sensor Noise (%)").classes(
                                            "text-xs text-gray-400"
                                        )

                                        async def _on_noise_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_noise = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_noise_slider = (
                                            ui.slider(
                                                min=0.0,
                                                max=30.0,
                                                step=0.5,
                                                value=self.mock_noise,
                                                on_change=_on_noise_change,
                                            )
                                            .props("color=teal dense debounce=500")
                                            .classes("w-full")
                                        )

                                    with ui.column().classes("gap-1"):
                                        ui.label("Lens Blur (px)").classes(
                                            "text-xs text-gray-400"
                                        )

                                        async def _on_blur_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_blur = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_blur_slider = (
                                            ui.slider(
                                                min=0.0,
                                                max=5.0,
                                                step=0.1,
                                                value=self.mock_blur,
                                                on_change=_on_blur_change,
                                            )
                                            .props("color=teal dense debounce=500")
                                            .classes("w-full")
                                        )

                                # Brightness & Contrast
                                with ui.grid(columns=2).classes("w-full gap-3"):
                                    with ui.column().classes("gap-1"):
                                        ui.label("Brightness").classes(
                                            "text-xs text-gray-400"
                                        )

                                        async def _on_bright_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_brightness = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_bright_slider = (
                                            ui.slider(
                                                min=0.2,
                                                max=2.0,
                                                step=0.05,
                                                value=self.mock_brightness,
                                                on_change=_on_bright_change,
                                            )
                                            .props("color=amber dense debounce=500")
                                            .classes("w-full")
                                        )

                                    with ui.column().classes("gap-1"):
                                        ui.label("Contrast").classes(
                                            "text-xs text-gray-400"
                                        )

                                        async def _on_contrast_change(
                                            e: Any,
                                        ) -> None:
                                            self.mock_contrast = float(e.value)
                                            await self._on_mock_param_change()

                                        self.mock_contrast_slider = (
                                            ui.slider(
                                                min=0.2,
                                                max=2.0,
                                                step=0.05,
                                                value=self.mock_contrast,
                                                on_change=_on_contrast_change,
                                            )
                                            .props("color=amber dense debounce=500")
                                            .classes("w-full")
                                        )

                            # --- Section 3: Colors & Resolution ---
                            with (
                                ui.expansion(
                                    "Colors & Resolution",
                                    icon="palette",
                                    value=False,
                                ).classes(
                                    "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
                                ),
                                ui.column().classes("w-full gap-3 p-1"),
                            ):
                                with ui.grid(columns=4).classes("w-full gap-2"):

                                    async def _on_lcd_c(e: Any) -> None:
                                        self.mock_lcd_color = e.value
                                        await self._on_mock_param_change()

                                    self.mock_lcd_color_select = (
                                        ui.select(
                                            options=[
                                                "black",
                                                "white",
                                                "red",
                                                "blue",
                                                "green",
                                            ],
                                            value=self.mock_lcd_color,
                                            on_change=_on_lcd_c,
                                            label="Digit Color",
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
                                                "black",
                                                "white",
                                                "silver",
                                            ],
                                            value=self.mock_lcd_bg,
                                            on_change=_on_lcd_bg,
                                            label="Digit BG",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_meter_bg(e: Any) -> None:
                                        self.mock_meter_bg = e.value
                                        await self._on_mock_param_change()

                                    self.mock_meter_bg_select = (
                                        ui.select(
                                            options=[
                                                "white",
                                                "grey",
                                                "blue",
                                                "brass",
                                                "dark",
                                                "aged",
                                            ],
                                            value=self.mock_meter_bg,
                                            on_change=_on_meter_bg,
                                            label="Meter BG",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                    async def _on_needle_c(e: Any) -> None:
                                        self.mock_needle_color = e.value
                                        await self._on_mock_param_change()

                                    self.mock_needle_color_select = (
                                        ui.select(
                                            options=[
                                                "red",
                                                "black",
                                                "white",
                                                "blue",
                                            ],
                                            value=self.mock_needle_color,
                                            on_change=_on_needle_c,
                                            label="Needle Color",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("text-xs")
                                    )

                                # Resolution Presets
                                with ui.row().classes(
                                    "w-full items-center justify-between gap-2"
                                ):

                                    async def _on_res_preset(e: Any) -> None:
                                        self.mock_res_preset = e.value
                                        if e.value != "custom":
                                            w, h = map(int, e.value.split("x"))
                                            self.mock_width = w
                                            self.mock_height = h
                                            if self.mock_width_input:
                                                self.mock_width_input.value = w
                                            if self.mock_height_input:
                                                self.mock_height_input.value = h
                                        await self._on_mock_param_change()

                                    self.mock_res_select = (
                                        ui.select(
                                            options=STANDARD_RESOLUTIONS,
                                            value=self.mock_res_preset,
                                            on_change=_on_res_preset,
                                            label="Resolution Preset",
                                        )
                                        .props("outlined dense options-dense")
                                        .classes("flex-1 text-xs")
                                    )

                                    async def _on_w_change(e: Any) -> None:
                                        if e.value:
                                            self.mock_width = int(e.value)
                                            await self._on_mock_param_change()

                                    self.mock_width_input = (
                                        ui.number(
                                            label="Width",
                                            value=self.mock_width,
                                            min=320,
                                            max=3840,
                                            step=10,
                                            on_change=_on_w_change,
                                        )
                                        .props("outlined dense")
                                        .classes("w-20 text-xs")
                                    )

                                    async def _on_h_change(e: Any) -> None:
                                        if e.value:
                                            self.mock_height = int(e.value)
                                            await self._on_mock_param_change()

                                    self.mock_height_input = (
                                        ui.number(
                                            label="Height",
                                            value=self.mock_height,
                                            min=240,
                                            max=2160,
                                            step=10,
                                            on_change=_on_h_change,
                                        )
                                        .props("outlined dense")
                                        .classes("w-20 text-xs")
                                    )

                            # --- Section 4: Digit & Dial Overrides ---
                            with (
                                ui.expansion(
                                    "Individual Drum / Dial Overrides",
                                    icon="pin",
                                    value=False,
                                ).classes(
                                    "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
                                ),
                                ui.column().classes("w-full gap-2 p-1"),
                            ):
                                ui.label(
                                    "Digital Drums (D1-D5, e.g. 0-9 or 2.5):"
                                ).classes("text-xs text-cyan-400 font-semibold")
                                with ui.grid(columns=5).classes("w-full gap-1.5"):
                                    self.mock_digit_inputs.clear()
                                    for i in range(5):

                                        def _make_dig_cb(idx: int):
                                            async def _cb(e: Any) -> None:
                                                self.mock_digit_overrides[idx] = e.value
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
                                    "Analog Needles (A1-A4, e.g. 0.0-9.9):"
                                ).classes("text-xs text-amber-400 font-semibold pt-1")
                                with ui.grid(columns=4).classes("w-full gap-1.5"):
                                    self.mock_analog_inputs.clear()
                                    for i in range(4):

                                        def _make_ana_cb(idx: int):
                                            async def _cb(e: Any) -> None:
                                                self.mock_analog_overrides[idx] = (
                                                    e.value
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


__all__ = [
    "ENDPOINTS",
    "SCENARIO_PRESETS",
    "STANDARD_RESOLUTIONS",
    "ApiConsolePage",
    "generate_curl_command",
]
