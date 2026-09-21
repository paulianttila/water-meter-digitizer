"""Interactive REST API Console & Mock Camera Studio Page for NiceGUI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from gui.api_console.mock_config_dialog import MockConfigDialog
from gui.api_console.mock_streaming import MockStreamingController
from gui.api_console.mock_studio_panel import MockStudioPanel
from gui.api_console.registry import (
    ENDPOINTS,
    SCENARIO_PRESETS,
    STANDARD_RESOLUTIONS,
    generate_curl_command,
)
from gui.api_console.rest_console_panel import RestConsolePanel
from gui.components import render_page_header
from gui.pages.base import BasePage

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)


class ApiConsolePage(BasePage):
    """Page allowing users to interactively test REST endpoints and studio mock camera feeds."""

    def __init__(self, callbacks: Callbacks | None = None, port: int = 3000) -> None:
        self.port = port
        self.rest_panel = RestConsolePanel(callbacks=callbacks, port=port)
        self.mock_panel = MockStudioPanel(callbacks=callbacks, port=port)
        super().__init__(callbacks)

    # -------------------------------------------------------------------------
    # REST Console Delegated Properties
    # -------------------------------------------------------------------------
    @property
    def selected_endpoint(self) -> str:
        return self.rest_panel.selected_endpoint

    @selected_endpoint.setter
    def selected_endpoint(self, value: str) -> None:
        self.rest_panel.selected_endpoint = value

    @property
    def selected_method(self) -> str:
        return self.rest_panel.selected_method

    @selected_method.setter
    def selected_method(self, value: str) -> None:
        self.rest_panel.selected_method = value

    @property
    def status_badge(self) -> ui.element | None:
        return self.rest_panel.status_badge

    @status_badge.setter
    def status_badge(self, value: ui.element | None) -> None:
        self.rest_panel.status_badge = value

    @property
    def status_label(self) -> ui.label | None:
        return self.rest_panel.status_label

    @status_label.setter
    def status_label(self, value: ui.label | None) -> None:
        self.rest_panel.status_label = value

    @property
    def latency_label(self) -> ui.label | None:
        return self.rest_panel.latency_label

    @latency_label.setter
    def latency_label(self, value: ui.label | None) -> None:
        self.rest_panel.latency_label = value

    @property
    def size_label(self) -> ui.label | None:
        return self.rest_panel.size_label

    @size_label.setter
    def size_label(self, value: ui.label | None) -> None:
        self.rest_panel.size_label = value

    @property
    def viewer_container(self) -> ui.column | None:
        return self.rest_panel.viewer_container

    @viewer_container.setter
    def viewer_container(self, value: ui.column | None) -> None:
        self.rest_panel.viewer_container = value

    @property
    def response_viewer(self) -> ui.code | None:
        return self.rest_panel.response_viewer

    @response_viewer.setter
    def response_viewer(self, value: ui.code | None) -> None:
        self.rest_panel.response_viewer = value

    @property
    def last_response_text(self) -> str:
        return self.rest_panel.last_response_text

    @last_response_text.setter
    def last_response_text(self, value: str) -> None:
        self.rest_panel.last_response_text = value

    @property
    def last_response_headers(self) -> dict[str, str]:
        return self.rest_panel.last_response_headers

    @last_response_headers.setter
    def last_response_headers(self, value: dict[str, str]) -> None:
        self.rest_panel.last_response_headers = value

    @property
    def last_curl_cmd(self) -> str:
        return self.rest_panel.last_curl_cmd

    @last_curl_cmd.setter
    def last_curl_cmd(self, value: str) -> None:
        self.rest_panel.last_curl_cmd = value

    @property
    def request_history(self) -> list[dict[str, Any]]:
        return self.rest_panel.request_history

    @request_history.setter
    def request_history(self, value: list[dict[str, Any]]) -> None:
        self.rest_panel.request_history = value

    @property
    def url_input(self) -> ui.input | None:
        return self.rest_panel.url_input

    @url_input.setter
    def url_input(self, value: ui.input | None) -> None:
        self.rest_panel.url_input = value

    @property
    def method_select(self) -> ui.select | None:
        return self.rest_panel.method_select

    @method_select.setter
    def method_select(self, value: ui.select | None) -> None:
        self.rest_panel.method_select = value

    @property
    def body_input(self) -> ui.textarea | None:
        return self.rest_panel.body_input

    @body_input.setter
    def body_input(self, value: ui.textarea | None) -> None:
        self.rest_panel.body_input = value

    @property
    def spinner(self) -> ui.spinner | None:
        return self.rest_panel.spinner

    @spinner.setter
    def spinner(self, value: ui.spinner | None) -> None:
        self.rest_panel.spinner = value

    @property
    def resp_tabs(self) -> ui.tabs | None:
        return self.rest_panel.resp_tabs

    @resp_tabs.setter
    def resp_tabs(self, value: ui.tabs | None) -> None:
        self.rest_panel.resp_tabs = value

    @property
    def resp_tab_body(self) -> ui.tab | None:
        return self.rest_panel.resp_tab_body

    @resp_tab_body.setter
    def resp_tab_body(self, value: ui.tab | None) -> None:
        self.rest_panel.resp_tab_body = value

    @property
    def resp_tab_headers(self) -> ui.tab | None:
        return self.rest_panel.resp_tab_headers

    @resp_tab_headers.setter
    def resp_tab_headers(self, value: ui.tab | None) -> None:
        self.rest_panel.resp_tab_headers = value

    @property
    def resp_tab_curl(self) -> ui.tab | None:
        return self.rest_panel.resp_tab_curl

    @resp_tab_curl.setter
    def resp_tab_curl(self, value: ui.tab | None) -> None:
        self.rest_panel.resp_tab_curl = value

    @property
    def resp_tab_history(self) -> ui.tab | None:
        return self.rest_panel.resp_tab_history

    @resp_tab_history.setter
    def resp_tab_history(self, value: ui.tab | None) -> None:
        self.rest_panel.resp_tab_history = value

    @property
    def headers_container(self) -> ui.column | None:
        return self.rest_panel.headers_container

    @headers_container.setter
    def headers_container(self, value: ui.column | None) -> None:
        self.rest_panel.headers_container = value

    @property
    def curl_viewer(self) -> ui.code | None:
        return self.rest_panel.curl_viewer

    @curl_viewer.setter
    def curl_viewer(self, value: ui.code | None) -> None:
        self.rest_panel.curl_viewer = value

    @property
    def history_container(self) -> ui.column | None:
        return self.rest_panel.history_container

    @history_container.setter
    def history_container(self, value: ui.column | None) -> None:
        self.rest_panel.history_container = value

    # -------------------------------------------------------------------------
    # REST Console Delegated Methods
    # -------------------------------------------------------------------------
    def _on_endpoint_change(self, e: Any) -> None:
        self.rest_panel._on_endpoint_change(e)

    async def _execute_request(self) -> None:
        await self.rest_panel._execute_request()

    def _copy_curl(self) -> None:
        self.rest_panel._copy_curl()

    def _copy_response(self) -> None:
        self.rest_panel._copy_response()

    # -------------------------------------------------------------------------
    # Mock Camera Studio Delegated Properties
    # -------------------------------------------------------------------------
    @property
    def mock_mode(self) -> str:
        return self.mock_panel.mock_mode

    @mock_mode.setter
    def mock_mode(self, value: str) -> None:
        self.mock_panel.mock_mode = value

    @property
    def mock_value(self) -> str:
        return self.mock_panel.mock_value

    @mock_value.setter
    def mock_value(self, value: str) -> None:
        self.mock_panel.mock_value = value

    @property
    def mock_rate(self) -> float:
        return self.mock_panel.mock_rate

    @mock_rate.setter
    def mock_rate(self, value: float) -> None:
        self.mock_panel.mock_rate = value

    @property
    def mock_rotate(self) -> float:
        return self.mock_panel.mock_rotate

    @mock_rotate.setter
    def mock_rotate(self, value: float) -> None:
        self.mock_panel.mock_rotate = value

    @property
    def mock_glare(self) -> bool:
        return self.mock_panel.mock_glare

    @mock_glare.setter
    def mock_glare(self, value: bool) -> None:
        self.mock_panel.mock_glare = value

    @property
    def mock_glare_pos(self) -> str:
        return self.mock_panel.mock_glare_pos

    @mock_glare_pos.setter
    def mock_glare_pos(self, value: str) -> None:
        self.mock_panel.mock_glare_pos = value

    @property
    def mock_glare_intensity(self) -> float:
        return self.mock_panel.mock_glare_intensity

    @mock_glare_intensity.setter
    def mock_glare_intensity(self, value: float) -> None:
        self.mock_panel.mock_glare_intensity = value

    @property
    def mock_noise(self) -> float:
        return self.mock_panel.mock_noise

    @mock_noise.setter
    def mock_noise(self, value: float) -> None:
        self.mock_panel.mock_noise = value

    @property
    def mock_blur(self) -> float:
        return self.mock_panel.mock_blur

    @mock_blur.setter
    def mock_blur(self, value: float) -> None:
        self.mock_panel.mock_blur = value

    @property
    def mock_brightness(self) -> float:
        return self.mock_panel.mock_brightness

    @mock_brightness.setter
    def mock_brightness(self, value: float) -> None:
        self.mock_panel.mock_brightness = value

    @property
    def mock_contrast(self) -> float:
        return self.mock_panel.mock_contrast

    @mock_contrast.setter
    def mock_contrast(self, value: float) -> None:
        self.mock_panel.mock_contrast = value

    @property
    def mock_lcd_color(self) -> str:
        return self.mock_panel.mock_lcd_color

    @mock_lcd_color.setter
    def mock_lcd_color(self, value: str) -> None:
        self.mock_panel.mock_lcd_color = value

    @property
    def mock_lcd_bg(self) -> str:
        return self.mock_panel.mock_lcd_bg

    @mock_lcd_bg.setter
    def mock_lcd_bg(self, value: str) -> None:
        self.mock_panel.mock_lcd_bg = value

    @property
    def mock_meter_bg(self) -> str:
        return self.mock_panel.mock_meter_bg

    @mock_meter_bg.setter
    def mock_meter_bg(self, value: str) -> None:
        self.mock_panel.mock_meter_bg = value

    @property
    def mock_needle_color(self) -> str:
        return self.mock_panel.mock_needle_color

    @mock_needle_color.setter
    def mock_needle_color(self, value: str) -> None:
        self.mock_panel.mock_needle_color = value

    @property
    def mock_width(self) -> int:
        return self.mock_panel.mock_width

    @mock_width.setter
    def mock_width(self, value: int) -> None:
        self.mock_panel.mock_width = value

    @property
    def mock_height(self) -> int:
        return self.mock_panel.mock_height

    @mock_height.setter
    def mock_height(self, value: int) -> None:
        self.mock_panel.mock_height = value

    @property
    def mock_res_preset(self) -> str:
        return self.mock_panel.mock_res_preset

    @mock_res_preset.setter
    def mock_res_preset(self, value: str) -> None:
        self.mock_panel.mock_res_preset = value

    @property
    def mock_digit_overrides(self) -> list[str]:
        return self.mock_panel.mock_digit_overrides

    @mock_digit_overrides.setter
    def mock_digit_overrides(self, value: list[str]) -> None:
        self.mock_panel.mock_digit_overrides = value

    @property
    def mock_analog_overrides(self) -> list[str]:
        return self.mock_panel.mock_analog_overrides

    @mock_analog_overrides.setter
    def mock_analog_overrides(self, value: list[str]) -> None:
        self.mock_panel.mock_analog_overrides = value

    @property
    def mock_show_rois(self) -> bool:
        return self.mock_panel.mock_show_rois

    @mock_show_rois.setter
    def mock_show_rois(self, value: bool) -> None:
        self.mock_panel.mock_show_rois = value

    @property
    def mock_test_config_mode(self) -> str:
        return self.mock_panel.mock_test_config_mode

    @mock_test_config_mode.setter
    def mock_test_config_mode(self, value: str) -> None:
        self.mock_panel.mock_test_config_mode = value

    @property
    def mock_custom_config(self) -> Any:
        return self.mock_panel.mock_custom_config

    @mock_custom_config.setter
    def mock_custom_config(self, value: Any) -> None:
        self.mock_panel.mock_custom_config = value

    @property
    def mock_custom_config_active(self) -> bool:
        return self.mock_panel.mock_custom_config_active

    @mock_custom_config_active.setter
    def mock_custom_config_active(self, value: bool) -> None:
        self.mock_panel.mock_custom_config_active = value

    @property
    def mock_streaming(self) -> bool:
        return self.mock_panel.mock_streaming

    @mock_streaming.setter
    def mock_streaming(self, value: bool) -> None:
        self.mock_panel.mock_streaming = value

    @property
    def mock_stream_timer(self) -> ui.timer | None:
        return self.mock_panel.mock_stream_timer

    @mock_stream_timer.setter
    def mock_stream_timer(self, value: ui.timer | None) -> None:
        self.mock_panel.mock_stream_timer = value

    @property
    def mock_img_src(self) -> str:
        return self.mock_panel.mock_img_src

    @mock_img_src.setter
    def mock_img_src(self, value: str) -> None:
        self.mock_panel.mock_img_src = value

    @property
    def mock_img_elem(self) -> Any:
        return self.mock_panel.mock_img_elem

    @mock_img_elem.setter
    def mock_img_elem(self, value: Any) -> None:
        self.mock_panel.mock_img_elem = value

    @property
    def mock_spinner(self) -> ui.spinner | None:
        return self.mock_panel.mock_spinner

    @mock_spinner.setter
    def mock_spinner(self, value: ui.spinner | None) -> None:
        self.mock_panel.mock_spinner = value

    @property
    def mock_url_display(self) -> ui.input | None:
        return self.mock_panel.mock_url_display

    @mock_url_display.setter
    def mock_url_display(self, value: ui.input | None) -> None:
        self.mock_panel.mock_url_display = value

    @property
    def mock_meta_meter_val(self) -> ui.label | None:
        return self.mock_panel.mock_meta_meter_val

    @mock_meta_meter_val.setter
    def mock_meta_meter_val(self, value: ui.label | None) -> None:
        self.mock_panel.mock_meta_meter_val = value

    @property
    def mock_meta_dig_val(self) -> ui.label | None:
        return self.mock_panel.mock_meta_dig_val

    @mock_meta_dig_val.setter
    def mock_meta_dig_val(self, value: ui.label | None) -> None:
        self.mock_panel.mock_meta_dig_val = value

    @property
    def mock_meta_ana_val(self) -> ui.label | None:
        return self.mock_panel.mock_meta_ana_val

    @mock_meta_ana_val.setter
    def mock_meta_ana_val(self, value: ui.label | None) -> None:
        self.mock_panel.mock_meta_ana_val = value

    @property
    def mock_meta_size_badge(self) -> ui.label | None:
        return self.mock_panel.mock_meta_size_badge

    @mock_meta_size_badge.setter
    def mock_meta_size_badge(self, value: ui.label | None) -> None:
        self.mock_panel.mock_meta_size_badge = value

    @property
    def _raw_mock_bytes(self) -> bytes:
        return self.mock_panel._raw_mock_bytes

    @_raw_mock_bytes.setter
    def _raw_mock_bytes(self, value: bytes) -> None:
        self.mock_panel._raw_mock_bytes = value

    @property
    def streaming_controller(self) -> MockStreamingController:
        return self.mock_panel.streaming_controller

    # -------------------------------------------------------------------------
    # Mock Camera Studio Delegated Methods
    # -------------------------------------------------------------------------
    def build_mock_query_string(self) -> str:
        return self.mock_panel.build_mock_query_string()

    def get_mock_url(self, relative: bool = False) -> str:
        return self.mock_panel.get_mock_url(relative=relative)

    def sync_state_from_url(self, url: str) -> None:
        self.mock_panel.sync_state_from_url(url)

    async def _generate_mock_frame(self) -> None:
        await self.mock_panel._generate_mock_frame()

    async def _execute_mock_query(self) -> None:
        await self.mock_panel._execute_mock_query()

    async def _reset_to_defaults(self) -> None:
        await self.mock_panel._reset_to_defaults()

    async def _reset_mock_ticker(self) -> None:
        await self.mock_panel._reset_mock_ticker()

    def _toggle_mock_streaming(self, e: Any = True) -> None:
        self.mock_panel._toggle_mock_streaming(e)

    async def _toggle_mock_show_rois(self, e: Any) -> None:
        await self.mock_panel._toggle_mock_show_rois(e)

    def _download_mock_image(self) -> None:
        self.mock_panel._download_mock_image()

    def _copy_mock_url(self) -> None:
        self.mock_panel._copy_mock_url()

    def _apply_as_active_image_source(self) -> None:
        self.mock_panel._apply_as_active_image_source()

    async def _apply_scenario_preset(self, preset: dict[str, Any]) -> None:
        await self.mock_panel._apply_scenario_preset(preset)

    async def _test_in_digitizer_engine(self) -> None:
        await self.mock_panel._test_in_digitizer_engine()

    def _open_mock_config_dialog(self) -> None:
        self.mock_panel._open_mock_config_dialog()

    # -------------------------------------------------------------------------
    # Lifecycle & Rendering
    # -------------------------------------------------------------------------
    def dispose(self) -> None:
        """Dispose child components and cleanup resources."""
        self.rest_panel.dispose()
        self.mock_panel.dispose()
        super().dispose()

    def _render_swagger_tab(self) -> None:
        """Render embedded Swagger UI and OpenAPI explorer."""
        with (
            ui.card().classes(
                "w-full h-full flex-1 min-h-[450px] flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3"
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
                    ).props("flat dense color=primary").classes("text-xs font-semibold")

                    ui.button(
                        "Open ReDoc",
                        icon="menu_book",
                        on_click=lambda: ui.navigate.to("/redoc", new_tab=True),
                    ).props("flat dense color=teal").classes("text-xs font-semibold")

                    ui.button(
                        "OpenAPI Spec (JSON)",
                        icon="download",
                        on_click=lambda: ui.navigate.to("/openapi.json", new_tab=True),
                    ).props("flat dense color=cyan").classes("text-xs font-semibold")

            # Embedded Swagger UI Frame
            with ui.element("div").classes(
                "w-full flex-1 min-h-[350px] bg-slate-950 rounded-xl border border-white/5 overflow-hidden relative"
            ):
                ui.element("iframe").props(
                    'src="/docs" title="Swagger UI Documentation"'
                ).classes("w-full h-full border-0 rounded-xl").style(
                    "width: 100%; height: 100%; min-height: 350px; border: 0; background-color: #0f172a;"
                )

    async def show(self) -> None:
        """Render the API Console page."""
        with ui.column().classes(
            "w-full h-full flex flex-col gap-3 p-4 overflow-hidden min-h-0 min-w-0 max-w-full"
        ):
            render_page_header(
                "REST API Console & Studio",
                "Interactive OpenAPI testing, real-time mock camera feed generator, and swagger explorer.",
                "api",
                classes="w-full justify-between items-center shrink-0 mb-1",
            )

            # Left-aligned navigation sub-tabs
            with (
                ui.tabs()
                .props("align=left no-caps")
                .classes(
                    "w-full bg-slate-900/90 border border-white/10 rounded-xl p-1 shrink-0 min-w-0"
                ) as tabs,
                ui.row().classes("w-full justify-start gap-2"),
            ):
                tab_rest = ui.tab("REST Endpoints", icon="terminal").classes(
                    "font-semibold text-sm"
                )
                tab_mock = ui.tab("Mock Camera Studio", icon="videocam").classes(
                    "font-semibold text-sm"
                )
                tab_swagger = ui.tab("Swagger UI", icon="auto_stories").classes(
                    "font-semibold text-sm"
                )

            with (
                ui.tab_panels(tabs, value=tab_rest)
                .classes(
                    "w-full flex-1 min-h-0 min-w-0 bg-transparent p-0 overflow-hidden flex flex-col"
                )
                .props('id="api-console-tab-panels"')
            ):
                with (
                    ui.tab_panel(tab_rest)
                    .classes(
                        "w-full h-full p-0 overflow-y-auto overflow-x-hidden min-w-0 max-w-full flex flex-col flex-nowrap min-h-0 gap-3"
                    )
                    .props('id="api-subtab-rest"')
                ):
                    self.rest_panel.render()

                with (
                    ui.tab_panel(tab_mock)
                    .classes(
                        "w-full h-full p-0 overflow-y-auto overflow-x-hidden min-w-0 max-w-full flex flex-col flex-nowrap min-h-0 gap-3"
                    )
                    .props('id="api-subtab-mock"')
                ):
                    self.mock_panel.render()

                with (
                    ui.tab_panel(tab_swagger)
                    .classes(
                        "w-full h-full p-0 overflow-y-auto overflow-x-hidden min-w-0 max-w-full flex flex-col flex-nowrap min-h-0"
                    )
                    .props('id="api-subtab-swagger"')
                ):
                    self._render_swagger_tab()


__all__ = [
    "ENDPOINTS",
    "SCENARIO_PRESETS",
    "STANDARD_RESOLUTIONS",
    "ApiConsolePage",
    "MockConfigDialog",
    "generate_curl_command",
]
