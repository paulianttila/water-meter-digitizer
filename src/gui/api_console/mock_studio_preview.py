"""Mock Camera Studio preview & action bars component."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from nicegui import ui

from gui.api_console.registry import SCENARIO_PRESETS
from gui.theme import ROW_ACTIONS, ROW_HEADER

if TYPE_CHECKING:
    from gui.api_console.mock_studio_panel import MockStudioPanel


def render_mock_studio_top_bar(panel: MockStudioPanel) -> None:
    """Render top query & action bar."""
    with ui.card().classes(
        "w-full p-3 bg-slate-900 border border-white/10 rounded-2xl shrink-0 gap-2"
    ):
        with ui.row().classes(f"{ROW_HEADER} gap-3"):
            with ui.row().classes("flex-1 items-center gap-2 min-w-0"):
                ui.icon("travel_explore", color="cyan").classes("text-lg")
                panel.mock_url_display = (
                    ui.input(
                        value=panel.get_mock_url(relative=True),
                        label="Mock Camera Query URL",
                    )
                    .props("outlined dense")
                    .classes("flex-1 font-mono text-xs bg-slate-950 text-cyan-300")
                )
                panel.mock_url_display.on("keydown.enter", panel._execute_mock_query)

            ui.button(
                "Make Query / Update Snapshot",
                icon="photo_camera",
                on_click=panel._execute_mock_query,
            ).props("unelevated color=primary").classes(
                "px-4 font-bold text-xs shadow-md shadow-blue-500/20"
            )

        with ui.row().classes(f"{ROW_HEADER} gap-3 pt-1 border-t border-white/5"):
            with ui.row().classes("items-center gap-4"):
                ui.switch(
                    "Auto-Update on Change",
                    value=panel.mock_auto_refresh,
                    on_change=lambda e: setattr(panel, "mock_auto_refresh", e.value),
                ).props("dense size=sm color=cyan").classes(
                    "text-xs font-semibold text-gray-300"
                )

                ui.switch(
                    "Live Stream Ticker (1s)",
                    value=panel.mock_streaming,
                    on_change=panel._toggle_mock_streaming,
                ).props("dense size=sm color=emerald").classes(
                    "text-xs font-semibold text-gray-300"
                )

            with ui.row().classes(f"{ROW_ACTIONS} flex-wrap"):
                ui.button(
                    "Download JPG",
                    icon="download",
                    on_click=panel._download_mock_image,
                ).props("flat dense size=sm color=grey-4").classes(
                    "text-xs font-semibold"
                )

                ui.button(
                    "Reset Defaults",
                    icon="settings_backup_restore",
                    on_click=panel._reset_to_defaults,
                ).props("outline dense size=sm color=purple").classes(
                    "text-xs font-semibold"
                )

                ui.button(
                    "Reset Ticker",
                    icon="restart_alt",
                    on_click=panel._reset_mock_ticker,
                ).props("outline dense size=sm color=amber").classes(
                    "text-xs font-semibold"
                )

                ui.button(
                    "Copy Mock URL",
                    icon="content_copy",
                    on_click=panel._copy_mock_url,
                ).props("outline dense size=sm color=cyan").classes(
                    "text-xs font-semibold"
                )

                ui.button(
                    "Set as [ImageSource] URL",
                    icon="download_done",
                    on_click=panel._apply_as_active_image_source,
                ).props("unelevated dense size=sm color=emerald").classes(
                    "text-xs font-semibold"
                )


def render_scenario_presets_strip(panel: MockStudioPanel) -> None:
    """Render scenario presets quick strip."""
    with ui.row().classes(
        "w-full items-center gap-2 px-3 py-2 bg-slate-900/80 rounded-xl border border-white/10 shrink-0 overflow-x-auto"
    ):
        ui.label("Scenario Presets:").classes(
            "text-xs font-bold text-cyan-400 shrink-0"
        )
        for preset in SCENARIO_PRESETS:

            def make_preset_cb(p: dict[str, Any]):
                return lambda: asyncio.create_task(panel._apply_scenario_preset(p))

            p_name = str(preset["name"])
            p_icon = str(preset["icon"])
            p_desc = str(preset["desc"])
            ui.button(
                p_name,
                icon=p_icon,
                on_click=make_preset_cb(preset),
            ).props(
                "outline dense size=xs color=cyan"
            ).classes("text-[11px] font-semibold").tooltip(p_desc)


def render_engine_inspection_card(panel: MockStudioPanel) -> None:
    """Render Digitizer Engine Testing & ROI Inspection Card."""
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
            panel.mock_show_rois_switch = (
                ui.switch(
                    "Overlay ROIs",
                    value=panel.mock_show_rois,
                    on_change=panel._toggle_mock_show_rois,
                )
                .props("dense size=sm color=amber")
                .classes("text-xs font-semibold text-amber-300")
                .tooltip(
                    "Draw Digital (blue) and Analog (orange) ROI bounding boxes on the preview canvas"
                )
            )

            async def _on_test_cfg_change(e: Any) -> None:
                panel.mock_test_config_mode = e.value

            panel.mock_test_config_select = (
                ui.select(
                    options={
                        "dedicated": "Dedicated Mock Config",
                        "active": "Active config.ini",
                    },
                    value=panel.mock_test_config_mode,
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
                on_click=panel._open_mock_config_dialog,
            ).props("outline dense size=sm color=cyan-4").classes(
                "text-xs font-semibold text-cyan-200"
            ).tooltip(
                "View and customize the dedicated mock camera configuration (CNN models, formulas, filters, ROIs)"
            )

            panel.mock_custom_config_badge = ui.badge(
                "Customized", color="teal"
            ).classes("text-[10px] font-bold tracking-wide")
            panel.mock_custom_config_badge.set_visibility(
                panel.mock_custom_config_active
            )

            ui.button(
                "Test in Engine",
                icon="speed",
                on_click=panel._test_in_digitizer_engine,
            ).props("unelevated dense size=sm color=cyan-8").classes(
                "text-xs font-semibold text-white px-3"
            ).tooltip(
                "Run digitizer engine recognition cycle on this mock frame using selected config"
            )


def render_mock_studio_preview(panel: MockStudioPanel) -> None:
    """Render live generated camera picture & output studio (right column)."""
    with ui.card().classes(
        "w-full h-full flex flex-col p-4 bg-slate-900 border border-white/10 rounded-2xl gap-3 overflow-y-auto"
    ):
        with ui.row().classes(
            "w-full justify-between items-center shrink-0 border-b border-white/5 pb-2"
        ):
            with ui.row().classes("items-center gap-2"):
                panel.mock_spinner = ui.spinner("dots", size="sm", color="cyan")
                panel.mock_spinner.visible = False
                ui.label("Live Generated Camera Picture").classes(
                    "text-sm font-bold text-white"
                )

            with ui.row().classes("items-center gap-2"):
                panel.mock_meta_size_badge = ui.label(
                    f"{panel.mock_width}x{panel.mock_height}"
                ).classes("text-xs text-gray-400 font-mono")

        # Live Rendered Image Container
        with ui.element("div").classes(
            "w-full flex-1 min-h-[320px] flex items-center justify-center bg-slate-950 rounded-xl border border-white/10 p-2 overflow-hidden relative"
        ):
            panel.mock_img_elem = (
                ui.image(panel.mock_img_src)
                .props('id="mock-camera-preview-img" fit="contain"')
                .classes(
                    "w-full h-full max-h-[440px] object-contain rounded-lg shadow-md"
                )
                .style("max-width: 100%; max-height: 100%; width: 100%; height: 100%;")
            )

        # Telemetry Badges
        with ui.row().classes(
            "w-full items-center justify-between p-2.5 bg-slate-950/80 rounded-xl border border-white/5"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.label("Meter:").classes("text-xs text-gray-400")
                panel.mock_meta_meter_val = ui.label(panel.mock_value).classes(
                    "text-xs font-mono font-bold text-cyan-300"
                )

            with ui.row().classes("items-center gap-2"):
                ui.label("Digital:").classes("text-xs text-gray-400")
                panel.mock_meta_dig_val = ui.label("00452").classes(
                    "text-xs font-mono text-blue-300"
                )

            with ui.row().classes("items-center gap-2"):
                ui.label("Analog:").classes("text-xs text-gray-400")
                panel.mock_meta_ana_val = ui.label("9124").classes(
                    "text-xs font-mono text-amber-300"
                )
