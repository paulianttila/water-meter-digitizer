import os
from pathlib import Path

import pytest

from config_history import BackupEntry, ConfigHistoryManager


@pytest.fixture
def temp_config_dir(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.ini"
    cfg_file.write_text(
        "[DEFAULT]\nLogLevel = INFO\n[ImageSource]\nURL = http://camera/image.jpg\n"
    )
    return cfg_dir, cfg_file


def test_create_and_list_backup(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None
    assert os.path.exists(backup_path)
    assert "/backups/" in backup_path
    assert backup_path.endswith(".bak")

    backups = ConfigHistoryManager.list_backups(str(cfg_file))
    assert len(backups) == 1
    b = backups[0]
    assert isinstance(b, BackupEntry)
    assert b.is_auto is True
    assert b.tag == "Auto Backup"
    assert b.size_bytes > 0
    assert "LogLevel = INFO" in Path(b.path).read_text()


def test_create_named_snapshot(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(
        str(cfg_file), tag="Pre Calibration"
    )
    assert backup_path is not None
    assert "Pre_Calibration" in backup_path

    backups = ConfigHistoryManager.list_backups(str(cfg_file))
    assert len(backups) == 1
    assert backups[0].is_auto is False
    assert backups[0].tag == "Pre Calibration"


def test_legacy_backup_discovery(temp_config_dir):
    cfg_dir, cfg_file = temp_config_dir

    # Place a legacy backup directly in cfg_dir
    legacy_file = cfg_dir / "config.ini_20260101_120000.bak"
    legacy_file.write_text("[DEFAULT]\nLogLevel = DEBUG\n")

    backups = ConfigHistoryManager.list_backups(str(cfg_file))
    assert len(backups) == 1
    assert backups[0].name == "config.ini_20260101_120000.bak"


def test_restore_backup(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    # Create initial backup
    backup_path = ConfigHistoryManager.create_backup(str(cfg_file), tag="v1")
    assert backup_path is not None

    # Modify active config
    cfg_file.write_text(
        "[DEFAULT]\nLogLevel = WARNING\n[ImageSource]\nURL = http://new/image.jpg\n"
    )
    assert "LogLevel = WARNING" in cfg_file.read_text()

    # Restore v1 backup
    ConfigHistoryManager.restore_backup(str(cfg_file), backup_path)
    restored_text = cfg_file.read_text()
    assert "LogLevel = INFO" in restored_text
    assert "http://camera/image.jpg" in restored_text

    # Verify a safety snapshot was taken before restore
    backups = ConfigHistoryManager.list_backups(str(cfg_file))
    assert any("before_restore" in b.name for b in backups)


def test_undo_last(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    # Create backup of v1
    b1 = ConfigHistoryManager.create_backup(str(cfg_file), tag="v1")
    assert b1 is not None

    # Save v2
    cfg_file.write_text("[DEFAULT]\nLogLevel = ERROR\n")

    # Undo
    undone_backup = ConfigHistoryManager.undo_last(str(cfg_file))
    assert undone_backup is not None
    assert "LogLevel = INFO" in cfg_file.read_text()


def test_delete_backup(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None
    assert os.path.exists(backup_path)

    backup_name = Path(backup_path).name
    deleted = ConfigHistoryManager.delete_backup(str(cfg_file), backup_name)
    assert deleted is True
    assert not os.path.exists(backup_path)


def test_diff_generation(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None

    current_modified = (
        "[DEFAULT]\nLogLevel = DEBUG\n[ImageSource]\nURL = http://camera/image.jpg\n"
    )
    diff = ConfigHistoryManager.get_diff(
        current_modified, backup_path, config_file=str(cfg_file)
    )
    assert len(diff) > 0
    diff_text = "".join(diff)
    assert "-LogLevel = INFO" in diff_text
    assert "+LogLevel = DEBUG" in diff_text


def test_nonexistent_config_file(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist.ini"
    assert ConfigHistoryManager.create_backup(str(nonexistent)) is None
    assert ConfigHistoryManager.list_backups(str(nonexistent)) == []
    assert ConfigHistoryManager.undo_last(str(nonexistent)) is None


def test_main_diff_config_backup_no_deadlock(temp_config_dir, monkeypatch):
    import main

    _cfg_dir, cfg_file = temp_config_dir
    monkeypatch.setattr(main, "config_file", str(cfg_file))

    # Create a backup
    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None
    backup_name = Path(backup_path).name

    # Modify the config file
    cfg_file.write_text("[DEFAULT]\nLogLevel = DEBUG\n")

    # Calling main.diff_config_backup must not deadlock
    diff_lines = main.diff_config_backup(backup_name)
    assert len(diff_lines) > 0
    diff_text = "".join(diff_lines)
    assert "-LogLevel = INFO" in diff_text
    assert "+LogLevel = DEBUG" in diff_text
