from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from leak.models import LeakState, ZeroFlowStatus
from main import app


@pytest.fixture(autouse=True)
def restore_app_state():
    orig_poller = getattr(app.state, "poller", None)
    orig_mqtt = getattr(app.state, "mqtt_service", None)
    orig_tracker = getattr(app.state, "zero_flow_tracker", None)
    orig_init_config_fn = getattr(app.state, "init_config_fn", None)
    yield
    app.state.poller = orig_poller
    app.state.mqtt_service = orig_mqtt
    app.state.zero_flow_tracker = orig_tracker
    app.state.init_config_fn = orig_init_config_fn


def test_leak_status_and_reset():
    client = TestClient(app)

    # 1. Tracker is None
    app.state.zero_flow_tracker = None
    resp_none = client.get("/leak/status")
    assert resp_none.status_code == 200
    assert resp_none.json()["enabled"] is False

    resp_reset_400 = client.post("/leak/reset")
    assert resp_reset_400.status_code == 400

    # 2. Tracker initialized
    mock_tracker = MagicMock()
    mock_status = ZeroFlowStatus(
        enabled=True,
        state=LeakState.OK,
        meter_name="total",
        current_flow_duration_seconds=0.0,
        current_flow_volume=0.0,
    )
    mock_tracker.get_status.return_value = mock_status
    mock_tracker.reset.return_value = mock_status
    app.state.zero_flow_tracker = mock_tracker

    resp_ok = client.get("/leak/status")
    assert resp_ok.status_code == 200
    assert resp_ok.json()["enabled"] is True
    assert resp_ok.json()["state"] == "OK"

    resp_reset_ok = client.post("/leak/reset")
    assert resp_reset_ok.status_code == 200
    mock_tracker.reset.assert_called_once()


def test_poller_status_and_trigger():
    client = TestClient(app)

    # 1. Poller is None
    app.state.poller = None
    resp_none = client.get("/poller/status")
    assert resp_none.status_code == 200
    assert resp_none.json()["enabled"] is False

    resp_trig_400 = client.post("/poller/trigger")
    assert resp_trig_400.status_code == 400

    # 2. Poller initialized
    mock_poller = MagicMock()
    mock_poller.get_status.return_value = {
        "enabled": True,
        "running": True,
        "interval_seconds": 30,
    }
    app.state.poller = mock_poller

    resp_ok = client.get("/poller/status")
    assert resp_ok.status_code == 200
    assert resp_ok.json()["running"] is True

    resp_trig_ok = client.post("/poller/trigger")
    assert resp_trig_ok.status_code == 200
    assert "successfully" in resp_trig_ok.json()["message"].lower()
    mock_poller.trigger_now.assert_called_once()


def test_mqtt_status():
    client = TestClient(app)

    # 1. MQTT service is None
    app.state.mqtt_service = None
    resp_none = client.get("/mqtt/status")
    assert resp_none.status_code == 200
    assert resp_none.json()["connected"] is False

    # 2. MQTT service initialized
    mock_mqtt = MagicMock()
    mock_mqtt.get_status.return_value = {
        "enabled": True,
        "connected": True,
        "broker_host": "localhost",
    }
    app.state.mqtt_service = mock_mqtt

    resp_ok = client.get("/mqtt/status")
    assert resp_ok.status_code == 200
    assert resp_ok.json()["connected"] is True


def test_system_routes():
    client = TestClient(app)

    # 1. GUI redirect
    resp_gui = client.get("/gui", follow_redirects=False)
    assert resp_gui.status_code in (301, 302, 307, 308)
    assert resp_gui.headers["location"] == "/"

    # 2. Version
    resp_ver = client.get("/version")
    assert resp_ver.status_code == 200
    assert "version" in resp_ver.json()

    # 3. Reload config success
    mock_init = MagicMock()
    app.state.init_config_fn = mock_init
    resp_reload = client.post("/reload")
    assert resp_reload.status_code == 200
    assert resp_reload.json()["status"] == "success"
    mock_init.assert_called_once()

    # 4. Reload config failure
    mock_init.side_effect = RuntimeError("Failed to load ini file")
    resp_reload_err = client.get("/reload")
    assert resp_reload_err.status_code == 500
    assert resp_reload_err.json()["status"] == "error"
