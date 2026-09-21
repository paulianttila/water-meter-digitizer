"""Mock Camera Studio Panel for NiceGUI (Dedicated Simulator & Generator)."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

import PIL.Image
import requests
from nicegui import ui

from api.routes_mock_camera import render_mock_camera_frame
from configuration import Config
from gui.api_console.mock_config_dialog import MockConfigDialog
from gui.api_console.mock_streaming import MockStreamingController
from gui.api_console.registry import (
    SCENARIO_PRESETS,
    STANDARD_RESOLUTIONS,
)
from gui.components.base_component import BaseComponent
from gui.components.engine_test_dialog import run_engine_test_dialog
from gui.theme import (
    ROW_ACTIONS,
    ROW_HEADER,
)
from processor.image import ImageProcessor
from services.simulator.meter_generator import MeterImageGenerator

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)


class MockStudioPanel(BaseComponent):
    """Component for interactive procedural mock camera generation, live preview, and configuration tuning."""

    def __init__(self, callbacks: Callbacks | None = None, port: int = 3000) -> None:
        super().__init__(callbacks)
        self.port = port

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
        self._raw_mock_bytes: bytes = b""

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

        # Streaming Controller
        self.streaming_controller = MockStreamingController(
            frame_generator=self._generate_mock_frame, interval_seconds=1.0
        )

        # Generate initial frame synchronously
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

    @property
    def mock_streaming(self) -> bool:
        return self.streaming_controller.is_streaming

    @mock_streaming.setter
    def mock_streaming(self, val: bool) -> None:
        self.streaming_controller.is_streaming = val

    @property
    def mock_stream_timer(self) -> ui.timer | None:
        return self.streaming_controller.stream_timer

    @mock_stream_timer.setter
    def mock_stream_timer(self, val: ui.timer | None) -> None:
        self.streaming_controller.stream_timer = val

    @property
    def _background_tasks(self) -> set[asyncio.Task[None]]:
        return self.streaming_controller._background_tasks

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
        self.mock_show_rois = bool(getattr(e, "value", e))
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

    def _toggle_mock_streaming(self, e: Any = True) -> None:
        """Toggle live periodic ticker stream timer."""
        self.streaming_controller.toggle_streaming(bool(getattr(e, "value", e)))

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

    def render(self, container: ui.element | None = None) -> None:
        """Render the Mock Camera Studio tab content."""
        super().render(container)
        if container is not None:
            self.container = container
            with self.container:
                self._render_content()
        else:
            self._render_content()

    def _render_content(self) -> None:
        # TOP QUERY & ACTION BAR
        with ui.card().classes(
            "w-full p-3 bg-slate-900 border border-white/10 rounded-2xl shrink-0 gap-2"
        ):
            with ui.row().classes(f"{ROW_HEADER} gap-3"):
                with ui.row().classes("flex-1 items-center gap-2 min-w-0"):
                    ui.icon("travel_explore", color="cyan").classes("text-lg")
                    self.mock_url_display = (
                        ui.input(
                            value=self.get_mock_url(relative=True),
                            label="Mock Camera Query URL",
                        )
                        .props("outlined dense")
                        .classes("flex-1 font-mono text-xs bg-slate-950 text-cyan-300")
                    )
                    self.mock_url_display.on("keydown.enter", self._execute_mock_query)

                ui.button(
                    "Make Query / Update Snapshot",
                    icon="photo_camera",
                    on_click=self._execute_mock_query,
                ).props("unelevated color=primary").classes(
                    "px-4 font-bold text-xs shadow-md shadow-blue-500/20"
                )

            with ui.row().classes(f"{ROW_HEADER} gap-3 pt-1 border-t border-white/5"):
                with ui.row().classes("items-center gap-4"):
                    ui.switch(
                        "Auto-Update on Change",
                        value=self.mock_auto_refresh,
                        on_change=lambda e: setattr(self, "mock_auto_refresh", e.value),
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
                    ).props("unelevated dense size=sm color=emerald").classes(
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
                                    self.mock_rate_input.enabled = self.mock_mode in (
                                        "ticker",
                                        "flow",
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
                                    float(e.value) if e.value is not None else 0.005
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
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("Rotation Angle").classes("text-xs text-gray-300")
                            self.mock_rot_badge = ui.badge(
                                f"{self.mock_rotate:.0f}°", color="cyan"
                            )

                        async def _on_rot_change(e: Any) -> None:
                            self.mock_rotate = float(e.value)
                            if self.mock_rot_badge:
                                self.mock_rot_badge.text = f"{self.mock_rotate:.0f}°"
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
                                ui.label("Brightness").classes("text-xs text-gray-400")

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
                                ui.label("Contrast").classes("text-xs text-gray-400")

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
                        ui.label("Digital Drums (D1-D5, e.g. 0-9 or 2.5):").classes(
                            "text-xs text-cyan-400 font-semibold"
                        )
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

                        ui.label("Analog Needles (A1-A4, e.g. 0.0-9.9):").classes(
                            "text-xs text-amber-400 font-semibold pt-1"
                        )
                        with ui.grid(columns=4).classes("w-full gap-1.5"):
                            self.mock_analog_inputs.clear()
                            for i in range(4):

                                def _make_ana_cb(idx: int):
                                    async def _cb(e: Any) -> None:
                                        self.mock_analog_overrides[idx] = e.value
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
                            ).classes("text-xs font-mono font-bold text-cyan-300")

                        with ui.row().classes("items-center gap-2"):
                            ui.label("Digital:").classes("text-xs text-gray-400")
                            self.mock_meta_dig_val = ui.label("00452").classes(
                                "text-xs font-mono text-blue-300"
                            )

                        with ui.row().classes("items-center gap-2"):
                            ui.label("Analog:").classes("text-xs text-gray-400")
                            self.mock_meta_ana_val = ui.label("9124").classes(
                                "text-xs font-mono text-amber-300"
                            )

            # Trigger initial generation in background
            self.streaming_controller.spawn_task(self._generate_mock_frame())

    def dispose(self) -> None:
        """Dispose timers, tasks, and state."""
        super().dispose()
        self.streaming_controller.dispose()
