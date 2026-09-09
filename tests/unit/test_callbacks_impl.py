"""Unit tests for CallbacksImpl bridging layer in src/gui/callbacks_impl.py."""

from unittest.mock import MagicMock
from gui.callbacks_impl import CallbacksImpl
from processor.digitizer import MeterResult


def test_callbacks_impl_methods():
    mock_meter_data = MagicMock(
        return_value=MeterResult(meters=[], digital_results={}, analog_results={})
    )
    mock_image_b64 = MagicMock(return_value="base64img")
    mock_config = MagicMock()
    mock_load_cfg = MagicMock(return_value="[DEFAULT]\n")
    mock_save_cfg = MagicMock()
    mock_use_cfg = MagicMock()
    mock_storage = MagicMock()
    mock_list_backups = MagicMock(return_value=[{"name": "b1.bak"}])
    mock_restore = MagicMock()
    mock_undo = MagicMock(return_value="b1.bak")
    mock_snapshot = MagicMock(return_value="snap.bak")
    mock_delete = MagicMock(return_value=True)
    mock_diff = MagicMock(return_value=["+ line\n"])

    callbacks = CallbacksImpl(
        get_meter_data_fn=mock_meter_data,
        get_image_base64_fn=mock_image_b64,
        get_config_fn=lambda: mock_config,
        load_config_file_fn=mock_load_cfg,
        save_config_file_fn=mock_save_cfg,
        use_config_fn=mock_use_cfg,
        get_storage_fn=lambda: mock_storage,
        list_backups_fn=mock_list_backups,
        restore_backup_fn=mock_restore,
        undo_backup_fn=mock_undo,
        create_snapshot_fn=mock_snapshot,
        delete_backup_fn=mock_delete,
        diff_backup_fn=mock_diff,
    )

    # Verify delegation for all methods
    assert callbacks.get_meter_data() == mock_meter_data.return_value
    assert callbacks.get_image_as_base64_str("orig") == "base64img"
    assert callbacks.get_config() == mock_config
    assert callbacks.load_config_file() == "[DEFAULT]\n"

    callbacks.save_config_file("[DEFAULT]\nLogLevel=DEBUG\n")
    mock_save_cfg.assert_called_once_with("[DEFAULT]\nLogLevel=DEBUG\n")

    callbacks.use_config()
    mock_use_cfg.assert_called_once()

    assert callbacks.get_storage() == mock_storage
    assert callbacks.list_config_backups() == [{"name": "b1.bak"}]

    callbacks.restore_config_backup("b1.bak")
    mock_restore.assert_called_once_with("b1.bak")

    assert callbacks.undo_last_config() == "b1.bak"
    assert callbacks.create_config_snapshot("tag") == "snap.bak"
    assert callbacks.delete_config_backup("b1.bak") is True
    assert callbacks.diff_config_backup("b1.bak") == ["+ line\n"]
