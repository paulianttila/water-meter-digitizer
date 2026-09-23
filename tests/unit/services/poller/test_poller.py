"""Unit tests for periodic background meter readout poller scheduler."""

import asyncio
from unittest.mock import MagicMock

import pytest

from configuration import Poller
from processor.digitizer import MeterResult, MeterValue
from services.poller.scheduler import BackgroundPoller


@pytest.mark.anyio
async def test_background_poller_lifecycle_and_run():
    poller_cfg = Poller(
        enabled=True,
        cron="*/10 * * * * *",
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
        cron="*/10 * * * * *",
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


@pytest.mark.anyio
async def test_background_poller_manual_trigger_when_disabled():
    poller_cfg = Poller(
        enabled=False,
        cron="0 * * * * *",
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

    poller = BackgroundPoller(
        config=poller_cfg,
        readout_func=mock_readout,
    )
    assert poller._running is False

    # Trigger manual poll even though background scheduler is disabled
    poller.trigger_now()
    await asyncio.sleep(0.1)

    assert mock_readout.call_count == 1
    assert poller.total_runs == 1
    assert poller.successful_runs == 1


def test_background_poller_start_without_loop():
    poller_cfg = Poller(
        enabled=True,
        cron="0 * * * * *",
        run_on_startup=False,
    )

    poller = BackgroundPoller(
        config=poller_cfg,
        readout_func=lambda: None,
    )
    # Should not raise RuntimeError even when no loop is running
    poller.start()
    assert poller._task is None


@pytest.mark.anyio
async def test_background_poller_consensus_filtering():
    poller_cfg = Poller(
        enabled=True,
        cron="*/10 * * * * *",
        consensus_reads=3,
        run_on_startup=False,
    )

    readings = [
        MeterResult(meters=[MeterValue(name="total", value="50.0")]),
        MeterResult(meters=[MeterValue(name="total", value="50.0")]),
        MeterResult(meters=[MeterValue(name="total", value="999.0")]),  # spike anomaly
        MeterResult(meters=[MeterValue(name="total", value="50.1")]),
    ]
    readings_iter = iter(readings)

    def mock_readout(*args, **kwargs):
        return next(readings_iter)

    mock_mqtt = MagicMock()
    poller = BackgroundPoller(
        config=poller_cfg,
        readout_func=mock_readout,
        mqtt_service=mock_mqtt,
    )

    status = poller.get_status()
    assert status["consensus_reads"] == 3
    assert status["consensus_buffer_size"] == 0

    # Poll 1
    r1 = await poller._execute_poll()
    assert r1.meters[0].value == "50.0"

    # Poll 2
    r2 = await poller._execute_poll()
    assert r2.meters[0].value == "50.0"

    # Poll 3 (Spike frame): consensus should return 50.0 instead of 999.0
    r3 = await poller._execute_poll()
    assert r3.meters[0].value == "50.0"

    # Poll 4: progression to 50.1
    r4 = await poller._execute_poll()
    assert r4.meters[0].value == "50.1"

    # Verify 999.0 was never published to MQTT
    published_values = [
        call.kwargs["meter_result"].meters[0].value
        for call in mock_mqtt.publish_meter_result.call_args_list
    ]
    assert "999.0" not in published_values
    assert published_values == ["50.0", "50.0", "50.0", "50.1"]


def test_poller_and_mqtt_api_endpoints():
    from fastapi.testclient import TestClient

    from main import app

    mock_poller = MagicMock()
    mock_poller.get_status.return_value = {
        "enabled": True,
        "running": True,
        "cron": "0 */5 * * * *",
        "consensus_reads": 1,
        "consensus_buffer_size": 0,
    }
    app.state.poller = mock_poller

    mock_mqtt = MagicMock()
    mock_mqtt.get_status.return_value = {
        "enabled": True,
        "connected": True,
        "topic_prefix": "watermeter",
    }
    app.state.mqtt_service = mock_mqtt

    client = TestClient(app)

    # Test /poller/status
    resp = client.get("/poller/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "running" in data
    assert "cron" in data
    assert "consensus_reads" in data

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


def test_calculate_next_cron_delay_seconds():
    from datetime import UTC, datetime

    from services.poller.scheduler import calculate_next_cron_delay

    base = datetime(2026, 9, 23, 12, 0, 12, 300000, tzinfo=UTC)
    delay, next_dt = calculate_next_cron_delay("*/15 * * * * *", now=base)
    assert abs(delay - 2.7) < 1e-4
    assert next_dt.second == 15

    # At boundary 15.0s, targets 30.0s
    base2 = datetime(2026, 9, 23, 12, 0, 15, 0, tzinfo=UTC)
    delay2, next_dt2 = calculate_next_cron_delay("*/15 * * * * *", now=base2)
    assert abs(delay2 - 15.0) < 1e-4
    assert next_dt2.second == 30

    # At 44.98s with min_delay=0.05, skips 45.0s to 12:01:00
    base3 = datetime(2026, 9, 23, 12, 0, 44, 980000, tzinfo=UTC)
    delay3, next_dt3 = calculate_next_cron_delay(
        "*/15 * * * * *", now=base3, min_delay=0.05
    )
    assert abs(delay3 - 15.02) < 1e-4
    assert next_dt3.second == 0
    assert next_dt3.minute == 1


def test_calculate_next_cron_delay_standard_5_field():
    from datetime import UTC, datetime

    from services.poller.scheduler import calculate_next_cron_delay

    base = datetime(2026, 9, 23, 12, 3, 20, tzinfo=UTC)
    delay, next_dt = calculate_next_cron_delay("*/5 * * * *", now=base)
    assert next_dt.minute == 5
    assert next_dt.second == 0
    assert abs(delay - 100.0) < 1e-4


@pytest.mark.anyio
async def test_background_poller_cron_schedule():
    from services.poller.scheduler import BackgroundPoller

    poller_cfg = Poller(
        enabled=True,
        cron="*/15 * * * * *",
        run_on_startup=False,
    )
    mock_readout = MagicMock(
        return_value=MeterResult(
            meters=[MeterValue(name="main", value="10.0")],
            digital_results={},
            analog_results={},
            error="",
        )
    )
    poller = BackgroundPoller(config=poller_cfg, readout_func=mock_readout)
    assert poller.get_status()["cron"] == "*/15 * * * * *"

    poller.start()
    assert poller._running is True
    await asyncio.sleep(0.05)
    assert poller.next_run is not None
    assert poller.next_run.second in (0, 15, 30, 45)

    poller.stop()


def test_poller_invalid_cron():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        Poller(cron="invalid cron expression")
