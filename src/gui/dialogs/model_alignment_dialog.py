"""Interactive dialog for visually aligning camera photos under meter model presets."""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import events, ui

import utils.image as ImageUtils
from gui.theme import (
    DIALOG_CARD,
    DIALOG_FOOTER_ROW,
    DIALOG_HEADER_ROW,
    HEADING_SECTION,
    HEX_ROI_ANALOG,
    HEX_ROI_DIGITAL,
    HEX_ROI_REFS,
)
from utils.model_alignment import (
    calculate_initial_fit,
    project_template_rois_to_camera,
)

if TYPE_CHECKING:
    from config.meter_presets import MeterTypePreset

logger = logging.getLogger(__name__)


def open_model_alignment_dialog(
    camera_image_b64: str,
    preset: MeterTypePreset,
    digital_names: list[str] | None = None,
    analog_names: list[str] | None = None,
    on_applied: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Opens a modal dialog allowing the user to pan, zoom, and rotate their camera photo

    underneath the preset's fixed template wireframe to auto-calculate all ROI positions.
    """
    if not camera_image_b64:
        ui.notify("No camera image loaded to align", type="warning")
        return

    # 1. Determine camera image dimensions
    try:
        pil_img = ImageUtils.convert_base64_str_to_image(camera_image_b64)
        cam_w, cam_h = ImageUtils.image_size(pil_img)
    except Exception as e:
        logger.error(f"Failed to inspect camera image size: {e}")
        ui.notify("Invalid camera image", type="negative")
        return

    if cam_w <= 0 or cam_h <= 0:
        ui.notify("Unable to read camera image dimensions", type="negative")
        return

    # 2. Determine template canvas dimensions
    canvas_w = preset.reference_resolution.width or 640
    canvas_h = preset.reference_resolution.height or 480

    # 3. Retrieve template ROIs in template canvas space
    eff_digital_names = digital_names or [p.name for p in preset.default_rois.digital]
    eff_analog_names = analog_names or [p.name for p in preset.default_rois.analog]

    flow_split = 0
    if preset.has_secondary_group:
        flow_split = len([n for n in eff_digital_names if n.startswith("flow")])

    ref_pos = preset.get_reference_positions(canvas_w, canvas_h)
    dig_pos = (
        preset.get_digital_roi_positions(
            eff_digital_names, canvas_w, canvas_h, flow_split
        )
        or []
    )
    ana_pos = (
        preset.get_analog_roi_positions(eff_analog_names, canvas_w, canvas_h) or []
    )

    # 4. Compute default fit parameters
    init_scale, init_pan_x, init_pan_y = calculate_initial_fit(
        cam_w=cam_w, cam_h=cam_h, canvas_w=canvas_w, canvas_h=canvas_h
    )

    state = {
        "scale": init_scale,
        "pan_x": init_pan_x,
        "pan_y": init_pan_y,
        "angle": 0.0,
        "opacity": 0.85,
    }

    drag_state = {
        "is_dragging": False,
        "start_x": 0.0,
        "start_y": 0.0,
        "orig_pan_x": 0.0,
        "orig_pan_y": 0.0,
    }

    hidden_rois: set[str] = set()

    def build_svg_content() -> str:
        s = state["scale"]
        px = state["pan_x"]
        py = state["pan_y"]
        angle = state["angle"]
        opacity = state["opacity"]

        draw_w = cam_w * s
        draw_h = cam_h * s
        cx = px + draw_w / 2.0
        cy = py + draw_h / 2.0
        rot_attr = (
            f'transform="rotate({angle:.1f} {cx:.1f} {cy:.1f})"' if angle != 0 else ""
        )

        # SVG string
        svg_parts = [
            f'<svg width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" '
            'xmlns="http://www.w3.org/2000/svg" style="display:block;user-select:none;">',
            '<rect width="100%" height="100%" fill="#020617"/>',
            f'<image href="data:image/jpeg;base64,{camera_image_b64}" '
            f'x="{px:.1f}" y="{py:.1f}" width="{draw_w:.1f}" height="{draw_h:.1f}" '
            f'{rot_attr} preserveAspectRatio="none" style="pointer-events:none;"/>',
            f'<g opacity="{opacity:.2f}">',
        ]

        # Draw references
        for r in ref_pos:
            if r.name in hidden_rois:
                continue
            rx, ry, rw, rh = r.x, r.y, r.w, r.h
            rcx = rx + rw / 2.0
            rcy = ry + rh / 2.0
            y_lbl = ry - 5 if ry >= 14 else ry + 13
            svg_parts.append(
                f'<text x="{rx}" y="{y_lbl}" fill="{HEX_ROI_REFS}" font-size="10" font-family="monospace" font-weight="bold">{r.name}</text>'
                f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" '
                f'stroke="{HEX_ROI_REFS}" stroke-width="2" stroke-dasharray="3 3" '
                f'fill="{HEX_ROI_REFS}" fill-opacity="0.18"/>'
                f'<line x1="{rx}" y1="{rcy:.1f}" x2="{rx + rw}" y2="{rcy:.1f}" stroke="{HEX_ROI_REFS}" stroke-width="1.5"/>'
                f'<line x1="{rcx:.1f}" y1="{ry}" x2="{rcx:.1f}" y2="{ry + rh}" stroke="{HEX_ROI_REFS}" stroke-width="1.5"/>'
            )

        # Draw digital ROIs: outer box, inner box (0.2 inset), and horizontal center dividing line
        for d in dig_pos:
            if d.name in hidden_rois:
                continue
            dx, dy, dw, dh = d.x, d.y, d.w, d.h
            y_lbl = dy - 5 if dy >= 14 else dy + 13
            inner_x = dx + dw * 0.2
            inner_y = dy + dh * 0.2
            inner_w = dw - dw * 0.4
            inner_h = dh - dh * 0.4
            line_y = dy + dh / 2.0
            svg_parts.append(
                f'<text x="{dx}" y="{y_lbl}" fill="{HEX_ROI_DIGITAL}" font-size="10" font-family="monospace" font-weight="bold">{d.name}</text>'
                f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" '
                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="2" '
                f'fill="{HEX_ROI_DIGITAL}" fill-opacity="0.12" rx="1"/>'
                f'<rect x="{inner_x:.1f}" y="{inner_y:.1f}" width="{inner_w:.1f}" height="{inner_h:.1f}" '
                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="1.2" fill-opacity="0"/>'
                f'<line x1="{inner_x:.1f}" y1="{line_y:.1f}" x2="{inner_x + inner_w:.1f}" y2="{line_y:.1f}" '
                f'stroke="{HEX_ROI_DIGITAL}" stroke-width="1.2"/>'
            )

        # Draw analog ROIs: outer box, inscribed ellipse/circle, and crosshairs
        for a in ana_pos:
            if a.name in hidden_rois:
                continue
            ax, ay, aw, ah = a.x, a.y, a.w, a.h
            acx = ax + aw / 2.0
            acy = ay + ah / 2.0
            y_lbl = ay - 5 if ay >= 14 else ay + 13
            svg_parts.append(
                f'<text x="{ax}" y="{y_lbl}" fill="{HEX_ROI_ANALOG}" font-size="10" font-family="monospace" font-weight="bold">{a.name}</text>'
                f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" '
                f'stroke="{HEX_ROI_ANALOG}" stroke-width="2" '
                f'fill="{HEX_ROI_ANALOG}" fill-opacity="0.10"/>'
                f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="{aw/2.0:.1f}" ry="{ah/2.0:.1f}" '
                f'stroke="{HEX_ROI_ANALOG}" stroke-width="1.5" fill-opacity="0"/>'
                f'<line x1="{acx:.1f}" y1="{ay}" x2="{acx:.1f}" y2="{ay + ah}" stroke="{HEX_ROI_ANALOG}" stroke-width="1.2"/>'
                f'<line x1="{ax}" y1="{acy:.1f}" x2="{ax + aw}" y2="{acy:.1f}" stroke="{HEX_ROI_ANALOG}" stroke-width="1.2"/>'
            )

        svg_parts.append("</g></svg>")
        return "".join(svg_parts)

    with (
        ui.dialog().props("persistent max-width") as dialog,
        ui.card().classes(
            f"{DIALOG_CARD} max-w-5xl w-[96vw] max-h-[92vh] flex flex-col p-4 overflow-hidden"
        ),
    ):
        # Header
        with ui.row().classes(f"{DIALOG_HEADER_ROW} flex-shrink-0"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("filter_center_focus", size="sm").classes("text-cyan-400")
                ui.label(f"Align Camera Photo to Model: {preset.label}").classes(
                    HEADING_SECTION
                )
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense"
            ).classes("text-slate-400 hover:text-white")

        ui.label(
            "Drag the canvas to move the camera image, or use the zoom/angle sliders until your meter lines up with the wireframe overlay."
        ).classes("text-xs text-slate-300 flex-shrink-0 -mt-2")

        # Pre-declare UI control handles for centralized synchronization
        scale_slider: ui.slider | None = None
        pan_x_slider: ui.slider | None = None
        pan_y_slider: ui.slider | None = None
        angle_slider: ui.slider | None = None
        scale_label: ui.label | None = None
        angle_label: ui.label | None = None
        hud_scale_label: ui.label | None = None
        hud_angle_label: ui.label | None = None

        def update_canvas_view() -> None:
            svg_data = build_svg_content()
            b64_svg = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
            viewport_image.set_source(f"data:image/svg+xml;base64,{b64_svg}")

        def sync_controls() -> None:
            if scale_slider is not None:
                scale_slider.value = state["scale"]
            if pan_x_slider is not None:
                pan_x_slider.value = state["pan_x"]
            if pan_y_slider is not None:
                pan_y_slider.value = state["pan_y"]
            if angle_slider is not None:
                angle_slider.value = state["angle"]
            if scale_label is not None:
                scale_label.text = f"{int(state['scale'] * 100)}%"
            if angle_label is not None:
                angle_label.text = f"{state['angle']:.1f}°"
            if hud_scale_label is not None:
                hud_scale_label.text = f"{int(state['scale'] * 100)}%"
            if hud_angle_label is not None:
                hud_angle_label.text = f"{state['angle']:.1f}°"
            update_canvas_view()

        def apply_zoom(
            new_scale: float,
            focus_cx: float | None = None,
            focus_cy: float | None = None,
        ) -> None:
            old_scale = state["scale"]
            new_scale = max(0.15, min(2.50, round(new_scale, 3)))
            if old_scale <= 0:
                return

            if focus_cx is None:
                focus_cx = canvas_w / 2.0
            if focus_cy is None:
                focus_cy = canvas_h / 2.0

            old_w = cam_w * old_scale
            old_h = cam_h * old_scale
            new_w = cam_w * new_scale
            new_h = cam_h * new_scale

            u = (focus_cx - state["pan_x"]) / old_w if old_w > 0 else 0.5
            v = (focus_cy - state["pan_y"]) / old_h if old_h > 0 else 0.5

            state["scale"] = new_scale
            state["pan_x"] = round(focus_cx - u * new_w, 1)
            state["pan_y"] = round(focus_cy - v * new_h, 1)
            sync_controls()

        def adjust_angle(delta: float) -> None:
            state["angle"] = max(-15.0, min(15.0, round(state["angle"] + delta, 1)))
            sync_controls()

        def adjust_pan(dx: float, dy: float) -> None:
            state["pan_x"] = round(state["pan_x"] + dx, 1)
            state["pan_y"] = round(state["pan_y"] + dy, 1)
            sync_controls()

        def reset_view() -> None:
            state["scale"] = init_scale
            state["pan_x"] = init_pan_x
            state["pan_y"] = init_pan_y
            state["angle"] = 0.0
            sync_controls()

        # Keyboard shortcuts handler
        def handle_keyboard(e: events.KeyEventArguments) -> None:
            if not dialog.value or not e.action.keydown:
                return
            step = 10 if e.modifiers.shift else 1
            if e.key in ("+", "="):
                apply_zoom(state["scale"] + 0.01)
            elif e.key in ("-", "_"):
                apply_zoom(state["scale"] - 0.01)
            elif e.key == "ArrowUp":
                adjust_pan(0, -step)
            elif e.key == "ArrowDown":
                adjust_pan(0, step)
            elif e.key == "ArrowLeft":
                adjust_pan(-step, 0)
            elif e.key == "ArrowRight":
                adjust_pan(step, 0)
            elif e.key in ("[", "<"):
                adjust_angle(-0.5)
            elif e.key in ("]", ">"):
                adjust_angle(0.5)
            elif e.key in ("0", "f", "F"):
                reset_view()

        ui.keyboard(on_key=handle_keyboard)

        # Main Content Row: Left Canvas, Right Controls
        with ui.row().classes("w-full flex-1 min-h-0 gap-4 no-wrap overflow-hidden"):
            # Left Viewport Card
            with (
                ui.card().classes(
                    "flex-1 h-full min-h-[360px] p-2 bg-slate-950 border border-white/10 rounded-xl "
                    "flex flex-col items-center justify-center relative overflow-hidden"
                ),
            ):
                viewport_image = ui.interactive_image(
                    size=(canvas_w, canvas_h),
                    events=["mousedown", "mouseup", "mousemove"],
                    cross=False,
                ).classes(
                    "w-full h-full max-h-full object-contain cursor-grab active:cursor-grabbing rounded-lg"
                )

                def on_mouse_event(e: events.MouseEventArguments) -> None:
                    if e.type == "mousedown":
                        drag_state["is_dragging"] = True
                        drag_state["start_x"] = e.image_x
                        drag_state["start_y"] = e.image_y
                        drag_state["orig_pan_x"] = state["pan_x"]
                        drag_state["orig_pan_y"] = state["pan_y"]
                    elif e.type == "mouseup":
                        drag_state["is_dragging"] = False
                    elif e.type == "mousemove" and drag_state["is_dragging"]:
                        dx = e.image_x - drag_state["start_x"]
                        dy = e.image_y - drag_state["start_y"]
                        state["pan_x"] = round(drag_state["orig_pan_x"] + dx, 1)
                        state["pan_y"] = round(drag_state["orig_pan_y"] + dy, 1)
                        if pan_x_slider is not None:
                            pan_x_slider.value = state["pan_x"]
                        if pan_y_slider is not None:
                            pan_y_slider.value = state["pan_y"]
                        update_canvas_view()

                viewport_image.on_mouse(on_mouse_event)

                # Mouse Wheel / Trackpad Pinch Zoom directly centered on cursor
                def on_wheel_event(e: events.GenericEventArguments) -> None:
                    data = e.args if isinstance(e.args, dict) else {}
                    delta_y = float(data.get("deltaY", 0))
                    if delta_y == 0:
                        return
                    frac_x = float(data.get("fracX", 0.5))
                    frac_y = float(data.get("fracY", 0.5))
                    focus_x = frac_x * canvas_w
                    focus_y = frac_y * canvas_h

                    factor = 1.08 if delta_y < 0 else (1.0 / 1.08)
                    apply_zoom(
                        state["scale"] * factor, focus_cx=focus_x, focus_cy=focus_y
                    )

                viewport_image.on(
                    "wheel",
                    handler=on_wheel_event,
                    args=["deltaY", "fracX", "fracY"],
                    js_handler="""(e) => {
                        e.preventDefault();
                        const rect = e.currentTarget.getBoundingClientRect();
                        const fracX = rect.width > 0 ? (e.clientX - rect.left) / rect.width : 0.5;
                        const fracY = rect.height > 0 ? (e.clientY - rect.top) / rect.height : 0.5;
                        emit({
                            deltaY: e.deltaY,
                            fracX: Math.max(0, Math.min(1, fracX)),
                            fracY: Math.max(0, Math.min(1, fracY))
                        });
                    }""",
                    throttle=0.03,
                )

                # Keybinding & gesture hint pill
                ui.label(
                    "💡 Scroll wheel: zoom to cursor • Drag: pan • Arrow keys: nudge • [ ]: rotate"
                ).classes(
                    "absolute top-2 left-3 z-10 pointer-events-none text-[10px] text-slate-400 "
                    "bg-slate-950/75 backdrop-blur-sm border border-white/10 px-2 py-0.5 rounded-full select-none"
                )

                # Floating Canvas Mini Toolbar HUD
                with ui.row().classes(
                    "absolute bottom-3 left-1/2 -translate-x-1/2 z-20 "
                    "bg-slate-900/90 backdrop-blur-md border border-white/15 "
                    "shadow-2xl rounded-full px-2.5 py-1 items-center gap-1 text-xs select-none"
                ):
                    ui.button(
                        icon="remove",
                        on_click=lambda: apply_zoom(state["scale"] - 0.01),
                    ).props("flat round dense").classes(
                        "text-slate-300 hover:text-white w-6 h-6 text-xs"
                    ).tooltip(
                        "Zoom Out (-1%)"
                    )

                    hud_scale_label = ui.label(f"{int(state['scale'] * 100)}%").classes(
                        "font-mono text-cyan-400 font-bold min-w-[42px] text-center cursor-pointer text-xs"
                    )
                    hud_scale_label.tooltip("Click to reset zoom to 100%").on(
                        "click", lambda: apply_zoom(1.0)
                    )

                    ui.button(
                        icon="add", on_click=lambda: apply_zoom(state["scale"] + 0.01)
                    ).props("flat round dense").classes(
                        "text-slate-300 hover:text-white w-6 h-6 text-xs"
                    ).tooltip(
                        "Zoom In (+1%)"
                    )

                    ui.element("div").classes("w-[1px] h-3.5 bg-white/20 mx-1")

                    ui.button(
                        icon="rotate_left", on_click=lambda: adjust_angle(-0.5)
                    ).props("flat round dense").classes(
                        "text-slate-300 hover:text-amber-400 w-6 h-6 text-xs"
                    ).tooltip(
                        "Rotate Left (-0.5°)"
                    )

                    hud_angle_label = ui.label(f"{state['angle']:.1f}°").classes(
                        "font-mono text-amber-400 font-bold min-w-[38px] text-center cursor-pointer text-xs"
                    )
                    hud_angle_label.tooltip("Click to reset angle to 0°").on(
                        "click", lambda: adjust_angle(-state["angle"])
                    )

                    ui.button(
                        icon="rotate_right", on_click=lambda: adjust_angle(0.5)
                    ).props("flat round dense").classes(
                        "text-slate-300 hover:text-amber-400 w-6 h-6 text-xs"
                    ).tooltip(
                        "Rotate Right (+0.5°)"
                    )

                    ui.element("div").classes("w-[1px] h-3.5 bg-white/20 mx-1")

                    ui.button(icon="center_focus_strong", on_click=reset_view).props(
                        "flat round dense"
                    ).classes(
                        "text-slate-300 hover:text-cyan-400 w-6 h-6 text-xs"
                    ).tooltip(
                        "Center & Fit to Frame"
                    )

            # Right Controls Panel
            with (
                ui.column().classes(
                    "w-72 flex-shrink-0 h-full overflow-y-auto pr-1 gap-3 text-xs"
                ),
            ):
                # Zoom / Scale Card
                with ui.card().classes(
                    "w-full p-2.5 bg-slate-900/80 border border-white/10 rounded-xl gap-1.5"
                ):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Zoom / Scale").classes(
                            "font-bold text-slate-200 text-xs"
                        )
                        scale_label = ui.label(f"{int(state['scale'] * 100)}%").classes(
                            "font-mono text-cyan-400 font-bold"
                        )

                    with ui.row().classes("w-full justify-between gap-1 mt-0.5"):
                        ui.button(
                            "-10%", on_click=lambda: apply_zoom(state["scale"] - 0.10)
                        ).props("flat dense").classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button(
                            "-1%", on_click=lambda: apply_zoom(state["scale"] - 0.01)
                        ).props("flat dense").classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button("1:1", on_click=lambda: apply_zoom(1.0)).props(
                            "flat dense"
                        ).classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button(
                            "+1%", on_click=lambda: apply_zoom(state["scale"] + 0.01)
                        ).props("flat dense").classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button(
                            "+10%", on_click=lambda: apply_zoom(state["scale"] + 0.10)
                        ).props("flat dense").classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )

                    def on_scale_change(e: Any) -> None:
                        val = float(e.value or 1.0)
                        apply_zoom(val)

                    scale_slider = (
                        ui.slider(
                            min=0.15,
                            max=2.50,
                            step=0.01,
                            value=state["scale"],
                            on_change=on_scale_change,
                        )
                        .props("dense")
                        .classes("w-full")
                    )

                # Pan Position Card
                with ui.card().classes(
                    "w-full p-2.5 bg-slate-900/80 border border-white/10 rounded-xl gap-1.5"
                ):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Pan Position (X / Y)").classes(
                            "font-bold text-slate-200 text-xs"
                        )
                        with ui.row().classes("gap-0.5"):
                            ui.button("◀", on_click=lambda: adjust_pan(-5, 0)).props(
                                "flat dense"
                            ).classes(
                                "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                            ).tooltip(
                                "Pan Left (-5px)"
                            )
                            ui.button("▲", on_click=lambda: adjust_pan(0, -5)).props(
                                "flat dense"
                            ).classes(
                                "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                            ).tooltip(
                                "Pan Up (-5px)"
                            )
                            ui.button("▼", on_click=lambda: adjust_pan(0, 5)).props(
                                "flat dense"
                            ).classes(
                                "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                            ).tooltip(
                                "Pan Down (+5px)"
                            )
                            ui.button("▶", on_click=lambda: adjust_pan(5, 0)).props(
                                "flat dense"
                            ).classes(
                                "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                            ).tooltip(
                                "Pan Right (+5px)"
                            )

                    def on_pan_x_change(e: Any) -> None:
                        state["pan_x"] = float(e.value or 0.0)
                        update_canvas_view()

                    def on_pan_y_change(e: Any) -> None:
                        state["pan_y"] = float(e.value or 0.0)
                        update_canvas_view()

                    with ui.row().classes("w-full items-center justify-between gap-2"):
                        ui.label("X:").classes("font-mono text-slate-400 w-4")
                        pan_x_slider = (
                            ui.slider(
                                min=-canvas_w,
                                max=canvas_w,
                                step=1,
                                value=state["pan_x"],
                                on_change=on_pan_x_change,
                            )
                            .props("dense")
                            .classes("flex-1")
                        )

                    with ui.row().classes("w-full items-center justify-between gap-2"):
                        ui.label("Y:").classes("font-mono text-slate-400 w-4")
                        pan_y_slider = (
                            ui.slider(
                                min=-canvas_h,
                                max=canvas_h,
                                step=1,
                                value=state["pan_y"],
                                on_change=on_pan_y_change,
                            )
                            .props("dense")
                            .classes("flex-1")
                        )

                # Rotation & Opacity Card
                with ui.card().classes(
                    "w-full p-2.5 bg-slate-900/80 border border-white/10 rounded-xl gap-1.5"
                ):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Fine Rotation").classes(
                            "font-bold text-slate-200 text-xs"
                        )
                        angle_label = ui.label(f"{state['angle']:.1f}°").classes(
                            "font-mono text-amber-400 font-bold"
                        )

                    with ui.row().classes("w-full justify-between gap-1 mt-0.5"):
                        ui.button("-2°", on_click=lambda: adjust_angle(-2.0)).props(
                            "flat dense"
                        ).classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button("-0.5°", on_click=lambda: adjust_angle(-0.5)).props(
                            "flat dense"
                        ).classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button(
                            "0°", on_click=lambda: adjust_angle(-state["angle"])
                        ).props("flat dense").classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button("+0.5°", on_click=lambda: adjust_angle(0.5)).props(
                            "flat dense"
                        ).classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )
                        ui.button("+2°", on_click=lambda: adjust_angle(2.0)).props(
                            "flat dense"
                        ).classes(
                            "text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 px-1.5 py-0.5 rounded text-[10px]"
                        )

                    def on_angle_change(e: Any) -> None:
                        val = float(e.value or 0.0)
                        adjust_angle(val - state["angle"])

                    angle_slider = (
                        ui.slider(
                            min=-15.0,
                            max=15.0,
                            step=0.5,
                            value=state["angle"],
                            on_change=on_angle_change,
                        )
                        .props("dense color=amber")
                        .classes("w-full")
                    )

                    with ui.row().classes(
                        "w-full justify-between items-center mt-1 pt-1 border-t border-white/5"
                    ):
                        ui.label("Wireframe Opacity").classes(
                            "text-slate-300 text-[11px]"
                        )
                        opacity_label = ui.label(
                            f"{int(state['opacity'] * 100)}%"
                        ).classes("font-mono text-slate-400 text-[11px]")

                    def on_opacity_change(e: Any) -> None:
                        val = float(e.value or 0.85)
                        state["opacity"] = val
                        opacity_label.text = f"{int(val * 100)}%"
                        update_canvas_view()

                    ui.slider(
                        min=0.20,
                        max=1.00,
                        step=0.05,
                        value=state["opacity"],
                        on_change=on_opacity_change,
                    ).props("dense color=grey").classes("w-full")

                # ROI Visibility Card
                if dig_pos or ana_pos or ref_pos:
                    with ui.card().classes(
                        "w-full p-2.5 bg-slate-900/80 border border-white/10 rounded-xl gap-2"
                    ):
                        with ui.row().classes("w-full justify-between items-center"):
                            with ui.row().classes("items-center gap-1.5"):
                                ui.icon("layers", size="xs").classes("text-slate-300")
                                ui.label("ROI Overlays").classes(
                                    "font-bold text-slate-200 text-xs"
                                )
                            with ui.row().classes("gap-1 items-center"):

                                def show_all_rois() -> None:
                                    hidden_rois.clear()
                                    render_visibility_chips()
                                    update_canvas_view()

                                def hide_all_rois() -> None:
                                    for d in dig_pos:
                                        hidden_rois.add(d.name)
                                    for a in ana_pos:
                                        hidden_rois.add(a.name)
                                    for r in ref_pos:
                                        hidden_rois.add(r.name)
                                    render_visibility_chips()
                                    update_canvas_view()

                                ui.button("All", on_click=show_all_rois).props(
                                    "flat dense"
                                ).classes(
                                    "text-[10px] text-cyan-400 hover:text-cyan-300 px-1 py-0.5"
                                )
                                ui.label("|").classes("text-slate-600 text-[10px]")
                                ui.button("None", on_click=hide_all_rois).props(
                                    "flat dense"
                                ).classes(
                                    "text-[10px] text-slate-400 hover:text-slate-300 px-1 py-0.5"
                                )

                        visibility_container = ui.column().classes("w-full gap-2")

                        def toggle_roi_visibility(name: str) -> None:
                            if name in hidden_rois:
                                hidden_rois.remove(name)
                            else:
                                hidden_rois.add(name)
                            render_visibility_chips()
                            update_canvas_view()

                        def render_visibility_chips() -> None:
                            visibility_container.clear()
                            with visibility_container:
                                if dig_pos:
                                    with ui.column().classes("w-full gap-1"):
                                        ui.label("Digits").classes(
                                            "text-[10px] font-semibold text-cyan-400 uppercase tracking-wider"
                                        )
                                        with ui.row().classes("w-full flex-wrap gap-1"):
                                            for d in dig_pos:
                                                is_hidden = d.name in hidden_rois
                                                btn_classes = (
                                                    "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                    "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                    if is_hidden
                                                    else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 "
                                                    "text-cyan-300 border border-cyan-500/40 hover:bg-cyan-900/80"
                                                )
                                                icon_name = (
                                                    "visibility_off"
                                                    if is_hidden
                                                    else "visibility"
                                                )
                                                ui.button(
                                                    d.name,
                                                    icon=icon_name,
                                                    on_click=lambda name=d.name: toggle_roi_visibility(
                                                        name
                                                    ),
                                                ).props(
                                                    "dense unelevated"
                                                    if not is_hidden
                                                    else "dense flat"
                                                ).classes(
                                                    btn_classes
                                                )

                                if ana_pos:
                                    with ui.column().classes("w-full gap-1"):
                                        ui.label("Analog Dials").classes(
                                            "text-[10px] font-semibold text-amber-400 uppercase tracking-wider"
                                        )
                                        with ui.row().classes("w-full flex-wrap gap-1"):
                                            for a in ana_pos:
                                                is_hidden = a.name in hidden_rois
                                                btn_classes = (
                                                    "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                    "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                    if is_hidden
                                                    else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 "
                                                    "text-amber-300 border border-amber-500/40 hover:bg-amber-900/80"
                                                )
                                                icon_name = (
                                                    "visibility_off"
                                                    if is_hidden
                                                    else "visibility"
                                                )
                                                ui.button(
                                                    a.name,
                                                    icon=icon_name,
                                                    on_click=lambda name=a.name: toggle_roi_visibility(
                                                        name
                                                    ),
                                                ).props(
                                                    "dense unelevated"
                                                    if not is_hidden
                                                    else "dense flat"
                                                ).classes(
                                                    btn_classes
                                                )

                                if ref_pos:
                                    with ui.column().classes("w-full gap-1"):
                                        ui.label("Reference Markers").classes(
                                            "text-[10px] font-semibold text-emerald-400 uppercase tracking-wider"
                                        )
                                        with ui.row().classes("w-full flex-wrap gap-1"):
                                            for r in ref_pos:
                                                is_hidden = r.name in hidden_rois
                                                btn_classes = (
                                                    "text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/40 "
                                                    "text-slate-500 border border-slate-700/40 line-through opacity-70"
                                                    if is_hidden
                                                    else "text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 "
                                                    "text-emerald-300 border border-emerald-500/40 hover:bg-emerald-900/80"
                                                )
                                                icon_name = (
                                                    "visibility_off"
                                                    if is_hidden
                                                    else "visibility"
                                                )
                                                ui.button(
                                                    r.name,
                                                    icon=icon_name,
                                                    on_click=lambda name=r.name: toggle_roi_visibility(
                                                        name
                                                    ),
                                                ).props(
                                                    "dense unelevated"
                                                    if not is_hidden
                                                    else "dense flat"
                                                ).classes(
                                                    btn_classes
                                                )

                        render_visibility_chips()

                # Action Presets Card
                with ui.row().classes("w-full gap-2 mt-auto"):
                    ui.button(
                        "Center & Fit", icon="center_focus_strong", on_click=reset_view
                    ).props("outline dense").classes(
                        "flex-1 text-slate-300 border-white/20 hover:bg-white/10 text-xs py-1"
                    )

        # Footer
        with ui.row().classes(f"{DIALOG_FOOTER_ROW} flex-shrink-0"):
            ui.button("Cancel", on_click=dialog.close).props("flat dense").classes(
                "text-slate-400 hover:text-white px-3 py-1"
            )

            def apply_and_close() -> None:
                # Calculate projected camera coordinates
                calc_refs = project_template_rois_to_camera(
                    template_rois=ref_pos,
                    scale=state["scale"],
                    pan_x=state["pan_x"],
                    pan_y=state["pan_y"],
                    cam_w=cam_w,
                    cam_h=cam_h,
                )
                calc_dig = project_template_rois_to_camera(
                    template_rois=dig_pos,
                    scale=state["scale"],
                    pan_x=state["pan_x"],
                    pan_y=state["pan_y"],
                    cam_w=cam_w,
                    cam_h=cam_h,
                )
                calc_ana = project_template_rois_to_camera(
                    template_rois=ana_pos,
                    scale=state["scale"],
                    pan_x=state["pan_x"],
                    pan_y=state["pan_y"],
                    cam_w=cam_w,
                    cam_h=cam_h,
                )

                if on_applied:
                    on_applied(
                        {
                            "references": calc_refs,
                            "digital": calc_dig,
                            "analog": calc_ana,
                            "rotation": state["angle"],
                        }
                    )

                dialog.close()
                ui.notify(
                    f"Aligned to {preset.label}: computed {len(calc_refs)} references, "
                    f"{len(calc_dig)} digits, {len(calc_ana)} analog dials",
                    type="positive",
                )

            ui.button(
                "✨ Apply Alignment & Calculate ROIs",
                icon="check_circle",
                on_click=apply_and_close,
            ).props("unelevated dense").classes(
                "bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-1.5 rounded-lg shadow-md"
            )

        # Initial canvas render
        update_canvas_view()
        dialog.open()
