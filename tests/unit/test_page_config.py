from unittest.mock import MagicMock, patch
from gui.page_config import ConfigPage


def test_page_config_init():
    callbacks = MagicMock()
    callbacks.load_config_file.return_value = "[DEFAULT]\nLogLevel = INFO\n"
    callbacks.list_config_backups.return_value = []

    page = ConfigPage(callbacks)
    assert page.txt == "[DEFAULT]\nLogLevel = INFO\n"
    assert page.new_config_saved is False


def test_page_config_show_and_actions():
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
    with patch("gui.page_config.ui"):
        page.show()
