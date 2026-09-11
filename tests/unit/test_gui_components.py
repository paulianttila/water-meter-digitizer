import asyncio
from unittest.mock import MagicMock, patch

import pytest

from gui.components.consumption_card import ConsumptionCard
from gui.components.diagnostics_card import DiagnosticsCard
from gui.components.history_table_card import HistoryTableCard
from gui.components.leak_monitor_card import LeakMonitorCard
from gui.components.services_status_card import ServicesStatusCard
from gui.page_api_console import ApiConsolePage
from gui.page_previous_values import PreviousValuesPage
from gui.page_services import ServicesPage


@pytest.fixture(autouse=True)
def mock_ui_notify():
    with patch("nicegui.ui.notify"), patch("nicegui.ui.run_javascript"):
        yield


@pytest.fixture
def mock_callbacks():
    cb = MagicMock()
    cb.get_health_data.return_value = {
        "status": "healthy",
        "uptime": {"uptime_human": "1d 2h", "uptime_seconds": 93600},
        "camera": {
            "reachable": True,
            "latency_ms": 12.5,
            "url": "http://cam.local/jpg",
        },
        "memory": {"rss_mb": 45.2, "peak_rss_mb": 50.1},
        "cache": {
            "hit_ratio_percent": 80.0,
            "current_size": 4,
            "max_size": 10,
            "hits": 8,
            "misses": 2,
        },
        "models": {
            "total_inferences": 15,
            "avg_inference_ms": 4.2,
            "digital": {"exists": True, "enabled": True},
            "analog": {"exists": True, "enabled": True},
        },
        "system": {
            "version": "1.0.0",
            "python_version": "3.11.13",
            "platform": "Darwin",
        },
    }
    cb.get_leak_status.return_value = {
        "enabled": True,
        "state": "OK",
        "meter_name": "total",
        "current_flow_rate": 0.0,
        "current_flow_duration_seconds": 0.0,
        "current_flow_volume": 0.0,
        "consecutive_zero_readings": 5,
        "last_zero_flow_time": "2026-09-10T12:00:00Z",
        "recent_events": [
            {
                "start_time": "2026-09-10T10:00:00Z",
                "duration_seconds": 60.0,
                "leaked_volume": 0.05,
                "resolved": True,
            }
        ],
    }
    cb.reset_leak_status.return_value = {
        "enabled": True,
        "state": "OK",
        "meter_name": "total",
    }
    cb.get_poller_status.return_value = {
        "enabled": True,
        "running": True,
        "interval_seconds": 30,
        "total_runs": 10,
        "successful_runs": 10,
        "failed_runs": 0,
        "next_run": "2026-09-10T12:00:30Z",
    }
    cb.trigger_poller.return_value = {
        "status": "success",
        "message": "Poller triggered successfully",
    }
    cb.get_mqtt_status.return_value = {
        "enabled": True,
        "connected": True,
        "broker": "192.168.1.10",
        "port": 1883,
        "topic_prefix": "watermeter",
        "ha_discovery": True,
    }
    cb.get_previous_values.return_value = {
        "total": {"value": "123.456", "time": "2026.09.10 12:00:00"}
    }
    cb.set_previous_value.return_value = {
        "status": "success",
        "message": "Baseline updated",
        "meter": "total",
        "value": "123.456",
    }
    mock_cfg = MagicMock()
    mock_meter = MagicMock()
    mock_meter.name = "total"
    mock_cfg.meter_configs = [mock_meter]
    cb.get_config.return_value = mock_cfg

    mock_storage = MagicMock()
    mock_summary = MagicMock()
    mock_summary.meters_tracked = ["total"]
    mock_summary.total_records = 42
    mock_storage.get_summary.return_value = mock_summary
    mock_storage.get_consumption.return_value = []
    cb.get_storage.return_value = mock_storage

    return cb


def test_diagnostics_card_rendering_and_update(mock_callbacks):
    card = DiagnosticsCard(mock_callbacks)
    card.render()
    assert card.container is not None

    # Update with healthy telemetry data
    card.update_data(mock_callbacks.get_health_data())
    assert card._data["status"] == "healthy"

    # Update with degraded / empty telemetry
    card.update_data({"status": "degraded"})
    assert card._data["status"] == "degraded"


def test_diagnostics_card_fetch(mock_callbacks):
    card = DiagnosticsCard(mock_callbacks)
    card.render()
    asyncio.run(card.fetch_and_update())
    mock_callbacks.get_health_data.assert_called_once()
    assert card._data["status"] == "healthy"


def test_leak_monitor_card_rendering_and_update(mock_callbacks):
    card = LeakMonitorCard(mock_callbacks)
    card.render()
    assert card.container is not None

    card.update_data(mock_callbacks.get_leak_status())
    assert card._data["state"] == "OK"

    # Test leak detected state
    card.update_data({"enabled": True, "state": "LEAK_DETECTED"})
    assert card._data["state"] == "LEAK_DETECTED"


def test_leak_monitor_card_actions(mock_callbacks):
    card = LeakMonitorCard(mock_callbacks)
    card.render()
    asyncio.run(card.fetch_and_update())
    mock_callbacks.get_leak_status.assert_called_once()

    asyncio.run(card.reset_leak_state())
    mock_callbacks.reset_leak_status.assert_called_once()


def test_services_status_card_rendering_and_update(mock_callbacks):
    card = ServicesStatusCard(mock_callbacks)
    card.render()
    assert card.container is not None

    card.update_data(
        mock_callbacks.get_poller_status(), mock_callbacks.get_mqtt_status()
    )
    assert card._poller_data["running"] is True
    assert card._mqtt_data["connected"] is True


def test_services_status_card_actions(mock_callbacks):
    card = ServicesStatusCard(mock_callbacks)
    card.render()
    asyncio.run(card.fetch_and_update())
    mock_callbacks.get_poller_status.assert_called_once()
    mock_callbacks.get_mqtt_status.assert_called_once()

    asyncio.run(card.trigger_poller())
    mock_callbacks.trigger_poller.assert_called_once()


def test_previous_values_page(mock_callbacks):
    page = PreviousValuesPage(mock_callbacks)
    page.table_container = MagicMock()
    page.refresh_table()
    mock_callbacks.get_previous_values.assert_called_once()


def test_previous_values_page_save(mock_callbacks):
    page = PreviousValuesPage(mock_callbacks)
    page.meter_select = MagicMock(value="total")
    page.value_input = MagicMock(value="456.789")

    asyncio.run(page._save_baseline())
    mock_callbacks.set_previous_value.assert_called_once_with("total", "456.789")


def test_api_console_page():
    page = ApiConsolePage()
    assert page.port == 3000

    # Test preset endpoint change
    page.url_input = MagicMock(value="")
    ev = MagicMock(value="/healthcheck")
    page._on_endpoint_change(ev)
    assert page.url_input.value == "/healthcheck"
    assert page.selected_method == "GET"


def test_api_console_page_execute():
    page = ApiConsolePage()
    page.url_input = MagicMock(value="/version")
    page.selected_method = "GET"
    page.status_label = MagicMock()
    page.response_viewer = MagicMock(content="")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"version": "1.0.0"}
        mock_resp.text = '{"version": "1.0.0"}'
        mock_get.return_value = mock_resp

        asyncio.run(page._execute_request())
        assert page.status_label.text == "HTTP 200"
        assert "1.0.0" in page.response_viewer.content


def test_consumption_card(mock_callbacks):
    from nicegui import ui

    card = ConsumptionCard(mock_callbacks)
    with ui.column() as container:
        card.render(container)
    mock_callbacks.get_storage.assert_called()


def test_history_table_card(mock_callbacks):
    from nicegui import ui

    card = HistoryTableCard(mock_callbacks)
    with ui.column() as container:
        card.render(container)
    mock_callbacks.get_storage.assert_called()


def test_time_machine_card(mock_callbacks):
    from nicegui import ui

    from gui.components.time_machine_card import TimeMachineCard

    mock_callbacks.get_frame_data_uri.return_value = "data:image/jpeg;base64,AAAA"

    mock_callbacks.get_timeline.return_value = [
        {
            "id": 1,
            "timestamp": "2026-09-10T12:00:00Z",
            "meters": {"total": {"value": 123.4, "unit": "m3", "confidence": 98.0}},
            "digital_results": {"0": "1", "1": "2"},
            "analog_results": {"0": "3"},
            "error": "",
            "frame_type": "full",
            "flow_detected": True,
            "confidence_scores": {"digital_0": 99.0},
        }
    ]

    card = TimeMachineCard(mock_callbacks)
    with ui.column() as container:
        card.render(container)
    mock_callbacks.get_timeline.assert_called()

    # Test rendering when no frame image is available
    mock_callbacks.get_frame_data_uri.return_value = None
    with ui.column() as c:
        card.render(c)


def test_services_page(mock_callbacks):
    page = ServicesPage(mock_callbacks)
    asyncio.run(page.fetch_all_telemetry())
    mock_callbacks.get_health_data.assert_called()
    mock_callbacks.get_leak_status.assert_called()
    mock_callbacks.get_poller_status.assert_called()
    mock_callbacks.get_mqtt_status.assert_called()
