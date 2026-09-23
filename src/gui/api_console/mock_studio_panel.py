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
from gui.api_console.mock_studio_controls import render_mock_studio_controls
from gui.api_console.mock_studio_preview import (
    render_engine_inspection_card,
    render_mock_studio_preview,
    render_mock_studio_top_bar,
    render_scenario_presets_strip,
)
from gui.api_console.registry import (
    STANDARD_RESOLUTIONS,
)
from gui.components.base_component import BaseComponent
from gui.components.engine_test_dialog import run_engine_test_dialog
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
        render_mock_studio_top_bar(self)
        render_scenario_presets_strip(self)
        render_engine_inspection_card(self)

        # LOWER WORKSPACE: Two-Column Split (Parameters Left, Snapshot Right)
        with ui.element("div").classes(
            "w-full flex-1 min-h-0 grid grid-cols-2 gap-4 overflow-hidden"
        ):
            render_mock_studio_controls(self)
            render_mock_studio_preview(self)

        # Trigger initial generation in background
        self.streaming_controller.spawn_task(self._generate_mock_frame())

    def dispose(self) -> None:
        """Dispose timers, tasks, and state."""
        super().dispose()
        self.streaming_controller.dispose()
