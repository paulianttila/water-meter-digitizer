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

    mock_health = MagicMock(return_value={"status": "healthy"})
    mock_leak = MagicMock(return_value={"enabled": True, "state": "OK"})
    mock_reset_leak = MagicMock(return_value={"enabled": True, "state": "OK"})
    mock_poller = MagicMock(return_value={"enabled": True, "running": True})
    mock_trigger = MagicMock(return_value={"status": "success"})
    mock_mqtt = MagicMock(return_value={"enabled": True, "connected": True})
    mock_prev_vals = MagicMock(
        return_value={"total": {"value": "100.0", "time": "2026.01.01 12:00:00"}}
    )
    mock_set_prev = MagicMock(
        return_value={"status": "success", "meter": "total", "value": "120.0"}
    )

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
        get_health_data_fn=mock_health,
        get_leak_status_fn=mock_leak,
        reset_leak_status_fn=mock_reset_leak,
        get_poller_status_fn=mock_poller,
        trigger_poller_fn=mock_trigger,
        get_mqtt_status_fn=mock_mqtt,
        get_previous_values_fn=mock_prev_vals,
        set_previous_value_fn=mock_set_prev,
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

    assert callbacks.get_health_data() == {"status": "healthy"}
    assert callbacks.get_leak_status() == {"enabled": True, "state": "OK"}
    assert callbacks.reset_leak_status() == {"enabled": True, "state": "OK"}
    assert callbacks.get_poller_status() == {"enabled": True, "running": True}
    assert callbacks.trigger_poller() == {"status": "success"}
    assert callbacks.get_mqtt_status() == {"enabled": True, "connected": True}
    assert callbacks.get_previous_values() == {
        "total": {"value": "100.0", "time": "2026.01.01 12:00:00"}
    }
    assert callbacks.set_previous_value("total", "120.0") == {
        "status": "success",
        "meter": "total",
        "value": "120.0",
    }


def test_callbacks_impl_fallbacks():
    """Verify default fallback behaviors when optional delegates are omitted."""
    callbacks = CallbacksImpl(
        get_meter_data_fn=lambda **kwargs: MeterResult(
            meters=[], digital_results={}, analog_results={}
        ),
        get_image_base64_fn=lambda name: "",
        get_config_fn=MagicMock,
        load_config_file_fn=lambda: "",
        save_config_file_fn=lambda data: None,
        use_config_fn=lambda: None,
        get_storage_fn=lambda: None,
        list_backups_fn=lambda: [],
        restore_backup_fn=lambda name: None,
        undo_backup_fn=lambda: None,
        create_snapshot_fn=lambda tag: None,
        delete_backup_fn=lambda name: False,
        diff_backup_fn=lambda name: [],
    )

    assert callbacks.get_health_data() == {"status": "unknown"}
    assert callbacks.get_leak_status() == {"enabled": False, "state": "OK"}
    assert callbacks.reset_leak_status() == {"enabled": False, "state": "OK"}
    assert callbacks.get_poller_status() == {"enabled": False, "running": False}
    assert callbacks.trigger_poller()["status"] == "error"
    assert callbacks.get_mqtt_status() == {"enabled": False, "connected": False}
    assert callbacks.get_previous_values() == {}
    assert callbacks.set_previous_value("total", "10.0")["status"] == "error"


def test_callbacks_impl_frame_data_uris():
    mock_storage = MagicMock()
    # JPEG test image bytes
    mock_storage.get_frame_bytes.return_value = (
        b"\xff\xd8\xff\xe0test_bytes",
        "image/jpeg",
    )

    callbacks = CallbacksImpl(
        get_meter_data_fn=lambda **kwargs: MeterResult(
            meters=[], digital_results={}, analog_results={}
        ),
        get_image_base64_fn=lambda name: "",
        get_config_fn=MagicMock,
        load_config_file_fn=lambda: "",
        save_config_file_fn=lambda data: None,
        use_config_fn=lambda: None,
        get_storage_fn=lambda: mock_storage,
        list_backups_fn=lambda: [],
        restore_backup_fn=lambda name: None,
        undo_backup_fn=lambda: None,
        create_snapshot_fn=lambda tag: None,
        delete_backup_fn=lambda name: False,
        diff_backup_fn=lambda name: [],
    )

    uri = callbacks.get_frame_data_uri(1)
    assert uri is not None
    assert uri.startswith("data:image/jpeg;base64,")

    # When storage is None
    callbacks_no_store = CallbacksImpl(
        get_meter_data_fn=lambda **kwargs: MeterResult(
            meters=[], digital_results={}, analog_results={}
        ),
        get_image_base64_fn=lambda name: "",
        get_config_fn=MagicMock,
        load_config_file_fn=lambda: "",
        save_config_file_fn=lambda data: None,
        use_config_fn=lambda: None,
        get_storage_fn=lambda: None,
        list_backups_fn=lambda: [],
        restore_backup_fn=lambda name: None,
        undo_backup_fn=lambda: None,
        create_snapshot_fn=lambda tag: None,
        delete_backup_fn=lambda name: False,
        diff_backup_fn=lambda name: [],
    )
    assert callbacks_no_store.get_frame_data_uri(1) is None
    assert callbacks_no_store.get_frame_diff_data_uri(1) is None


def test_callbacks_impl_timeline_and_diffs():
    from datetime import datetime

    import cv2
    import numpy as np

    from storage.base import MeterReading, ReadingRecord

    # Create dummy images
    img1 = np.zeros((50, 50, 3), dtype=np.uint8)
    img2 = np.ones((50, 50, 3), dtype=np.uint8) * 200
    _, buf1 = cv2.imencode(".jpg", img1)
    _, buf2 = cv2.imencode(".jpg", img2)
    bytes1 = buf1.tobytes()
    bytes2 = buf2.tobytes()

    mock_storage = MagicMock()
    mock_record = ReadingRecord(
        id=1,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        meters={"total": MeterReading(value=100.0)},
        digital_results={"total": "100"},
        analog_results={},
        error="",
        frame_type="anomaly",
        frame_path=None,
        flow_detected=True,
        confidence_scores={"total": 0.99},
    )
    mock_storage.get_timeline.return_value = [mock_record]
    mock_storage.get_frame_bytes.side_effect = lambda rid: (
        (bytes1, "image/jpeg")
        if rid == 1
        else ((bytes2, "image/jpeg") if rid == 2 else (None, None))
    )

    callbacks = CallbacksImpl(
        get_meter_data_fn=lambda **kwargs: MeterResult(
            meters=[], digital_results={}, analog_results={}
        ),
        get_image_base64_fn=lambda name: "",
        get_config_fn=MagicMock,
        load_config_file_fn=lambda: "",
        save_config_file_fn=lambda data: None,
        use_config_fn=lambda: None,
        get_storage_fn=lambda: mock_storage,
        list_backups_fn=lambda: [],
        restore_backup_fn=lambda name: None,
        undo_backup_fn=lambda: None,
        create_snapshot_fn=lambda tag: None,
        delete_backup_fn=lambda name: False,
        diff_backup_fn=lambda name: [],
    )

    timeline = callbacks.get_timeline(
        limit=10, offset=0, anomalies_only=False, frames_only=False
    )
    assert len(timeline) == 1
    assert timeline[0]["id"] == 1
    assert timeline[0]["has_frame"] is True

    # Frame diff with compare_id
    diff_res = callbacks.get_frame_diff(1, compare_id=2)
    assert "ssim_similarity" in diff_res
    assert diff_res["reading_id"] == 1
    assert diff_res["compare_id"] == 2

    # Frame diff with self
    diff_self = callbacks.get_frame_diff(1, compare_id=None)
    assert diff_self["ssim_similarity"] == 1.0

    # Frame diff with missing frame
    diff_err = callbacks.get_frame_diff(99)
    assert "error" in diff_err

    # Frame diff data URI
    diff_uri = callbacks.get_frame_diff_data_uri(1, compare_id=2)
    assert diff_uri is not None
    assert diff_uri.startswith("data:image/jpeg;base64,")

    # Empty storage timeline
    callbacks_no_store = CallbacksImpl(
        get_meter_data_fn=lambda **kwargs: MeterResult(
            meters=[], digital_results={}, analog_results={}
        ),
        get_image_base64_fn=lambda name: "",
        get_config_fn=MagicMock,
        load_config_file_fn=lambda: "",
        save_config_file_fn=lambda data: None,
        use_config_fn=lambda: None,
        get_storage_fn=lambda: None,
        list_backups_fn=lambda: [],
        restore_backup_fn=lambda name: None,
        undo_backup_fn=lambda: None,
        create_snapshot_fn=lambda tag: None,
        delete_backup_fn=lambda name: False,
        diff_backup_fn=lambda name: [],
    )
    assert callbacks_no_store.get_timeline() == []
    assert "error" in callbacks_no_store.get_frame_diff(1)
