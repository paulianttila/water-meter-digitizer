"""Unit tests for ServiceAccessor in src/gui/service_accessor.py."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException

from gui.callbacks_impl import CallbacksImpl
from gui.service_accessor import ServiceAccessor
from processor.digitizer import MeterResult


def test_service_accessor_config_and_storage():
    mock_app = FastAPI()
    mock_config = MagicMock()
    mock_storage = MagicMock()
    mock_app.state.config = mock_config
    mock_app.state.storage = mock_storage
    mock_app.state.config_version = 4

    accessor = ServiceAccessor(mock_app)
    assert accessor.app is mock_app
    assert accessor.get_config() is mock_config
    assert accessor.get_storage() is mock_storage
    assert accessor.get_config_version() == 4


def test_service_accessor_default_config_fallback():
    mock_app = FastAPI()
    mock_default = MagicMock()

    accessor = ServiceAccessor(mock_app, default_config=mock_default)
    assert accessor.get_config() is mock_default


def test_service_accessor_meter_data_and_image():
    mock_app = FastAPI()
    mock_app.state.image_cache = MagicMock()
    accessor = ServiceAccessor(mock_app)

    with patch("gui.service_accessor.get_meter_data") as mock_get_meter:
        mock_result = MeterResult(meters=[], digital_results={}, analog_results={})
        mock_get_meter.return_value = mock_result
        res = accessor.get_meter_data(url="http://cam.local", saveimages=True)
        assert res is mock_result
        mock_get_meter.assert_called_once_with(
            url="http://cam.local",
            saveimages=True,
            app_instance=mock_app,
            config=None,
        )

    with patch("gui.service_accessor.get_cached_image_base64", return_value="b64str"):
        assert accessor.get_image_as_base64_str("final") == "b64str"

    with (
        patch("gui.service_accessor.get_cached_image_base64", return_value=None),
        pytest.raises(HTTPException),
    ):
        accessor.get_image_as_base64_str("missing")


def test_service_accessor_services_status():
    mock_app = FastAPI()
    mock_tracker = MagicMock()
    status_mock = MagicMock()
    status_mock.to_dict.return_value = {"enabled": True, "state": "OK"}
    mock_tracker.get_status.return_value = status_mock
    mock_tracker.reset.return_value = status_mock

    mock_poller = MagicMock()
    mock_poller.get_status.return_value = {"enabled": True, "running": True}

    mock_mqtt = MagicMock()
    mock_mqtt.get_status.return_value = {"enabled": True, "connected": True}

    mock_app.state.zero_flow_tracker = mock_tracker
    mock_app.state.poller = mock_poller
    mock_app.state.mqtt_service = mock_mqtt

    accessor = ServiceAccessor(mock_app)
    assert accessor.get_leak_status() == {"enabled": True, "state": "OK"}
    assert accessor.reset_leak_status() == {"enabled": True, "state": "OK"}
    assert accessor.get_poller_status() == {"enabled": True, "running": True}
    assert accessor.trigger_poller()["status"] == "success"
    assert accessor.get_mqtt_status() == {"enabled": True, "connected": True}


def test_service_accessor_previous_values(tmp_path):
    mock_app = FastAPI()
    mock_cfg = MagicMock()
    pv_path = tmp_path / "prevalue.ini"
    mock_cfg.previous_value_file = str(pv_path)
    mock_app.state.config = mock_cfg

    accessor = ServiceAccessor(mock_app)

    with patch(
        "previous_value.get_all_previous_values",
        return_value={"main": {"value": "100"}},
    ):
        assert accessor.get_previous_values() == {"main": {"value": "100"}}

    with patch("previous_value.save_previous_value_to_file") as mock_save:
        res = accessor.set_previous_value("main", "123.45")
        assert res["status"] == "success"
        assert res["value"] == "123.45"
        mock_save.assert_called_once_with(str(pv_path), "main", "123.45")

    with pytest.raises(ValueError, match="Value cannot be empty"):
        accessor.set_previous_value("main", "")

    with pytest.raises(ValueError, match="Value cannot be negative"):
        accessor.set_previous_value("main", "-10")

    with pytest.raises(ValueError, match="Meter name cannot be empty"):
        accessor.set_previous_value("  ", "10")


def test_callbacks_from_service_accessor():
    mock_app = FastAPI()
    mock_cfg_svc = MagicMock()
    mock_cfg_svc.load.return_value = "[DEFAULT]\n"
    mock_cfg_svc.list_backups.return_value = []

    accessor = ServiceAccessor(mock_app, config_file_service=mock_cfg_svc)
    mock_use_cfg = MagicMock()
    callbacks = CallbacksImpl.from_service_accessor(
        accessor, use_config_fn=mock_use_cfg
    )

    assert callbacks.load_config_file() == "[DEFAULT]\n"
    assert callbacks.list_config_backups() == []
    callbacks.use_config()
    mock_use_cfg.assert_called_once()
