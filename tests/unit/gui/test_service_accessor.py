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


def test_service_accessor_cnn_models_and_evaluation(tmp_path):
    mock_app = FastAPI()
    cfg = MagicMock()
    dig_dir = tmp_path / "digital" / "class100"
    dig_dir.mkdir(parents=True)
    m1 = dig_dir / "test_model_q.tflite"
    m1.write_bytes(b"dummy")
    m2 = dig_dir / "test_model2.tflite"
    m2.write_bytes(b"dummy2")

    cfg.digital_models_dir = str(tmp_path / "digital")
    cfg.analog_models_dir = str(tmp_path / "analog")
    mock_app.state.config = cfg

    accessor = ServiceAccessor(mock_app)

    # 1. list_cnn_models
    models = accessor.list_cnn_models("digital")
    assert len(models) == 2
    assert any(m["quantized"] is True for m in models)
    assert any(m["quantized"] is False for m in models)

    # empty dir
    assert accessor.list_cnn_models("analog") == []

    # 2. evaluate_crop_model empty
    empty_res = accessor.evaluate_crop_model("", str(m1), is_digital=True)
    assert empty_res["error"] == "No image data provided"
    assert empty_res["value"] is None

    # 3. evaluate_crop_model mock
    with (
        patch("utils.image.convert_base64_str_to_image", return_value=MagicMock()),
        patch("cnn.digital_counter_cnn.DigitalCounterCNN") as mock_cnn_cls,
    ):
        mock_instance = mock_cnn_cls.return_value
        mock_instance.readout_with_confidence.return_value = (3.5, 92.4)

        res = accessor.evaluate_crop_model("dGVzdA==", str(m1), is_digital=True)
        assert res["value"] == 3.5
        assert res["confidence"] == 92.4
        assert res["error"] is None
        assert res["latency_ms"] >= 0.0

    # 4. benchmark_crop_models
    with (
        patch.object(
            accessor,
            "evaluate_crop_model",
            side_effect=[
                {
                    "value": 1.0,
                    "confidence": 75.0,
                    "latency_ms": 5.0,
                    "error": None,
                },
                {
                    "value": 2.0,
                    "confidence": 95.0,
                    "latency_ms": 2.0,
                    "error": None,
                },
            ],
        ),
    ):
        bench = accessor.benchmark_crop_models("dGVzdA==", is_digital=True)
        assert len(bench) == 2
        # Ranked by confidence desc: 95.0 first
        assert bench[0]["confidence"] == 95.0
        assert bench[1]["confidence"] == 75.0


def test_service_accessor_apply_model_to_config():
    mock_app = FastAPI()
    cfg = MagicMock()
    mock_cfg_svc = MagicMock()
    use_cfg_mock = MagicMock()

    cfg.digital_readout = MagicMock()
    cfg.analog_readout = MagicMock()
    cfg.save_to_string.return_value = "[SAVED]"
    mock_app.state.config = cfg

    accessor = ServiceAccessor(mock_app, config_file_service=mock_cfg_svc)

    res = accessor.apply_model_to_config(
        "/path/to/model.tflite", is_digital=True, use_config_fn=use_cfg_mock
    )
    assert res is True
    assert cfg.digital_readout.model_file == "/path/to/model.tflite"
    assert cfg.digital_readout.model == "auto"
    mock_cfg_svc.save.assert_called_once_with("[SAVED]")
    use_cfg_mock.assert_called_once()
