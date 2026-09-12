"""Unit tests for ConfigPage, format_diff_html, and configuration management."""

from unittest.mock import MagicMock, patch

from gui.page_config import ConfigPage, format_diff_html


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


def test_page_config_init_and_show():
    callbacks = MagicMock()
    callbacks.load_config_file.return_value = "[DEFAULT]\nLogLevel = INFO\n"
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
    assert page.txt == "[DEFAULT]\nLogLevel = INFO\n"

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
    callbacks.load_config_file.return_value = "[DEFAULT]\nLogLevel = INFO\n"
    callbacks.list_config_backups.return_value = []
    callbacks.undo_last_config.return_value = "config_bak_1"

    page = ConfigPage(callbacks)

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
