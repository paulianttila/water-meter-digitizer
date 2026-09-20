"""Reusable page and card header components for standardizing title, icon, and toolbar layout."""

from collections.abc import Generator
from contextlib import contextmanager

from nicegui import ui

from gui.theme import HEADING_SECTION, ROW_ACTIONS, ROW_HEADER


def render_page_header(
    title: str,
    subtitle: str,
    icon: str = "speed",
    color: str = "cyan",
    classes: str = "w-full justify-between items-center",
) -> ui.row:
    """Render standard page header with left icon badge and title, returning the row."""
    with ui.row().classes(classes) as row, ui.row().classes("items-center gap-3"):
        with ui.element("div").classes(
            f"w-10 h-10 rounded-xl bg-{color}-500/20 border border-{color}-500/30 "
            f"flex items-center justify-center text-{color}-400"
        ):
            ui.icon(icon, size="md")
        with ui.column().classes("gap-0"):
            ui.label(title).classes("text-h5 font-['Outfit']")
            ui.label(subtitle).classes("text-xs text-gray-400")
    return row


@contextmanager
def page_header(
    title: str,
    subtitle: str,
    icon: str = "speed",
    color: str = "cyan",
    classes: str = "w-full justify-between items-center",
) -> Generator[ui.row, None, None]:
    """Context manager rendering header and yielding the right-hand action container row."""
    with ui.row().classes(classes):
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").classes(
                f"w-10 h-10 rounded-xl bg-{color}-500/20 border border-{color}-500/30 "
                f"flex items-center justify-center text-{color}-400"
            ):
                ui.icon(icon, size="md")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-h5 font-['Outfit']")
                ui.label(subtitle).classes("text-xs text-gray-400")
        with ui.row().classes("items-center gap-2") as actions_row:
            yield actions_row


@contextmanager
def card_header(
    title: str,
    subtitle: str | None = None,
    icon: str = "settings",
    color: str = "cyan",
    badge_text: str | None = None,
    badge_cls: str | None = None,
    classes: str = ROW_HEADER,
    title_classes: str = HEADING_SECTION,
) -> Generator[ui.row, None, None]:
    """Context manager for standard card headers with left icon+title and right action area."""
    with ui.row().classes(classes):
        with ui.row().classes(ROW_ACTIONS):
            ui.icon(icon, color=color).classes("text-xl")
            if subtitle:
                with ui.column().classes("gap-0"):
                    ui.label(title).classes(title_classes)
                    ui.label(subtitle).classes("text-xs text-gray-400")
            else:
                ui.label(title).classes(title_classes)
            if badge_text and badge_cls:
                with ui.element("span").classes(badge_cls):
                    ui.label(badge_text)
        with ui.row().classes(ROW_ACTIONS) as actions_row:
            yield actions_row
