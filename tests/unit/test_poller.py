import asyncio
from unittest.mock import MagicMock

import pytest

from configuration import Poller
from poller.scheduler import BackgroundPoller
from processor.digitizer import MeterResult, MeterValue


@pytest.mark.anyio
async def test_background_poller_lifecycle_and_run():
    poller_cfg = Poller(
        enabled=True,
        interval_seconds=10,
        run_on_startup=False,
    )

    mock_readout = MagicMock(
        return_value=MeterResult(
            meters=[MeterValue(name="main", value="50.0")],
            digital_results={},
            analog_results={},
            error="",
        )
    )
    mock_mqtt = MagicMock()

    poller = BackgroundPoller(
        config=poller_cfg,
        readout_func=mock_readout,
        mqtt_service=mock_mqtt,
    )

    status_initial = poller.get_status()
    assert status_initial["enabled"] is True
    assert status_initial["running"] is False
    assert status_initial["total_runs"] == 0

    poller.start()
    assert poller._running is True

    # Trigger manual poll
    poller.trigger_now()
    await asyncio.sleep(0.1)

    assert mock_readout.call_count >= 1
    assert mock_mqtt.publish_meter_result.call_count >= 1

    status_after = poller.get_status()
    assert status_after["total_runs"] >= 1
    assert status_after["successful_runs"] >= 1
    assert status_after["last_error"] == ""

    poller.stop()
    assert poller._running is False


@pytest.mark.anyio
async def test_background_poller_error_handling():
    poller_cfg = Poller(
        enabled=True,
        interval_seconds=10,
        run_on_startup=False,
    )

    def failing_readout(*args, **kwargs):
        raise RuntimeError("Camera connection failed")

    mock_mqtt = MagicMock()

    poller = BackgroundPoller(
        config=poller_cfg,
        readout_func=failing_readout,
        mqtt_service=mock_mqtt,
    )

    res = await poller._execute_poll()
    assert res is None
    assert poller.failed_runs == 1
    assert "Camera connection failed" in poller.last_error
    mock_mqtt.publish_error.assert_called_once_with("Camera connection failed")


def test_poller_and_mqtt_api_endpoints():
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)

    # Test /poller/status
    resp = client.get("/poller/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "running" in data
    assert "interval_seconds" in data

    # Test /poller/trigger
    resp_trig = client.post("/poller/trigger")
    assert resp_trig.status_code == 200
    assert "triggered successfully" in resp_trig.json()["message"]

    # Test /mqtt/status
    resp_mqtt = client.get("/mqtt/status")
    assert resp_mqtt.status_code == 200
    data_mqtt = resp_mqtt.json()
    assert "enabled" in data_mqtt
    assert "connected" in data_mqtt
    assert "topic_prefix" in data_mqtt
