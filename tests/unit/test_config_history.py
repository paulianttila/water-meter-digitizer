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
    assert backups[0].is_auto is True


def test_restore_and_undo_backup(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    # Create backup with initial content
    b_path = ConfigHistoryManager.create_backup(str(cfg_file), tag="Initial")
    assert b_path is not None

    # Overwrite config file
    cfg_file.write_text("[DEFAULT]\nLogLevel = DEBUG\n")
    assert "LogLevel = DEBUG" in cfg_file.read_text()

    # Test restore_backup
    ConfigHistoryManager.restore_backup(str(cfg_file), b_path)
    assert "LogLevel = INFO" in cfg_file.read_text()

    # Overwrite config file again and test undo_last
    cfg_file.write_text("[DEFAULT]\nLogLevel = WARNING\n")
    undone = ConfigHistoryManager.undo_last(str(cfg_file))
    assert undone is not None


def test_delete_backup(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None
    b_name = Path(backup_path).name

    deleted = ConfigHistoryManager.delete_backup(str(cfg_file), b_name)
    assert deleted is True
    assert not os.path.exists(backup_path)

    # Delete non-existent
    assert (
        ConfigHistoryManager.delete_backup(str(cfg_file), "non_existent.bak") is False
    )


def test_get_diff(temp_config_dir):
    _cfg_dir, cfg_file = temp_config_dir

    backup_path = ConfigHistoryManager.create_backup(str(cfg_file))
    assert backup_path is not None

    current_content = "[DEFAULT]\nLogLevel = DEBUG\n"
    diff = ConfigHistoryManager.get_diff(
        current_content, Path(backup_path).name, config_file=str(cfg_file)
    )
    assert len(diff) > 0
    diff_str = "".join(diff)
    assert "-LogLevel = INFO" in diff_str or "- LogLevel = INFO" in diff_str
    assert "+LogLevel = DEBUG" in diff_str or "+ LogLevel = DEBUG" in diff_str


def test_edge_cases_and_missing_files(temp_config_dir):
    cfg_dir, cfg_file = temp_config_dir

    # 1. Restore non-existent file
    with pytest.raises(FileNotFoundError):
        ConfigHistoryManager.restore_backup(str(cfg_file), "does_not_exist.bak")

    # 2. Diff non-existent file
    with pytest.raises(FileNotFoundError):
        ConfigHistoryManager.get_diff(
            "[DEFAULT]", "does_not_exist.bak", config_file=str(cfg_file)
        )

    # 3. Undo on empty backups
    empty_cfg = cfg_dir / "empty.ini"
    empty_cfg.write_text("[DEFAULT]")
    assert ConfigHistoryManager.undo_last(str(empty_cfg)) is None

    # 4. Legacy backup in parent dir restored by name
    legacy_file = cfg_dir / "config.ini_20260202_100000.bak"
    legacy_file.write_text("[DEFAULT]\nLogLevel = TRACE\n")
    ConfigHistoryManager.restore_backup(str(cfg_file), legacy_file.name)
    assert "LogLevel = TRACE" in cfg_file.read_text()

    # 5. Delete legacy backup in parent dir by relative name
    legacy_file2 = cfg_dir / "config.ini_20260202_110000.bak"
    legacy_file2.write_text("[DEFAULT]\nLogLevel = TRACE\n")
    assert ConfigHistoryManager.delete_backup(str(cfg_file), legacy_file2.name) is True
