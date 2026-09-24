"""Unit tests for services.config_file_service.ConfigFileService."""

import configparser
from unittest.mock import MagicMock, patch

import pytest

from services.config_file_service import ConfigFileService


def test_config_file_service_load(tmp_path):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[DEFAULT]\nLogLevel = INFO\n", encoding="utf-8")

    service = ConfigFileService(str(cfg_file))
    assert service.config_file == str(cfg_file)
    assert "LogLevel = INFO" in service.load()


def test_config_file_service_callable_config_file(tmp_path):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[DEFAULT]\nLogLevel = DEBUG\n", encoding="utf-8")

    current_path = str(cfg_file)
    service = ConfigFileService(lambda: current_path)
    assert service.config_file == current_path
    assert "LogLevel = DEBUG" in service.load()


def test_config_file_service_save_valid(tmp_path):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[DEFAULT]\nLogLevel = INFO\n", encoding="utf-8")

    service = ConfigFileService(str(cfg_file))
    with patch("config_history.ConfigHistoryManager.create_backup") as mock_backup:
        service.save("[DEFAULT]\nLogLevel = WARNING\n")
        mock_backup.assert_called_once_with(str(cfg_file.resolve()))

    assert "LogLevel = WARNING" in cfg_file.read_text(encoding="utf-8")


def test_config_file_service_save_invalid_syntax(tmp_path):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[DEFAULT]\nLogLevel = INFO\n", encoding="utf-8")

    service = ConfigFileService(str(cfg_file))
    with pytest.raises(configparser.Error):
        service.save("INVALID_SYNTAX_WITHOUT_SECTION_OR_KEY")

    # Original file is preserved
    assert "LogLevel = INFO" in cfg_file.read_text(encoding="utf-8")


def test_config_file_service_backup_operations(tmp_path):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[DEFAULT]\nLogLevel = INFO\n", encoding="utf-8")

    service = ConfigFileService(str(cfg_file))

    with patch("config_history.ConfigHistoryManager") as MockMgr:
        mock_entry = MagicMock()
        mock_entry.model_dump.return_value = {"name": "backup1.bak"}
        MockMgr.list_backups.return_value = [mock_entry]
        MockMgr.undo_last.return_value = "backup1.bak"
        MockMgr.create_backup.return_value = "snap.bak"
        MockMgr.delete_backup.return_value = True
        MockMgr.get_diff.return_value = ["+ diff line\n"]
        MockMgr.get_backup_content.return_value = "[DEFAULT]\nOld=1\n"

        assert service.list_backups() == [{"name": "backup1.bak"}]
        MockMgr.list_backups.assert_called_once_with(str(cfg_file))

        service.restore_backup("backup1.bak")
        MockMgr.restore_backup.assert_called_once_with(str(cfg_file), "backup1.bak")

        assert service.undo_last() == "backup1.bak"
        assert service.create_snapshot("manual_tag") == "snap.bak"
        MockMgr.create_backup.assert_called_with(str(cfg_file), tag="manual_tag")

        assert service.delete_backup("backup1.bak") is True
        assert service.diff_backup("backup1.bak") == ["+ diff line\n"]
        assert service.load_backup("backup1.bak") == "[DEFAULT]\nOld=1\n"
