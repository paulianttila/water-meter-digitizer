"""Unit tests for ConfigPage, format_diff_html, section parsing, and configuration management."""

from unittest.mock import MagicMock, patch

from gui.page_config import (
    ConfigPage,
    format_diff_html,
    get_section_icon,
    parse_ini_sections,
)


def test_format_diff_html_scenarios():
    # 1. Empty / no difference
    html_empty = format_diff_html([])
    assert "Identical to current configuration" in html_empty

    # 2. Additions and deletions
    lines = [
        "--- old.ini\n",
        "+++ new.ini\n",
        "@@ -1,2 +1,2 @@\n",
        "- LogLevel = INFO\n",
        "+ LogLevel = DEBUG\n",
        " Section = Main\n",
    ]
    html_diff = format_diff_html(lines)
    assert "text-rose-300" in html_diff
    assert "text-emerald-300" in html_diff
    assert "text-cyan-400" in html_diff
    assert "--- old.ini" in html_diff


def test_parse_ini_sections_and_icons():
    ini_content = """
[TakeImage]
Url = http://192.168.1.10/capture
Rotate = 90

[Meters]
Names = total, sub1

[MQTT]
Host = 192.168.1.5
Port = 1883
"""
    sections = parse_ini_sections(ini_content)
    assert len(sections) == 3
    assert sections[0]["name"] == "TakeImage"
    assert sections[0]["items"]["rotate"] == "90"
    assert sections[1]["name"] == "Meters"
    assert sections[2]["name"] == "MQTT"

    # Test icons
    assert get_section_icon("TakeImage") == "camera_alt"
    assert get_section_icon("Alignment") == "crop_free"
    assert get_section_icon("AnalogReadout") == "speed"
    assert get_section_icon("DigitalReadout") == "pin"
    assert get_section_icon("Meters") == "water_drop"
    assert get_section_icon("MQTT") == "hub"
    assert get_section_icon("Poller") == "schedule"
    assert get_section_icon("ZeroFlowTracker") == "water_damage"
    assert get_section_icon("Logging") == "description"
    assert get_section_icon("HistoricalData") == "show_chart"
    assert get_section_icon("UnknownSection") == "settings"

    # Test broken syntax handling
    broken_sections = parse_ini_sections("[BrokenSection\nKey = Value")
    assert broken_sections == []


def test_page_config_init_and_show():
    callbacks = MagicMock()
    callbacks.load_config_file.return_value = "[TakeImage]\nUrl = http://mock/capture\n"
    callbacks.get_config_version.return_value = 3
    callbacks.list_config_backups.return_value = [
        {
            "name": "config.ini_20260908_120000.bak",
            "path": "/config/backups/config.ini_20260908_120000.bak",
            "timestamp": "2026-09-08T12:00:00",
            "formatted_time": "2026-09-08 12:00:00",
            "size_bytes": 1024,
            "tag": "Auto Backup",
            "is_auto": True,
        }
    ]
    callbacks.diff_config_backup.return_value = [
        "- LogLevel = INFO\n",
        "+ LogLevel = DEBUG\n",
    ]

    page = ConfigPage(callbacks)
    assert page.txt == "[TakeImage]\nUrl = http://mock/capture\n"
    assert page.view_mode == "editor"

    with patch("gui.page_config.ui") as mock_ui:
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock()
        mock_ui.dialog.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()

        page.show()


def test_page_config_editor_actions():
    callbacks = MagicMock()
    callbacks.load_config_file.return_value = "[TakeImage]\nUrl = http://mock/capture\n"
    callbacks.get_config_version.return_value = 1
    callbacks.list_config_backups.return_value = []
    callbacks.undo_last_config.return_value = "config_bak_1"

    page = ConfigPage(callbacks)

    with (
        patch("gui.page_config.ui") as mock_ui,
        patch("gui.page_config.theme_copy_to_clipboard") as mock_clipboard,
    ):
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock()
        mock_ui.dialog.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_textarea = MagicMock()
        mock_textarea.value = page.txt
        mock_ui.textarea.return_value.classes.return_value.props.return_value = (
            mock_textarea
        )

        # Capture button click handlers
        button_handlers = {}

        def fake_button(*args, **kwargs):
            btn = MagicMock()
            if kwargs.get("on_click"):
                handler = kwargs["on_click"]
                name = args[0] if args else kwargs.get("text", "")
                button_handlers[name] = handler
            btn.on = MagicMock()
            btn.classes = MagicMock(return_value=btn)
            btn.props = MagicMock(return_value=btn)
            btn.tooltip = MagicMock(return_value=btn)
            return btn

        mock_ui.button.side_effect = fake_button

        page.show()

        # Verify Copy button triggered theme_copy_to_clipboard
        if "Copy" in button_handlers:
            button_handlers["Copy"]()
            mock_clipboard.assert_called_once_with(
                page.txt,
                notify_message="Configuration copied to clipboard",
            )
