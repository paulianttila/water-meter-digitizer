"""Reusable modal dialog for confirmation actions (resets, deletions, undo, hot-reload)."""

import inspect
from collections.abc import Callable
from typing import Any

from nicegui import ui

COLOR_MAP = {
    "amber": {
        "icon_bg": "bg-amber-500/20",
        "icon_border": "border-amber-500/30",
        "icon_color": "text-amber-400",
        "btn_gradient": "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500",
    },
    "rose": {
        "icon_bg": "bg-rose-500/20",
        "icon_border": "border-rose-500/30",
        "icon_color": "text-rose-400",
        "btn_gradient": "bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500",
    },
    "blue": {
        "icon_bg": "bg-blue-500/20",
        "icon_border": "border-blue-500/30",
        "icon_color": "text-blue-400",
        "btn_gradient": "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500",
    },
    "indigo": {
        "icon_bg": "bg-indigo-500/20",
        "icon_border": "border-indigo-500/30",
        "icon_color": "text-indigo-400",
        "btn_gradient": "bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500",
    },
    "emerald": {
        "icon_bg": "bg-emerald-500/20",
        "icon_border": "border-emerald-500/30",
        "icon_color": "text-emerald-400",
        "btn_gradient": "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500",
    },
}


def open_confirm_dialog(
    title: str,
    message: str,
    confirm_label: str = "Confirm",
    confirm_icon: str | None = None,
    cancel_label: str = "Cancel",
    color_scheme: str = "amber",
    subtitle: str | None = None,
    icon: str = "warning",
    checkbox_label: str | None = None,
    checkbox_default: bool = True,
    on_confirm: Callable[..., Any] | None = None,
    max_width: str = "max-w-md",
) -> ui.dialog:
    """Standardized confirmation dialog with optional checkbox and theme styling."""
    theme = COLOR_MAP.get(color_scheme, COLOR_MAP["amber"])

    with (
        ui.dialog() as dialog,
        ui.card().classes(
            f"w-full {max_width} p-5 bg-slate-900 border border-white/10 rounded-2xl gap-4"
        ),
    ):
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").classes(
                f"w-10 h-10 rounded-xl {theme['icon_bg']} border {theme['icon_border']} "
                f"flex items-center justify-center {theme['icon_color']}"
            ):
                ui.icon(icon, size="md")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-base font-bold text-slate-100")
                if subtitle:
                    ui.label(subtitle).classes("text-xs text-slate-400")

        ui.label(message).classes("text-sm text-slate-300 leading-relaxed")

        checkbox_elem = None
        if checkbox_label:
            checkbox_elem = ui.checkbox(
                checkbox_label,
                value=checkbox_default,
            ).classes("text-xs text-slate-300")

        async def _handle_confirm():
            dialog.close()
            if on_confirm is not None:
                # If callback accepts arguments, pass checkbox state if available
                sig = inspect.signature(on_confirm)
                if len(sig.parameters) > 0 and checkbox_elem is not None:
                    res = on_confirm(checkbox_elem.value)
                else:
                    res = on_confirm()
                if inspect.isawaitable(res):
                    await res

        with ui.row().classes("w-full justify-end items-center gap-2 mt-2"):
            ui.button(cancel_label, on_click=dialog.close).props("flat dense").classes(
                "text-slate-300 px-3"
            )

            ui.button(
                confirm_label,
                icon=confirm_icon,
                on_click=_handle_confirm,
            ).props("unelevated dense").classes(
                f"{theme['btn_gradient']} text-white font-medium px-4 py-1.5 rounded-lg shadow-md"
            )

    dialog.open()
    return dialog
