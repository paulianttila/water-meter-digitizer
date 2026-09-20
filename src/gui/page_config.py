import configparser
import logging
import re
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from configuration import Config
from gui.components import (
    open_code_inspect_dialog,
    open_config_history_dialog,
    open_confirm_dialog,
    page_header,
    run_engine_test_dialog,
)
from gui.theme import (
    DIALOG_HEADER_ROW,
    ROW_ACTIONS,
    ROW_HEADER,
)
from gui.theme import (
    copy_to_clipboard as theme_copy_to_clipboard,
)

logger = logging.getLogger(__name__)

FIELD_SCHEMAS: dict[tuple[str, str], dict[str, Any]] = {
    # [DEFAULT]
    ("default", "loglevel"): {
        "type": "select",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "description": "Log level for the application",
    },
    ("default", "minconfidencethreshold"): {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "step": 1.0,
        "description": "Minimum CNN prediction confidence %",
    },
    # [ImageSource]
    ("imagesource", "timeout"): {
        "type": "int",
        "min": 1,
        "max": 300,
        "step": 1,
        "description": "Image fetch timeout in seconds",
    },
    ("imagesource", "minsize"): {
        "type": "int",
        "min": 0,
        "step": 1000,
        "description": "Minimum image file size in bytes",
    },
    # [Alignment]
    ("alignment", "rotationangle"): {
        "type": "select",
        "options": ["0", "90", "180", "270"],
        "description": "Initial coarse rotation angle (deg)",
    },
    ("alignment", "postrotationangle"): {
        "type": "float",
        "min": -180.0,
        "max": 180.0,
        "step": 0.1,
        "description": "Fine-tuning rotation angle after alignment",
    },
    # [Digits], [Analog]
    ("digits", "model"): {
        "type": "select",
        "options": ["digital100", "digital", "analog100", "analog", "auto"],
        "description": "CNN inference model for digits",
    },
    ("analog", "model"): {
        "type": "select",
        "options": ["analog100", "analog", "digital100", "digital", "auto"],
        "description": "CNN inference model for analog needles",
    },
    # [ImageProcessing]
    ("imageprocessing", "contrast"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "brightness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "color"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "sharpness"): {
        "type": "float",
        "min": 0.0,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "gamma"): {
        "type": "float",
        "min": 0.1,
        "max": 5.0,
        "step": 0.1,
    },
    ("imageprocessing", "grayscale"): {"type": "boolean"},
    ("imageprocessing", "sharpnessmode"): {
        "type": "select",
        "options": ["standard", "unsharp_mask", "auto"],
        "description": "Sharpening filter mode",
    },
    ("imageprocessing", "unsharpradius"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
    },
    ("imageprocessing", "unsharpamount"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
    },
    ("imageprocessing", "unsharpthreshold"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
    },
    ("imageprocessing", "glaresuppressionmode"): {
        "type": "select",
        "options": ["clahe", "inpaint", "illumination_normalize", "combined"],
        "description": "Hotspot glare mitigation mode",
    },
    ("imageprocessing", "glareinpaintthreshold"): {
        "type": "int",
        "min": 0,
        "max": 255,
        "step": 1,
    },
    ("imageprocessing", "glareinpaintradius"): {
        "type": "int",
        "min": 1,
        "max": 50,
        "step": 1,
    },
    ("imageprocessing", "glareclahecliplimit"): {
        "type": "float",
        "min": 0.1,
        "max": 10.0,
        "step": 0.5,
    },
    ("imageprocessing", "glareclahegridsize"): {
        "type": "int",
        "min": 2,
        "max": 64,
        "step": 1,
    },
    # [History]
    ("history", "backend"): {
        "type": "select",
        "options": ["sqlite", "memory"],
        "description": "Storage backend engine",
    },
    ("history", "maxmemorymb"): {
        "type": "float",
        "min": 1.0,
        "step": 5.0,
    },
    ("history", "maxrecords"): {
        "type": "int",
        "min": 100,
        "step": 1000,
    },
    ("history", "retentiondays"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    ("history", "pruneinterval"): {
        "type": "int",
        "min": 1,
        "step": 10,
    },
    # [Snapshots]
    ("snapshots", "mode"): {
        "type": "select",
        "options": [
            "smart_tiered",
            "change_only",
            "roi_strips_only",
            "full_frames",
            "disabled",
        ],
        "description": "Storage tiering policy",
    },
    ("snapshots", "format"): {
        "type": "select",
        "options": ["webp", "jpeg"],
        "description": "Image encoding format",
    },
    ("snapshots", "quality"): {
        "type": "int",
        "min": 1,
        "max": 100,
        "step": 5,
        "description": "Encoding quality (1-100)",
    },
    ("snapshots", "maxdiskmb"): {
        "type": "float",
        "min": 10.0,
        "step": 50.0,
        "description": "Max disk storage quota in MB",
    },
    ("snapshots", "recentfullframedays"): {
        "type": "int",
        "min": 0,
        "step": 1,
    },
    ("snapshots", "roistripretentiondays"): {
        "type": "int",
        "min": 0,
        "step": 1,
    },
    ("snapshots", "idleheartbeatminutes"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    # [Poller]
    ("poller", "intervalseconds"): {
        "type": "int",
        "min": 1,
        "step": 10,
        "description": "Polling interval in seconds",
    },
    ("poller", "retryintervalseconds"): {
        "type": "int",
        "min": 1,
        "step": 5,
    },
    # [MQTT]
    ("mqtt", "port"): {
        "type": "int",
        "min": 1,
        "max": 65535,
        "step": 1,
        "description": "MQTT broker TCP port",
    },
    ("mqtt", "keepalive"): {
        "type": "int",
        "min": 5,
        "max": 3600,
        "step": 5,
    },
    # [ZeroFlowMonitor]
    ("zeroflowmonitor", "valuetype"): {
        "type": "select",
        "options": ["cumulative", "flow_rate"],
        "description": "Zero-flow calculation mode",
    },
    ("zeroflowmonitor", "continuousflowhours"): {
        "type": "float",
        "min": 0.1,
        "step": 0.5,
        "description": "Continuous flow hours before leak alert",
    },
    ("zeroflowmonitor", "minleakvolume"): {
        "type": "float",
        "min": 0.001,
        "step": 0.005,
        "description": "Minimum consumption delta to trigger leak",
    },
    ("zeroflowmonitor", "flowthreshold"): {
        "type": "float",
        "min": 0.0001,
        "step": 0.001,
    },
    ("zeroflowmonitor", "resolvedebouncecount"): {
        "type": "int",
        "min": 1,
        "step": 1,
    },
    ("zeroflowmonitor", "maxhistoryevents"): {
        "type": "int",
        "min": 5,
        "step": 10,
    },
}


def get_field_schema(section: str, key: str, value: str) -> dict[str, Any]:
    """Resolve field schema (type, options, bounds) for section parameter."""
    sec_k = section.lower()
    k_lower = key.lower()
    val_clean = value.strip()

    # Exact section + key match
    if (sec_k, k_lower) in FIELD_SCHEMAS:
        return FIELD_SCHEMAS[(sec_k, k_lower)]

    # Meter.<name> format fields
    if sec_k.startswith("meter."):
        if k_lower in (
            "consistencyenabled",
            "allownegativerates",
            "usepreviousvalue",
            "useextendedresolution",
            "detectnegativesign",
        ):
            return {"type": "boolean"}
        if k_lower == "maxratevalue":
            return {"type": "float", "min": 0.0, "step": 0.1}
        if k_lower == "prevaluefromfilemaxage":
            return {"type": "int", "min": 0, "step": 60}

    # Boolean detection by key name or boolean value string
    if (
        k_lower.endswith("enabled")
        or k_lower.startswith("is")
        or k_lower
        in (
            "autovacuum",
            "grayscale",
            "tls",
            "retain",
            "homeassistantdiscovery",
            "runonstartup",
            "saveimages",
            "alwayssaveonanomaly",
            "applytocutimages",
            "autocontrastcutimagesenabled",
            "autosharpencutimages",
        )
        or val_clean.lower() in ("true", "false")
    ):
        return {"type": "boolean"}

    # Coordinate fields (X, Y, W, H)
    if k_lower in ("x", "y", "w", "h"):
        return {"type": "int", "min": 0, "step": 1}

    # Integer detection
    if re.match(r"^-?\d+$", val_clean):
        return {"type": "int", "step": 1}

    # Float detection
    if re.match(r"^-?\d+\.\d+$", val_clean):
        return {"type": "float", "step": 0.1}

    return {"type": "text"}


def update_ini_value(ini_text: str, section: str, key: str, new_value: str) -> str:
    """Update a specific key in a specific section within raw INI text, preserving comments and formatting."""
    lines = ini_text.splitlines()
    in_target_section = False
    section_pattern = re.compile(r"^\s*\[([^\]]+)\]\s*$")
    key_pattern = re.compile(
        r"^(\s*" + re.escape(key) + r"\s*[:=]\s*)(.*)$", re.IGNORECASE
    )

    found_key = False
    section_start_idx = -1
    section_end_idx = len(lines)

    for i, line in enumerate(lines):
        sec_match = section_pattern.match(line)
        if sec_match:
            sec_name = sec_match.group(1).strip()
            if sec_name.lower() == section.lower():
                in_target_section = True
                section_start_idx = i
                continue
            elif in_target_section:
                section_end_idx = i
                in_target_section = False
                break

        if in_target_section:
            k_match = key_pattern.match(line)
            if k_match:
                prefix = k_match.group(1)
                old_val_part = k_match.group(2)
                comment_match = re.search(r"(\s+[#;].*)$", old_val_part)
                comment_part = comment_match.group(1) if comment_match else ""
                lines[i] = f"{prefix}{new_value}{comment_part}"
                found_key = True
                break

    if not found_key:
        if section_start_idx != -1:
            lines.insert(section_end_idx, f"{key} = {new_value}")
        else:
            lines.append(f"\n[{section}]")
            lines.append(f"{key} = {new_value}")

    return "\n".join(lines)


def parse_ini_sections(text: str) -> list[dict[str, Any]]:
    """Parse raw INI text into structured section dictionaries for visual inspection."""
    parser = configparser.ConfigParser(
        interpolation=None,
        default_section="",
        inline_comment_prefixes=("#", ";"),
    )
    parser.optionxform = str  # type: ignore[method-assign,assignment]
    try:
        parser.read_string(text)
    except Exception:
        logger.warning("Failed to parse INI sections", exc_info=True)
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
    if "default" in name_lower:
        return "tune"
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
                logger.debug("Could not list config backups", exc_info=True)
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
                open_code_inspect_dialog(
                    title="Parsed Configuration (JSON)",
                    code_content=j,
                    language="json",
                )
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

        async def test_config() -> None:
            try:
                config = Config()
                config.load_from_string(editor.value)
            except Exception as e:
                ui.notify(f"Cannot test invalid configuration: {e}", type="negative")
                return

            await run_engine_test_dialog(
                config=config,
                callbacks=self.callbacks,
                title_tag="Config Editor",
            )

        def undo_config() -> None:
            backups = self.callbacks.list_config_backups()
            if not backups:
                ui.notify("No backup found to revert to", type="warning")
                return

            latest = backups[0]
            f_time = latest.get("formatted_time", "earlier")
            b_name = latest.get("name", "")
            b_tag = latest.get("tag", "Auto Backup")

            def confirm_undo():
                res = self.callbacks.undo_last_config()
                if res:
                    load_config()
                    ui.notify(f"Reverted to backup '{res}'", type="positive")
                else:
                    ui.notify("Undo failed: no backup found", type="negative")

            open_confirm_dialog(
                title="Undo Configuration Changes?",
                subtitle=f"Revert to backup from {f_time}",
                message=(
                    f"This will replace active config.ini with '{b_name}' "
                    f"({b_tag}). A safety snapshot will be preserved."
                ),
                confirm_label="Revert Config",
                confirm_icon="history",
                color_scheme="amber",
                icon="undo",
                on_confirm=confirm_undo,
            )

        def open_history_dialog() -> None:
            def on_restore(target_name: str, target_time: str) -> None:
                try:
                    self.callbacks.restore_config_backup(target_name)
                    load_config()
                    ui.notify(
                        f"Restored config from {target_time}",
                        type="positive",
                    )
                except Exception as e:
                    ui.notify(f"Restore failed: {e}", type="negative")

            async def on_test(target_name: str, target_tag: str) -> None:
                try:
                    content = self.callbacks.load_config_backup(target_name)
                    if not content:
                        ui.notify(
                            f"Could not load backup '{target_name}'",
                            type="negative",
                        )
                        return
                    b_cfg = Config()
                    b_cfg.load_from_string(content)
                    await run_engine_test_dialog(
                        config=b_cfg,
                        callbacks=self.callbacks,
                        title_tag=f"Snapshot: {target_tag}",
                    )
                except Exception as e:
                    ui.notify(f"Test failed: {e}", type="negative")

            open_config_history_dialog(
                callbacks=self.callbacks,
                title="Configuration History",
                subtitle="Manage automatic backups, snapshots, and line-by-line diffs",
                show_snapshot_creator=True,
                on_restore=on_restore,
                on_test=on_test,
                allow_diff=True,
                allow_delete=True,
            )

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

            query = (search_filter.value or "").strip().lower()

            def on_field_change(sec_name: str, key_name: str, new_val: Any) -> None:
                if isinstance(new_val, bool):
                    val_str = "true" if new_val else "false"
                elif new_val is None:
                    val_str = ""
                else:
                    val_str = str(new_val).strip()
                editor.value = update_ini_value(
                    editor.value, sec_name, key_name, val_str
                )
                check_buttons()

            rendered_count = 0
            with inspector_cards_container:
                for sec in sections:
                    s_name = sec["name"]
                    s_items = sec["items"]
                    s_icon = get_section_icon(s_name)

                    matching_items = {}
                    for k, v in s_items.items():
                        if (
                            not query
                            or query in s_name.lower()
                            or query in k.lower()
                            or query in str(v).lower()
                        ):
                            matching_items[k] = v

                    if query and not matching_items and query not in s_name.lower():
                        continue

                    rendered_count += 1
                    items_to_render = matching_items if query else s_items

                    with ui.card().classes(
                        "w-full p-4 bg-slate-900/90 border border-white/10 rounded-xl flex flex-col gap-2 shadow-sm"
                    ):
                        with ui.row().classes(DIALOG_HEADER_ROW):
                            with ui.row().classes(ROW_ACTIONS):
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

                        with ui.column().classes("w-full gap-2 pt-1"):
                            for k, v in items_to_render.items():
                                schema = get_field_schema(s_name, k, str(v))
                                f_type = schema.get("type", "text")
                                f_desc = schema.get("description", "")

                                with ui.row().classes(
                                    f"{ROW_HEADER} text-xs py-1.5 px-3 rounded-lg bg-slate-950/60 border border-white/5 font-mono gap-3"
                                ):
                                    with ui.column().classes(
                                        "gap-0 min-w-[160px] max-w-sm shrink-0"
                                    ):
                                        ui.label(k).classes(
                                            "text-slate-200 font-semibold text-xs"
                                        )
                                        if f_desc:
                                            ui.label(f_desc).classes(
                                                "text-[10px] text-slate-400 font-normal truncate max-w-xs"
                                            )

                                    with ui.row().classes(
                                        "items-center justify-end flex-1"
                                    ):
                                        if f_type == "select":
                                            opts = list(schema.get("options", []))
                                            cur_val = str(v).strip()
                                            matching_opt = next(
                                                (
                                                    o
                                                    for o in opts
                                                    if o.lower() == cur_val.lower()
                                                ),
                                                None,
                                            )
                                            val_to_use = (
                                                matching_opt
                                                if matching_opt is not None
                                                else cur_val
                                            )
                                            if val_to_use not in opts:
                                                opts.append(val_to_use)
                                            ui.select(
                                                options=opts,
                                                value=val_to_use,
                                                on_change=lambda e, s=s_name, key=k: on_field_change(
                                                    s, key, e.value
                                                ),
                                            ).props(
                                                "dense outlined options-dense"
                                            ).classes(
                                                "w-44 text-xs bg-slate-900 text-cyan-400"
                                            )
                                        elif f_type == "boolean":
                                            is_checked = str(v).strip().lower() in (
                                                "true",
                                                "1",
                                                "yes",
                                                "on",
                                            )
                                            ui.switch(
                                                value=is_checked,
                                                on_change=lambda e, s=s_name, key=k: on_field_change(
                                                    s, key, e.value
                                                ),
                                            ).props("dense color=cyan").classes(
                                                "scale-90"
                                            )
                                        elif f_type == "int":
                                            try:
                                                int_val = int(str(v).strip())
                                            except ValueError:
                                                int_val = 0
                                            ui.number(
                                                value=int_val,
                                                min=schema.get("min"),
                                                max=schema.get("max"),
                                                step=schema.get("step", 1),
                                                on_change=lambda e, s=s_name, key=k: on_field_change(
                                                    s,
                                                    key,
                                                    (
                                                        int(e.value)
                                                        if e.value is not None
                                                        else 0
                                                    ),
                                                ),
                                            ).props("dense outlined").classes(
                                                "w-32 text-xs bg-slate-900 text-cyan-400 font-mono"
                                            )
                                        elif f_type == "float":
                                            try:
                                                float_val = float(str(v).strip())
                                            except ValueError:
                                                float_val = 0.0
                                            ui.number(
                                                value=float_val,
                                                min=schema.get("min"),
                                                max=schema.get("max"),
                                                step=schema.get("step", 0.1),
                                                on_change=lambda e, s=s_name, key=k: on_field_change(
                                                    s,
                                                    key,
                                                    (
                                                        float(e.value)
                                                        if e.value is not None
                                                        else 0.0
                                                    ),
                                                ),
                                            ).props("dense outlined").classes(
                                                "w-32 text-xs bg-slate-900 text-cyan-400 font-mono"
                                            )
                                        else:
                                            ui.input(
                                                value=str(v),
                                                on_change=lambda e, s=s_name, key=k: on_field_change(
                                                    s, key, e.value
                                                ),
                                            ).props("dense outlined").classes(
                                                "w-72 max-w-full text-xs bg-slate-900 text-cyan-400 font-mono"
                                            )

            if query and rendered_count == 0:
                with (
                    inspector_cards_container,
                    ui.column().classes(
                        "w-full py-8 items-center justify-center text-slate-400 gap-1"
                    ),
                ):
                    ui.icon("search_off", size="lg")
                    ui.label(f'No configuration parameters match "{query}"').classes(
                        "text-xs"
                    )

        with ui.column().classes(
            "w-full h-full flex flex-col gap-2.5 p-4 overflow-hidden"
        ):
            # Header Row
            with page_header(
                title="Configuration Editor",
                subtitle="Manage system parameters, calibration constants, and service hot-reloading",
                icon="build",
                color="cyan",
                classes="w-full justify-between items-center shrink-0",
            ):
                # Mode switcher
                with ui.row().classes(
                    "p-1 rounded-xl bg-slate-900 border border-white/10 items-center gap-1"
                ):
                    btn_mode_editor = ui.button(
                        "Raw INI",
                        icon="code",
                        on_click=lambda: switch_view("editor"),
                    ).props("unelevated dense size=sm color=cyan-8")
                    btn_mode_inspector = (
                        ui.button(
                            "Visual Editor",
                            icon="tune",
                            on_click=lambda: switch_view("inspector"),
                        )
                        .props("flat dense size=sm color=grey-4")
                        .tooltip(
                            "Switch to visual parameter editor with choice dropdowns and toggles"
                        )
                    )

                ui.label("config.ini").classes(
                    "font-mono text-xs text-cyan-400 bg-cyan-500/10 "
                    "border border-cyan-500/30 px-3 py-1.5 rounded-full font-semibold"
                )

            # Toolbar Row
            with ui.row().classes(
                f"{ROW_HEADER} gap-3 p-2.5 "
                "rounded-xl bg-slate-900/80 border border-white/10 shrink-0"
            ):
                with ui.row().classes(f"{ROW_ACTIONS} flex-wrap"):
                    ui.button(
                        "Reload File", icon="file_download", on_click=load_config
                    ).props("outline color=grey-4 size=sm").tooltip(
                        "Discard editor changes and reload config.ini file from disk"
                    )
                    ui.button("Validate", icon="verified", on_click=syntax_check).props(
                        "outline color=cyan size=sm"
                    ).tooltip("Validate INI syntax and configuration structure")
                    ui.button(
                        "Test Config", icon="play_arrow", on_click=test_config
                    ).props("outline color=emerald size=sm").tooltip(
                        "Test configuration against digitizer engine and inspect recognition results"
                    )
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

                with ui.row().classes(f"{ROW_ACTIONS} flex-wrap"):
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
                with ui.row().classes(f"{ROW_ACTIONS} flex-1 min-w-0"):
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

            # 2. Visual Section Editor Container
            with (
                ui.column()
                .classes("w-full flex-1 overflow-y-auto pr-1 gap-3")
                .props('id="inspector-container"') as inspector_container
            ):
                inspector_container.visible = False
                with ui.row().classes(
                    "w-full max-w-5xl items-center justify-between gap-3 shrink-0"
                ):
                    search_filter = (
                        ui.input(
                            placeholder="Filter sections or parameters (e.g. MQTT, LogLevel, Mode)...",
                            on_change=lambda: refresh_visual_inspector(),
                        )
                        .props("dense outlined clearable rounded")
                        .classes("w-full bg-slate-900/90 text-xs text-slate-200")
                    )
                inspector_cards_container = ui.column().classes(
                    "w-full gap-3 max-w-5xl"
                )

            # Status & Telemetry Bar
            with ui.row().classes(
                f"{ROW_HEADER} px-3 py-1.5 rounded-lg "
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
