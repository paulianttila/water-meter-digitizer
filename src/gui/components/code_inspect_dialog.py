"""Reusable modal dialog for inspecting formatted code, JSON, INI, or text snippets with copy functionality."""

from nicegui import ui

from gui.theme import (
    DIALOG_CARD,
    DIALOG_HEADER_ROW,
    ROW_ACTIONS,
    ROW_HEADER,
    copy_to_clipboard,
)


def open_code_inspect_dialog(
    title: str,
    code_content: str,
    language: str = "json",
    subtitle: str | None = None,
    caption: str | None = None,
    icon: str = "preview",
    max_width: str = "max-w-4xl",
) -> ui.dialog:
    """Open a modal showing syntax-highlighted code/JSON/INI with a one-click copy button."""
    with (
        ui.dialog() as dialog,
        ui.card()
        .classes(f"column no-wrap {DIALOG_CARD} {max_width} gap-3")
        .style("max-width: 95vw; width: 900px;"),
    ):
        with ui.row().classes(DIALOG_HEADER_ROW):
            with ui.row().classes(ROW_ACTIONS):
                ui.icon(icon, color="cyan", size="sm")
                with ui.column().classes("gap-0"):
                    ui.label(title).classes("text-base font-bold text-slate-100")
                    if subtitle:
                        ui.label(subtitle).classes("text-xs text-slate-400")
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense aria-label='Close dialog'"
            )

        ui.code(code_content, language=language).classes(
            "w-full max-h-[70vh] overflow-auto rounded-lg bg-slate-950 p-4 border border-white/5 font-mono text-xs"
        )

        with ui.row().classes(f"{ROW_HEADER} pt-1"):
            if caption:
                ui.label(caption).classes("text-xs font-mono text-slate-400")
            else:
                ui.element("div")
            ui.button(
                "Copy Content",
                icon="content_copy",
                on_click=lambda: copy_to_clipboard(code_content, "Copied to clipboard"),
            ).props("outline dense size=sm color=cyan")

    dialog.open()
    return dialog
