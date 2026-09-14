import configparser
import html
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from configuration import Config
from gui.theme import (
    BADGE_AUTO_CLS,
    BADGE_SNAP_CLS,
    BTN_ACTIVE_CLS,
    BTN_INACTIVE_CLS,
    TAG_AUTO_CLS,
    TAG_SNAP_CLS,
)
from gui.theme import (
    copy_to_clipboard as theme_copy_to_clipboard,
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

    inner = "".join(rows)
    return (
        '<div class="w-full max-h-64 overflow-auto bg-slate-900/95 p-2.5 rounded-lg '
        "border border-white/10 font-mono text-[11px] leading-relaxed select-text "
        f'whitespace-pre-wrap">{inner}</div>'
    )


def parse_ini_sections(text: str) -> list[dict[str, Any]]:
    """Parse raw INI text into structured section dictionaries for visual inspection."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except Exception:
        return []

    sections = []
    for section_name in parser.sections():
        items = dict(parser.items(section_name))
        sections.append(
            {
                "name": section_name,
                "items": items,
                "count": len(items),
            }
        )
    return sections


def get_section_icon(name: str) -> str:
    """Return appropriate icon for config sections."""
    name_lower = name.lower()
    if "image" in name_lower or "camera" in name_lower:
        return "camera_alt"
    if "align" in name_lower or "marker" in name_lower:
        return "crop_free"
    if "analog" in name_lower or "dial" in name_lower:
        return "speed"
    if "digit" in name_lower:
        return "pin"
    if "meter" in name_lower:
        return "water_drop"
    if "mqtt" in name_lower:
        return "hub"
    if "poll" in name_lower or "schedule" in name_lower:
        return "schedule"
    if "leak" in name_lower or "zero" in name_lower:
        return "water_damage"
    if "log" in name_lower:
        return "description"
    if "influx" in name_lower or "history" in name_lower or "historic" in name_lower:
        return "show_chart"
    return "settings"


class ConfigPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.txt = self.callbacks.load_config_file()
        self.new_config_saved = False
        self.view_mode = "editor"  # "editor" or "inspector"

    def show(self) -> None:
        def check_buttons() -> None:
            is_dirty = editor.value != self.txt
            button_save.enabled = is_dirty
            button_use_config.enabled = True

            # Update status bar
            lines_count = len(editor.value.splitlines())
            char_count = len(editor.value)
            size_kb = char_count / 1024.0
            status_lines.text = f"Lines: {lines_count}"
            status_size.text = f"{size_kb:.1f} KB ({char_count} chars)"

            if is_dirty:
                status_dirty.text = "● Unsaved Changes"
                status_dirty.classes(
                    replace="text-amber-400 bg-amber-500/10 border-amber-500/30 font-semibold"
                )
            else:
                status_dirty.text = "✓ Synced with Disk"
                status_dirty.classes(
                    replace="text-emerald-400 bg-emerald-500/10 border-emerald-500/30 font-medium"
                )

            try:
                backups = self.callbacks.list_config_backups()
                button_undo.enabled = len(backups) > 0
            except Exception:
                button_undo.enabled = False

        def save_config() -> None:
            if syntax_check() is True:
                self.callbacks.save_config_file(editor.value)
                self.new_config_saved = True
                ui.notify(
                    "Configuration saved to file (backup created)",
                    type="positive",
                )
            self.txt = editor.value
            check_buttons()

        def load_config() -> None:
            self.txt = self.callbacks.load_config_file()
            editor.value = self.txt
            self.new_config_saved = False
            check_buttons()
            refresh_visual_inspector()
            ui.notify("Configuration reloaded from disk into editor", type="info")

        def show_config() -> None:
            try:
                config = Config()
                config.load_from_string(editor.value)
                j = config.model_dump_json(indent=4)
                with (
                    ui.dialog() as dialog,
                    ui.card().classes(
                        "w-full max-w-4xl p-6 bg-slate-900 "
                        "border border-white/10 rounded-xl"
                    ),
                ):
                    with ui.row().classes("w-full justify-between items-center mb-4"):
                        ui.label("Parsed Configuration (JSON)").classes(
                            "text-h5 font-['Outfit']"
                        )
                        ui.button(icon="close", on_click=dialog.close).props(
                            "flat round dense"
                        )
                    ui.code(j, language="json").classes(
                        "w-full max-h-[70vh] overflow-auto rounded-lg "
                        "bg-slate-950 p-4 border border-white/5"
                    )
                dialog.open()
            except Exception as e:
                ui.notify(f"Syntax error: {e}", type="negative")

        def use_config() -> None:
            if editor.value != self.txt:
                ui.notify(
                    "You have unsaved changes in the editor. Save File first before hot-reloading into runtime.",
                    type="warning",
                )
                return
            self.callbacks.use_config()
            self.new_config_saved = False
            check_buttons()
            ui.notify(
                "Configuration hot-reloaded into runtime services", type="positive"
            )

        def syntax_check() -> bool:
            try:
                config = Config()
                config.load_from_string(editor.value)
                sections = parse_ini_sections(editor.value)
                diag_banner.visible = True
                diag_banner.classes(
                    replace="w-full p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-300"
                )
                diag_icon.name = "check_circle"
                diag_icon.props("color=emerald")
                meter_count = len(getattr(config, "meter_configs", []))
                diag_text.text = (
                    f"✓ Configuration Valid: {len(sections)} sections parsed, "
                    f"{meter_count} meter{'s' if meter_count != 1 else ''} configured."
                )
                ui.notify("Syntax is valid", type="positive")
                check_buttons()
                return True
            except Exception as e:
                diag_banner.visible = True
                diag_banner.classes(
                    replace="w-full p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 flex items-center justify-between text-xs text-rose-300"
                )
                diag_icon.name = "error"
                diag_icon.props("color=rose")
                diag_text.text = f"Syntax Error: {e}"
                ui.notify(f"Syntax error: {e}", type="negative")
                button_save.disable()
                return False

        def undo_config() -> None:
            backups = self.callbacks.list_config_backups()
            if not backups:
                ui.notify("No backup found to revert to", type="warning")
                return

            latest = backups[0]
            with (
                ui.dialog() as undo_dialog,
                ui.card().classes(
                    "w-full max-w-md p-5 bg-slate-900 border border-white/10 "
                    "rounded-2xl gap-4"
                ),
            ):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-amber-500/20 border "
                        "border-amber-500/30 flex items-center justify-center "
                        "text-amber-400"
                    ):
                        ui.icon("undo", size="md")
                    with ui.column().classes("gap-0"):
                        ui.label("Undo Configuration Changes?").classes(
                            "text-base font-bold text-slate-100"
                        )
                        f_time = latest.get("formatted_time", "earlier")
                        ui.label(f"Revert to backup from {f_time}").classes(
                            "text-xs text-slate-400"
                        )
                b_name = latest.get("name", "")
                b_tag = latest.get("tag", "Auto Backup")
                ui.label(
                    f"This will replace active config.ini with '{b_name}' "
                    f"({b_tag}). A safety snapshot will be preserved."
                ).classes("text-sm text-slate-300 leading-relaxed")

                with ui.row().classes("w-full justify-end items-center gap-2 mt-2"):
                    ui.button("Cancel", on_click=undo_dialog.close).props(
                        "flat dense"
                    ).classes("text-slate-300 px-3")

                    def confirm_undo():
                        undo_dialog.close()
                        res = self.callbacks.undo_last_config()
                        if res:
                            load_config()
                            ui.notify(f"Reverted to backup '{res}'", type="positive")
                        else:
                            ui.notify("Undo failed: no backup found", type="negative")

                    ui.button(
                        "Revert Config", icon="history", on_click=confirm_undo
                    ).props("unelevated dense").classes(
                        "bg-gradient-to-r from-amber-600 to-orange-600 "
                        "hover:from-amber-500 hover:to-orange-500 text-white "
                        "font-medium px-4 shadow-md"
                    )
            undo_dialog.open()

        def open_history_dialog() -> None:
            with (
                ui.dialog() as history_dialog,
                ui.card().classes(
                    "w-full max-w-5xl p-6 bg-slate-900 border "
                    "border-white/10 rounded-2xl gap-4"
                ),
            ):
                with ui.row().classes(
                    "w-full justify-between items-center pb-3 "
                    "border-b border-white/10"
                ):
                    with ui.row().classes("items-center gap-3"):
                        with ui.element("div").classes(
                            "w-10 h-10 rounded-xl bg-indigo-500/20 "
                            "border border-indigo-500/30 flex items-center "
                            "justify-center text-indigo-400"
                        ):
                            ui.icon("manage_history", size="md")
                        with ui.column().classes("gap-0"):
                            ui.label("Configuration History").classes(
                                "text-lg font-bold text-slate-100"
                            )
                            ui.label(
                                "Manage automatic backups, snapshots, and "
                                "line-by-line diffs"
                            ).classes("text-xs text-slate-400")
                    ui.button(icon="close", on_click=history_dialog.close).props(
                        "flat round dense"
                    )

                # Snapshot creator bar
                with ui.row().classes(
                    "w-full items-center justify-between p-3 "
                    "rounded-xl bg-slate-950/70 border border-white/10 gap-3"
                ):
                    with ui.row().classes("items-center gap-2 flex-grow"):
                        ui.icon("bookmark_add", color="indigo", size="sm")
                        snapshot_input = (
                            ui.input(
                                placeholder=(
                                    "Snapshot label / description "
                                    "(e.g. Pre-calibration)"
                                )
                            )
                            .props("dense borderless")
                            .classes("w-full text-sm text-slate-200")
                        )

                    def create_snapshot():
                        tag_val = snapshot_input.value.strip()
                        res = self.callbacks.create_config_snapshot(tag=tag_val)
                        if res:
                            snapshot_input.value = ""
                            ui.notify(
                                "Manual snapshot saved",
                                type="positive",
                            )
                            refresh_backups_list()
                        else:
                            ui.notify(
                                "Could not create snapshot",
                                type="negative",
                            )

                    ui.button(
                        "Take Snapshot",
                        icon="camera",
                        on_click=create_snapshot,
                    ).props("unelevated dense").classes(
                        "bg-indigo-600 hover:bg-indigo-500 text-white "
                        "text-xs font-medium px-3 py-1 shadow"
                    )

                # Container for backups list
                backups_container = ui.column().classes(
                    "w-full gap-2 max-h-[55vh] overflow-y-auto pr-1"
                )

                def refresh_backups_list():
                    backups_container.clear()
                    try:
                        backups = self.callbacks.list_config_backups()
                    except Exception as e:
                        backups = []
                        ui.notify(
                            f"Failed to list backups: {e}",
                            type="negative",
                        )

                    if not backups:
                        with (
                            backups_container,
                            ui.column().classes(
                                "w-full py-8 items-center "
                                "justify-center text-slate-400 gap-1"
                            ),
                        ):
                            ui.icon("inventory_2", size="lg")
                            ui.label("No configuration backups found yet.").classes(
                                "text-sm"
                            )
                        return

                    with backups_container:
                        for b in backups:
                            b_name = b.get("name", "")
                            b_tag = b.get("tag", "Auto Backup")
                            b_time = b.get("formatted_time", "")
                            b_size = b.get("size_bytes", 0)
                            b_is_auto = b.get("is_auto", True)

                            size_kb = (
                                f"{b_size / 1024:.1f} KB"
                                if b_size > 0
                                else f"{b_size} B"
                            )
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
                                            "w-8 h-8 rounded-lg flex "
                                            "items-center justify-center " + tag_c
                                        ):
                                            ui.icon(
                                                (
                                                    "auto_mode"
                                                    if b_is_auto
                                                    else "bookmark"
                                                ),
                                                size="xs",
                                            )

                                        with ui.column().classes("gap-0.5"):
                                            with ui.row().classes("items-center gap-2"):
                                                ui.label(b_time).classes(
                                                    "text-sm font-semibold "
                                                    "text-slate-200"
                                                )
                                                ui.label(b_tag).classes(
                                                    "text-[10px] px-2 py-0.5 "
                                                    "rounded-full font-medium "
                                                    + badge_c
                                                )
                                            ui.label(f"{b_name} • {size_kb}").classes(
                                                "text-xs font-mono text-slate-400"
                                            )

                                    with ui.row().classes("items-center gap-1.5"):

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
                                                        diff_fn = (
                                                            self.callbacks.diff_config_backup
                                                        )
                                                        diff_lines = diff_fn(
                                                            target_name
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
                                                    except Exception as e:
                                                        ui.notify(
                                                            f"Diff failed: {e}",
                                                            type="negative",
                                                        )

                                            return toggle

                                        diff_btn = (
                                            ui.button(
                                                "Diff",
                                                icon="difference",
                                            )
                                            .props("flat dense")
                                            .classes(
                                                "text-xs text-cyan-400 "
                                                "hover:bg-cyan-500/10 px-2 py-1"
                                            )
                                            .tooltip(
                                                "Toggle line-by-line diff vs "
                                                "current config"
                                            )
                                        )

                                        def make_restore_handler(
                                            target_name: str,
                                            target_time: str,
                                        ):
                                            def do_restore():
                                                try:
                                                    self.callbacks.restore_config_backup(
                                                        target_name
                                                    )
                                                    load_config()
                                                    history_dialog.close()
                                                    ui.notify(
                                                        "Restored config "
                                                        f"from {target_time}",
                                                        type="positive",
                                                    )
                                                except Exception as e:
                                                    ui.notify(
                                                        f"Restore failed: {e}",
                                                        type="negative",
                                                    )

                                            return do_restore

                                        ui.button(
                                            "Restore",
                                            icon="restore",
                                            on_click=make_restore_handler(
                                                b_name, b_time
                                            ),
                                        ).props("unelevated dense").classes(
                                            "text-xs bg-emerald-600/80 "
                                            "hover:bg-emerald-600 text-white "
                                            "px-2.5 py-1"
                                        ).tooltip(
                                            "Restore over config.ini"
                                        )

                                        def make_delete_handler(
                                            target_name: str,
                                        ):
                                            def do_delete():
                                                del_func = (
                                                    self.callbacks.delete_config_backup
                                                )
                                                deleted = del_func(target_name)
                                                if deleted:
                                                    ui.notify(
                                                        "Backup deleted",
                                                        type="info",
                                                    )
                                                    refresh_backups_list()
                                                else:
                                                    ui.notify(
                                                        "Could not delete "
                                                        f"{target_name}",
                                                        type="negative",
                                                    )

                                            return do_delete

                                        ui.button(
                                            icon="delete",
                                            on_click=make_delete_handler(b_name),
                                        ).props("flat round dense").classes(
                                            "text-slate-500 "
                                            "hover:text-rose-400 "
                                            "hover:bg-rose-500/10"
                                        ).tooltip(
                                            "Delete backup"
                                        )

                                # Inline diff container
                                diff_html = ui.html().classes(
                                    "w-full pt-1 border-t border-white/10"
                                )
                                diff_html.visible = False

                                diff_btn.on(
                                    "click",
                                    make_toggle_diff(
                                        b_name,
                                        diff_html,
                                        diff_btn,
                                    ),
                                )

                refresh_backups_list()

            history_dialog.open()

        def copy_to_clipboard() -> None:
            theme_copy_to_clipboard(
                editor.value,
                notify_message="Configuration copied to clipboard",
            )

        def download_config() -> None:
            ui.download(editor.value.encode("utf-8"), filename="config.ini")
            ui.notify("Downloading config.ini", type="info")

        def switch_view(mode: str) -> None:
            self.view_mode = mode
            if mode == "editor":
                editor_container.visible = True
                inspector_container.visible = False
                btn_mode_editor.props("unelevated color=cyan-8").classes(
                    replace="text-white"
                )
                btn_mode_inspector.props("flat color=grey-4").classes(
                    replace="text-slate-400"
                )
            else:
                editor_container.visible = False
                inspector_container.visible = True
                btn_mode_editor.props("flat color=grey-4").classes(
                    replace="text-slate-400"
                )
                btn_mode_inspector.props("unelevated color=cyan-8").classes(
                    replace="text-white"
                )
                refresh_visual_inspector()

        def refresh_visual_inspector() -> None:
            inspector_cards_container.clear()
            sections = parse_ini_sections(editor.value)
            if not sections:
                with (
                    inspector_cards_container,
                    ui.column().classes("w-full py-12 items-center justify-center"),
                ):
                    ui.icon("warning", size="xl", color="amber")
                    ui.label("Unable to parse sections from current text").classes(
                        "text-slate-400 text-sm mt-2"
                    )
                return

            with inspector_cards_container:
                for sec in sections:
                    s_name = sec["name"]
                    s_items = sec["items"]
                    s_icon = get_section_icon(s_name)

                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/90 border border-white/10 rounded-xl flex flex-col gap-2"
                    ):
                        with ui.row().classes(
                            "w-full justify-between items-center pb-2 border-b border-white/5"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                with ui.element("div").classes(
                                    "w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400"
                                ):
                                    ui.icon(s_icon, size="xs")
                                ui.label(f"[{s_name}]").classes(
                                    "font-mono font-bold text-sm text-cyan-300"
                                )
                            ui.label(f"{len(s_items)} parameters").classes(
                                "text-[11px] px-2 py-0.5 rounded-full bg-white/5 text-slate-400 border border-white/10"
                            )

                        with ui.column().classes("w-full gap-1.5 pt-1"):
                            for k, v in s_items.items():
                                with ui.row().classes(
                                    "w-full justify-between items-center text-xs py-1 px-2 rounded bg-slate-950/60 border border-white/5 font-mono"
                                ):
                                    ui.label(k).classes("text-slate-300 font-semibold")
                                    ui.label(str(v)).classes(
                                        "text-cyan-400 truncate max-w-md select-all"
                                    )

        with ui.column().classes(
            "w-full h-full flex flex-col gap-2.5 p-4 overflow-hidden"
        ):
            # Header Row
            with ui.row().classes("w-full justify-between items-center shrink-0"):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 "
                        "flex items-center justify-center shadow-lg shadow-cyan-500/10"
                    ):
                        ui.icon("build", color="cyan").classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label("Configuration Editor").classes("text-h4")
                        ui.label(
                            "Manage system parameters, calibration constants, and service hot-reloading"
                        ).classes("text-xs text-slate-400")

                with ui.row().classes("items-center gap-2"):
                    # Mode switcher
                    with ui.row().classes(
                        "p-1 rounded-xl bg-slate-900 border border-white/10 items-center gap-1"
                    ):
                        btn_mode_editor = ui.button(
                            "Raw INI",
                            icon="code",
                            on_click=lambda: switch_view("editor"),
                        ).props("unelevated dense size=sm color=cyan-8")
                        btn_mode_inspector = ui.button(
                            "Visual Explorer",
                            icon="dashboard_customize",
                            on_click=lambda: switch_view("inspector"),
                        ).props("flat dense size=sm color=grey-4")

                    ui.label("config.ini").classes(
                        "font-mono text-xs text-cyan-400 bg-cyan-500/10 "
                        "border border-cyan-500/30 px-3 py-1.5 rounded-full font-semibold"
                    )

            # Toolbar Row
            with ui.row().classes(
                "w-full items-center justify-between gap-3 p-2.5 "
                "rounded-xl bg-slate-900/80 border border-white/10 shrink-0"
            ):
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    ui.button(
                        "Reload File", icon="file_download", on_click=load_config
                    ).props("outline color=grey-4 size=sm").tooltip(
                        "Discard editor changes and reload config.ini file from disk"
                    )
                    ui.button("Validate", icon="verified", on_click=syntax_check).props(
                        "outline color=cyan size=sm"
                    ).tooltip("Validate INI syntax and configuration structure")
                    button_save = (
                        ui.button("Save File", icon="save", on_click=save_config)
                        .props("unelevated color=primary size=sm")
                        .tooltip(
                            "Save editor changes to config.ini file on disk (creates auto-backup)"
                        )
                    )
                    button_undo = (
                        ui.button("Undo", icon="undo", on_click=undo_config)
                        .props("outline color=amber size=sm")
                        .tooltip("Revert config.ini to the last snapshot backup")
                    )
                    button_use_config = (
                        ui.button(
                            "Hot-Reload",
                            icon="bolt",
                            on_click=use_config,
                        )
                        .props("unelevated color=warning size=sm")
                        .classes("text-black font-semibold shadow-sm")
                        .tooltip(
                            "Hot-reload config.ini directly into running services without server restart (zero downtime)"
                        )
                    )

                with ui.row().classes("items-center gap-2 flex-wrap"):
                    ui.button(
                        "Snapshots & Diffs",
                        icon="manage_history",
                        on_click=open_history_dialog,
                    ).props("outline color=indigo size=sm").tooltip(
                        "Manage configuration snapshots and visual line diffs"
                    )
                    ui.button(
                        "Copy", icon="content_copy", on_click=copy_to_clipboard
                    ).props("flat color=grey-4 size=sm").tooltip(
                        "Copy configuration to clipboard"
                    )
                    ui.button(
                        "Download", icon="download", on_click=download_config
                    ).props("flat color=grey-4 size=sm").tooltip(
                        "Download config.ini file"
                    )
                    ui.button(
                        "Inspect JSON", icon="preview", on_click=show_config
                    ).props("flat color=grey-4 size=sm").tooltip(
                        "Inspect parsed configuration structure as JSON"
                    )

            # Validation Diagnostics Banner (collapsible)
            with (
                ui.row()
                .classes(
                    "w-full p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 "
                    "items-center justify-between text-xs text-emerald-300 shrink-0"
                )
                .props('id="config-diag-banner"') as diag_banner
            ):
                diag_banner.visible = False
                with ui.row().classes("items-center gap-2 flex-1 min-w-0"):
                    diag_icon = ui.icon("check_circle", color="emerald", size="sm")
                    diag_text = ui.label("Syntax is valid").classes(
                        "font-medium truncate"
                    )
                ui.button(
                    icon="close",
                    on_click=lambda: diag_banner.set_visibility(False),
                ).props("flat round dense size=xs text-color=grey-4")

            # Main Content Containers
            # 1. Raw INI Editor Container
            with (
                ui.element("div")
                .classes(
                    "w-full flex-1 min-h-[300px] rounded-xl bg-slate-950 p-3 "
                    "border border-white/10 flex flex-col overflow-hidden"
                )
                .props('id="editor-container"') as editor_container
            ):
                editor = (
                    ui.textarea(
                        value=self.callbacks.load_config_file(),
                        on_change=check_buttons,
                    )
                    .classes("w-full h-full config-editor-field font-mono text-sm")
                    .props("borderless")
                )

            # 2. Visual Section Inspector Container
            with (
                ui.column()
                .classes("w-full flex-1 overflow-y-auto pr-1 gap-3")
                .props('id="inspector-container"') as inspector_container
            ):
                inspector_container.visible = False
                inspector_cards_container = ui.column().classes(
                    "w-full gap-3 max-w-5xl"
                )

            # Status & Telemetry Bar
            with ui.row().classes(
                "w-full items-center justify-between px-3 py-1.5 rounded-lg "
                "bg-slate-900/60 border border-white/5 text-xs text-slate-400 shrink-0 select-none"
            ):
                with ui.row().classes("items-center gap-3"):
                    status_dirty = ui.label("✓ Synced with Disk").classes(
                        "px-2 py-0.5 rounded text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 font-medium"
                    )
                    status_lines = ui.label("Lines: 0").classes("font-mono")
                    status_size = ui.label("0 KB").classes("font-mono")

                with ui.row().classes("items-center gap-3"):
                    version_num = self.callbacks.get_config_version()
                    ui.label(f"Runtime Version #{version_num}").classes(
                        "text-slate-400 font-mono text-[11px]"
                    )
                    ui.label("/config/config.ini").classes(
                        "font-mono text-cyan-400/80 text-[11px]"
                    )

            check_buttons()
