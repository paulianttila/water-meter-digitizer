"""Mock Camera Studio controls component (parameters, sliders, overrides)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

from gui.api_console.registry import STANDARD_RESOLUTIONS

if TYPE_CHECKING:
    from gui.api_console.mock_studio_panel import MockStudioPanel


def render_mock_studio_controls(panel: MockStudioPanel) -> None:
    """Render procedural mock camera parameters controls (left column)."""
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
                    panel.mock_mode = e.value
                    if panel.mock_value_input:
                        panel.mock_value_input.enabled = panel.mock_mode == "fixed"
                    if panel.mock_rate_input:
                        panel.mock_rate_input.enabled = panel.mock_mode in (
                            "ticker",
                            "flow",
                        )
                    await panel._on_mock_param_change()

                panel.mock_mode_select = (
                    ui.select(
                        options=[
                            "fixed",
                            "ticker",
                            "random",
                            "flow",
                        ],
                        value=panel.mock_mode,
                        on_change=_on_mode_change,
                        label="Mode",
                    )
                    .props("outlined dense options-dense")
                    .classes("text-xs")
                )

                async def _on_val_change(e: Any) -> None:
                    panel.mock_value = e.value
                    await panel._on_mock_param_change()

                panel.mock_value_input = (
                    ui.input(
                        label="Meter Value",
                        value=panel.mock_value,
                        on_change=_on_val_change,
                    )
                    .props("outlined dense debounce=300")
                    .classes("font-mono text-xs")
                )

            with ui.row().classes("w-full items-center justify-between gap-2"):

                async def _on_rate_change(e: Any) -> None:
                    panel.mock_rate = float(e.value) if e.value is not None else 0.005
                    await panel._on_mock_param_change()

                panel.mock_rate_input = (
                    ui.number(
                        label="Ticker Rate / Frame",
                        value=panel.mock_rate,
                        step=0.001,
                        on_change=_on_rate_change,
                    )
                    .props("outlined dense debounce=500")
                    .classes("w-44 text-xs")
                )
                panel.mock_rate_input.enabled = panel.mock_mode in (
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
                panel.mock_rot_badge = ui.badge(
                    f"{panel.mock_rotate:.0f}°", color="cyan"
                )

            async def _on_rot_change(e: Any) -> None:
                panel.mock_rotate = float(e.value)
                if panel.mock_rot_badge:
                    panel.mock_rot_badge.text = f"{panel.mock_rotate:.0f}°"
                await panel._on_mock_param_change()

            panel.mock_rot_slider = (
                ui.slider(
                    min=-180.0,
                    max=180.0,
                    step=1.0,
                    value=panel.mock_rotate,
                    on_change=_on_rot_change,
                )
                .props("color=cyan dense debounce=500")
                .classes("w-full")
            )

            # Glare & Glare Intensity
            with ui.row().classes("w-full items-center justify-between gap-2"):

                async def _on_glare_change(e: Any) -> None:
                    panel.mock_glare = e.value
                    await panel._on_mock_param_change()

                panel.mock_glare_switch = (
                    ui.switch(
                        "Enable Glare Hotspot",
                        value=panel.mock_glare,
                        on_change=_on_glare_change,
                    )
                    .props("dense size=sm color=cyan")
                    .classes("text-xs text-gray-300")
                )

                async def _on_gpos_change(e: Any) -> None:
                    panel.mock_glare_pos = e.value
                    await panel._on_mock_param_change()

                panel.mock_glare_pos_input = (
                    ui.input(
                        label="Glare Pos (X,Y)",
                        value=panel.mock_glare_pos,
                        on_change=_on_gpos_change,
                    )
                    .props("outlined dense debounce=300")
                    .classes("w-32 font-mono text-xs")
                )

            # Noise & Blur
            with ui.grid(columns=2).classes("w-full gap-3"):
                with ui.column().classes("gap-1"):
                    ui.label("Sensor Noise (%)").classes("text-xs text-gray-400")

                    async def _on_noise_change(e: Any) -> None:
                        panel.mock_noise = float(e.value)
                        await panel._on_mock_param_change()

                    panel.mock_noise_slider = (
                        ui.slider(
                            min=0.0,
                            max=30.0,
                            step=0.5,
                            value=panel.mock_noise,
                            on_change=_on_noise_change,
                        )
                        .props("color=teal dense debounce=500")
                        .classes("w-full")
                    )

                with ui.column().classes("gap-1"):
                    ui.label("Lens Blur (px)").classes("text-xs text-gray-400")

                    async def _on_blur_change(e: Any) -> None:
                        panel.mock_blur = float(e.value)
                        await panel._on_mock_param_change()

                    panel.mock_blur_slider = (
                        ui.slider(
                            min=0.0,
                            max=5.0,
                            step=0.2,
                            value=panel.mock_blur,
                            on_change=_on_blur_change,
                        )
                        .props("color=amber dense debounce=500")
                        .classes("w-full")
                    )

            # Brightness & Contrast
            with ui.grid(columns=2).classes("w-full gap-3"):
                with ui.column().classes("gap-1"):
                    ui.label("Brightness Factor").classes("text-xs text-gray-400")

                    async def _on_bright_change(e: Any) -> None:
                        panel.mock_brightness = float(e.value)
                        await panel._on_mock_param_change()

                    panel.mock_bright_slider = (
                        ui.slider(
                            min=0.2,
                            max=2.0,
                            step=0.05,
                            value=panel.mock_brightness,
                            on_change=_on_bright_change,
                        )
                        .props("color=yellow dense debounce=500")
                        .classes("w-full")
                    )

                with ui.column().classes("gap-1"):
                    ui.label("Contrast Factor").classes("text-xs text-gray-400")

                    async def _on_contrast_change(e: Any) -> None:
                        panel.mock_contrast = float(e.value)
                        await panel._on_mock_param_change()

                    panel.mock_contrast_slider = (
                        ui.slider(
                            min=0.2,
                            max=2.0,
                            step=0.05,
                            value=panel.mock_contrast,
                            on_change=_on_contrast_change,
                        )
                        .props("color=orange dense debounce=500")
                        .classes("w-full")
                    )

        # --- Section 3: Appearance & Dimensions ---
        with (
            ui.expansion(
                "Colors, Appearance & Resolution",
                icon="palette",
                value=False,
            ).classes(
                "w-full bg-slate-950/60 rounded-xl border border-white/5 text-sm"
            ),
            ui.column().classes("w-full gap-3 p-1"),
        ):
            with ui.grid(columns=2).classes("w-full gap-2"):

                async def _on_lcd_c_change(e: Any) -> None:
                    panel.mock_lcd_color = e.value
                    await panel._on_mock_param_change()

                panel.mock_lcd_color_select = (
                    ui.select(
                        options=["black", "grey", "blue", "red"],
                        value=panel.mock_lcd_color,
                        label="LCD Digits",
                        on_change=_on_lcd_c_change,
                    )
                    .props("outlined dense options-dense")
                    .classes("text-xs")
                )

                async def _on_lcd_bg_change(e: Any) -> None:
                    panel.mock_lcd_bg = e.value
                    await panel._on_mock_param_change()

                panel.mock_lcd_bg_select = (
                    ui.select(
                        options=["grey", "green", "white", "black"],
                        value=panel.mock_lcd_bg,
                        label="LCD BG",
                        on_change=_on_lcd_bg_change,
                    )
                    .props("outlined dense options-dense")
                    .classes("text-xs")
                )

                async def _on_mbg_change(e: Any) -> None:
                    panel.mock_meter_bg = e.value
                    await panel._on_mock_param_change()

                panel.mock_meter_bg_select = (
                    ui.select(
                        options=["white", "metal", "worn", "dark", "blue", "brass"],
                        value=panel.mock_meter_bg,
                        label="Meter Faceplate",
                        on_change=_on_mbg_change,
                    )
                    .props("outlined dense options-dense")
                    .classes("text-xs")
                )

                async def _on_needle_c_change(e: Any) -> None:
                    panel.mock_needle_color = e.value
                    await panel._on_mock_param_change()

                panel.mock_needle_color_select = (
                    ui.select(
                        options=["red", "black", "blue"],
                        value=panel.mock_needle_color,
                        label="Needle Color",
                        on_change=_on_needle_c_change,
                    )
                    .props("outlined dense options-dense")
                    .classes("text-xs")
                )

            # Resolution preset + custom
            with ui.row().classes("w-full items-center gap-2"):

                async def _on_res_preset(e: Any) -> None:
                    val = e.value
                    panel.mock_res_preset = val
                    if val != "custom":
                        w, h = map(int, val.split("x"))
                        panel.mock_width = w
                        panel.mock_height = h
                        if panel.mock_width_input:
                            panel.mock_width_input.value = w
                        if panel.mock_height_input:
                            panel.mock_height_input.value = h
                    await panel._on_mock_param_change()

                res_opts = {k: k for k in STANDARD_RESOLUTIONS}
                res_opts["custom"] = "Custom"
                panel.mock_res_preset_select = (
                    ui.select(
                        options=res_opts,
                        value=panel.mock_res_preset,
                        label="Resolution",
                        on_change=_on_res_preset,
                    )
                    .props("outlined dense options-dense")
                    .classes("w-36 text-xs")
                )

                async def _on_w_change(e: Any) -> None:
                    panel.mock_width = int(e.value)
                    panel.mock_res_preset = "custom"
                    if panel.mock_res_preset_select:
                        panel.mock_res_preset_select.value = "custom"
                    await panel._on_mock_param_change()

                panel.mock_width_input = (
                    ui.number(
                        label="Width",
                        value=panel.mock_width,
                        min=320,
                        max=3840,
                        step=10,
                        on_change=_on_w_change,
                    )
                    .props("outlined dense")
                    .classes("w-20 text-xs")
                )

                async def _on_h_change(e: Any) -> None:
                    panel.mock_height = int(e.value)
                    panel.mock_res_preset = "custom"
                    if panel.mock_res_preset_select:
                        panel.mock_res_preset_select.value = "custom"
                    await panel._on_mock_param_change()

                panel.mock_height_input = (
                    ui.number(
                        label="Height",
                        value=panel.mock_height,
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
                panel.mock_digit_inputs.clear()
                for i in range(5):

                    def _make_dig_cb(idx: int):
                        async def _cb(e: Any) -> None:
                            panel.mock_digit_overrides[idx] = e.value
                            await panel._on_mock_param_change()

                        return _cb

                    d_inp = (
                        ui.input(
                            label=f"D{i+1}",
                            value=panel.mock_digit_overrides[i],
                            on_change=_make_dig_cb(i),
                        )
                        .props("outlined dense")
                        .classes("font-mono text-xs")
                    )
                    panel.mock_digit_inputs.append(d_inp)

            ui.label("Analog Needles (A1-A4, e.g. 0.0-9.9):").classes(
                "text-xs text-amber-400 font-semibold pt-1"
            )
            with ui.grid(columns=4).classes("w-full gap-1.5"):
                panel.mock_analog_inputs.clear()
                for i in range(4):

                    def _make_ana_cb(idx: int):
                        async def _cb(e: Any) -> None:
                            panel.mock_analog_overrides[idx] = e.value
                            await panel._on_mock_param_change()

                        return _cb

                    a_inp = (
                        ui.input(
                            label=f"A{i+1}",
                            value=panel.mock_analog_overrides[i],
                            on_change=_make_ana_cb(i),
                        )
                        .props("outlined dense")
                        .classes("font-mono text-xs")
                    )
                    panel.mock_analog_inputs.append(a_inp)
