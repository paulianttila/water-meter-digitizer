"""Reusable Configuration History and Snapshot management dialog."""

import html
import inspect
from collections.abc import Callable
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.components.confirm_dialog import open_confirm_dialog
from gui.theme import (
    BADGE_AUTO_CLS,
    BADGE_SNAP_CLS,
    BTN_ACTIVE_CLS,
    BTN_INACTIVE_CLS,
    TAG_AUTO_CLS,
    TAG_SNAP_CLS,
)


def format_diff_html(diff_lines: list[str]) -> str:
    """Format unified diff lines into a single performant HTML string."""
    if not diff_lines:
        return (
            '<div class="flex items-center gap-2 py-2 px-3 bg-emerald-950/40 '
            'border border-emerald-500/30 rounded-lg text-emerald-300 text-xs w-full">'
            '<span class="text-emerald-400 font-bold">✓</span> '
            "Identical to current configuration (no differences)</div>"
        )

    rows = []
    for line in diff_lines:
        clean = line.rstrip("\r\n")
        escaped = html.escape(clean)
        if not escaped:
            escaped = "&nbsp;"
        if clean.startswith("---") or clean.startswith("+++"):
            rows.append(f'<div class="text-slate-400 font-bold px-1">{escaped}</div>')
        elif clean.startswith("@@"):
            rows.append(
                '<div class="text-cyan-400 bg-cyan-950/60 px-1 rounded my-0.5">'
                f"{escaped}</div>"
            )
        elif clean.startswith("+"):
            rows.append(
                '<div class="text-emerald-300 bg-emerald-950/70 border-l-2 '
                f'border-emerald-500 px-1">{escaped}</div>'
            )
        elif clean.startswith("-"):
            rows.append(
                '<div class="text-rose-300 bg-rose-950/70 border-l-2 '
                f'border-rose-500 px-1">{escaped}</div>'
            )
        else:
            rows.append(f'<div class="text-slate-400 px-1">{escaped}</div>')

    return (
        '<div class="w-full bg-slate-950 rounded-lg p-3 font-mono text-xs '
        'overflow-x-auto border border-white/10 space-y-0.5 leading-tight">'
        + "".join(rows)
        + "</div>"
    )


def open_config_history_dialog(
    callbacks: Callbacks,
    title: str = "Configuration History",
    subtitle: str = "Manage automatic backups, snapshots, and line-by-line diffs",
    show_snapshot_creator: bool = True,
    on_restore: Callable[[str, str], Any] | None = None,
    on_test: Callable[[str, str], Any] | None = None,
    allow_diff: bool = True,
    allow_delete: bool = True,
    on_delete: Callable[[str], Any] | None = None,
    max_width: str = "max-w-5xl",
) -> ui.dialog:
    """Open unified configuration history & backup management dialog."""
    with (
        ui.dialog() as history_dialog,
        ui.card()
        .classes(
            f"column no-wrap w-full {max_width} p-6 bg-slate-900 border border-white/10 rounded-2xl gap-4"
        )
        .style("max-width: 95vw; width: 1000px;"),
    ):
        with ui.row().classes(
            "w-full justify-between items-center pb-3 border-b border-white/10"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 "
                    "flex items-center justify-center text-indigo-400"
                ):
                    ui.icon("manage_history", size="md")
                with ui.column().classes("gap-0"):
                    ui.label(title).classes("text-lg font-bold text-slate-100")
                    ui.label(subtitle).classes("text-xs text-slate-400")
            ui.button(icon="close", on_click=history_dialog.close).props(
                "flat round dense aria-label='Close dialog'"
            )

        # Optional snapshot creator bar
        if show_snapshot_creator:
            with ui.row().classes(
                "w-full items-center justify-between p-3 rounded-xl "
                "bg-slate-950/70 border border-white/10 gap-3"
            ):
                with ui.row().classes("items-center gap-2 flex-grow"):
                    ui.icon("bookmark_add", color="indigo", size="sm")
                    snapshot_input = (
                        ui.input(
                            placeholder=(
                                "Snapshot label / description (e.g. Pre-calibration)"
                            )
                        )
                        .props("dense borderless")
                        .classes("w-full text-sm text-slate-200")
                    )

                def create_snapshot():
                    tag_val = snapshot_input.value.strip()
                    res = callbacks.create_config_snapshot(tag=tag_val)
                    if res:
                        snapshot_input.value = ""
                        ui.notify("Manual snapshot saved", type="positive")
                        refresh_backups_list()
                    else:
                        ui.notify("Could not create snapshot", type="negative")

                ui.button(
                    "Take Snapshot",
                    icon="camera",
                    on_click=create_snapshot,
                ).props("unelevated dense").classes(
                    "bg-indigo-600 hover:bg-indigo-500 text-white "
                    "text-xs font-medium px-3 py-1 shadow"
                )

        # Backups container
        backups_container = ui.column().classes(
            "w-full gap-2 max-h-[55vh] overflow-y-auto pr-1"
        )

        def refresh_backups_list():
            backups_container.clear()
            try:
                backups = callbacks.list_config_backups()
            except Exception as e:
                backups = []
                ui.notify(f"Failed to list backups: {e}", type="negative")

            if not backups:
                with (
                    backups_container,
                    ui.column().classes(
                        "w-full py-8 items-center justify-center text-slate-400 gap-1"
                    ),
                ):
                    ui.icon("inventory_2", size="lg")
                    ui.label("No configuration backups found.").classes("text-sm")
                return

            with backups_container:
                for b in backups:
                    b_name = b.get("name", "")
                    b_tag = b.get("tag", "Auto Backup")
                    b_time = b.get("formatted_time", "")
                    b_size = b.get("size_bytes", 0)
                    b_is_auto = b.get("is_auto", True)

                    size_kb = f"{b_size / 1024:.1f} KB" if b_size > 0 else f"{b_size} B"
                    tag_c = TAG_AUTO_CLS if b_is_auto else TAG_SNAP_CLS
                    badge_c = BADGE_AUTO_CLS if b_is_auto else BADGE_SNAP_CLS

                    with ui.element("div").classes(
                        "w-full p-3 rounded-xl bg-slate-950/50 border "
                        "border-white/5 hover:border-indigo-500/30 "
                        "transition-all flex flex-col gap-2"
                    ):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-3"
                        ):
                            with ui.row().classes("items-center gap-3"):
                                with ui.element("div").classes(
                                    "w-8 h-8 rounded-lg flex items-center justify-center "
                                    + tag_c
                                ):
                                    ui.icon(
                                        "auto_mode" if b_is_auto else "bookmark",
                                        size="xs",
                                    )

                                with ui.column().classes("gap-0.5"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(b_time).classes(
                                            "text-sm font-semibold text-slate-200"
                                        )
                                        ui.label(b_tag).classes(
                                            "text-[10px] px-2 py-0.5 rounded-full font-medium "
                                            + badge_c
                                        )
                                    ui.label(f"{b_name} • {size_kb}").classes(
                                        "text-xs font-mono text-slate-400"
                                    )

                            with ui.row().classes("items-center gap-1.5"):
                                if allow_diff:

                                    def make_toggle_diff(
                                        target_name: str,
                                        target_html: ui.html,
                                        btn: ui.button,
                                    ):
                                        def toggle():
                                            if target_html.visible:
                                                target_html.visible = False
                                                target_html.content = ""
                                                btn.props("flat dense")
                                                btn.classes(
                                                    remove=BTN_ACTIVE_CLS,
                                                    add=BTN_INACTIVE_CLS,
                                                )
                                            else:
                                                try:
                                                    diff_lines = (
                                                        callbacks.diff_config_backup(
                                                            target_name
                                                        )
                                                    )
                                                    target_html.content = (
                                                        format_diff_html(diff_lines)
                                                    )
                                                    target_html.visible = True
                                                    btn.props("unelevated dense")
                                                    btn.classes(
                                                        remove=BTN_INACTIVE_CLS,
                                                        add=BTN_ACTIVE_CLS,
                                                    )
                                                except Exception as err:
                                                    ui.notify(
                                                        f"Diff failed: {err}",
                                                        type="negative",
                                                    )

                                        return toggle

                                    diff_btn = (
                                        ui.button("Diff", icon="difference")
                                        .props("flat dense")
                                        .classes(
                                            "text-xs text-cyan-400 hover:bg-cyan-500/10 px-2 py-1"
                                        )
                                        .tooltip(
                                            "Toggle line-by-line diff vs current config"
                                        )
                                    )

                                if on_test is not None:

                                    def make_test_handler(
                                        target_name: str, target_tag: str
                                    ):
                                        async def do_test():
                                            res = on_test(target_name, target_tag)
                                            if inspect.isawaitable(res):
                                                await res

                                        return do_test

                                    ui.button(
                                        "Test",
                                        icon="play_arrow",
                                        on_click=make_test_handler(b_name, b_tag),
                                    ).props("flat dense").classes(
                                        "text-xs text-emerald-400 hover:bg-emerald-500/10 px-2 py-1"
                                    ).tooltip(
                                        "Test this backup configuration against digitizer engine with live camera result"
                                    )

                                if on_restore is not None:

                                    def make_restore_handler(
                                        target_name: str, target_time: str
                                    ):
                                        async def do_restore():
                                            res = on_restore(target_name, target_time)
                                            if inspect.isawaitable(res):
                                                await res

                                        return do_restore

                                    ui.button(
                                        "Restore",
                                        icon="restore",
                                        on_click=make_restore_handler(b_name, b_time),
                                    ).props("unelevated dense").classes(
                                        "text-xs bg-emerald-600/80 hover:bg-emerald-600 text-white px-2.5 py-1"
                                    ).tooltip(
                                        "Restore over config.ini"
                                    )

                                if allow_delete:

                                    def make_delete_handler(
                                        target_name: str, target_time: str
                                    ):
                                        def do_delete():
                                            def on_confirm_delete():
                                                try:
                                                    callbacks.delete_config_backup(
                                                        target_name
                                                    )
                                                    ui.notify(
                                                        f"Deleted backup {target_name}",
                                                        type="positive",
                                                    )
                                                    refresh_backups_list()
                                                    if on_delete is not None:
                                                        on_delete(target_name)
                                                except Exception as err:
                                                    ui.notify(
                                                        f"Delete failed: {err}",
                                                        type="negative",
                                                    )

                                            open_confirm_dialog(
                                                title="Delete Backup?",
                                                message=f"Are you sure you want to permanently delete backup '{target_name}' from {target_time}?",
                                                confirm_label="Delete Backup",
                                                confirm_icon="delete",
                                                color_scheme="rose",
                                                icon="delete_forever",
                                                on_confirm=on_confirm_delete,
                                            )

                                        return do_delete

                                    ui.button(
                                        icon="delete",
                                        on_click=make_delete_handler(b_name, b_time),
                                    ).props(
                                        "flat round dense text-rose-400 aria-label='Delete backup'"
                                    ).tooltip(
                                        "Delete backup permanently"
                                    )

                        if allow_diff:
                            diff_slot = ui.html("").classes("w-full")
                            diff_slot.visible = False
                            diff_btn.on_click(
                                make_toggle_diff(b_name, diff_slot, diff_btn)
                            )

        refresh_backups_list()

    history_dialog.open()
    return history_dialog
