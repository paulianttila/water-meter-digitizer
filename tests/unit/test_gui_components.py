import asyncio
from unittest.mock import MagicMock, patch

import pytest

from configuration import Config
from gui.components.consumption_card import ConsumptionCard
from gui.components.diagnostics_card import DiagnosticsCard
from gui.components.history_table_card import HistoryTableCard
from gui.components.leak_monitor_card import LeakMonitorCard
from gui.components.services_status_card import ServicesStatusCard
from gui.page_api_console import ApiConsolePage
from gui.page_previous_values import PreviousValuesPage
from gui.page_services import ServicesPage
from simulator.meter_generator import MeterImageGenerator


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
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.content = b'{"version": "1.0.0"}'
        mock_resp.json.return_value = {"version": "1.0.0"}
        mock_resp.text = '{"version": "1.0.0"}'
        mock_get.return_value = mock_resp

        asyncio.run(page._execute_request())
        assert page.status_label.text == "HTTP 200"
        assert "1.0.0" in page.response_viewer.content


def test_api_console_page_mock_camera_url_builder():
    page = ApiConsolePage()
    # Default fixed URL
    qs = page.build_mock_query_string()
    assert "value=00452.91241" in qs

    # Modify parameters
    page.mock_mode = "ticker"
    page.mock_rate = 0.010
    page.mock_rotate = 15.0
    page.mock_glare = True
    page.mock_glare_intensity = 1.5
    page.mock_glare_pos = "200,150"
    page.mock_noise = 5.0
    page.mock_lcd_color = "blue"
    page.mock_lcd_bg = "black"
    page.mock_needle_color = "white"
    page.mock_width = 800
    page.mock_height = 600
    page.mock_digit_overrides[0] = "1"
    page.mock_analog_overrides[0] = "5.5"

    url = page.get_mock_url(relative=True)
    assert "mode=ticker" in url
    assert "rate=0.01" in url
    assert "rotate=15" in url
    assert "glare=true" in url
    assert "glare_intensity=1.5" in url
    assert "glare_pos=200%2C150" in url or "glare_pos=200,150" in url
    assert "noise=5" in url
    assert "lcd_color=blue" in url
    assert "lcd_bg=black" in url
    assert "needle_color=white" in url
    assert "width=800" in url
    assert "height=600" in url
    assert "digit1=1" in url
    assert "analog1=5.5" in url


def test_api_console_page_mock_camera_generate_and_reset():
    page = ApiConsolePage()
    page.mock_img_elem = MagicMock()
    page.mock_meta_meter_val = MagicMock()
    page.mock_meta_dig_val = MagicMock()
    page.mock_meta_ana_val = MagicMock()
    page.mock_meta_size_badge = MagicMock()

    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("gui.page_api_console.ui.notify") as mock_notify,
    ):
        mock_resp_get = MagicMock()
        mock_resp_get.ok = True
        mock_resp_get.headers = {
            "Content-Type": "image/jpeg",
            "X-Mock-Meter-Value": "00452.91241",
            "X-Mock-Digital-Value": "00452",
            "X-Mock-Analog-Value": "9124",
        }
        mock_resp_get.content = b"fake_jpeg_bytes"
        mock_get.return_value = mock_resp_get

        asyncio.run(page._generate_mock_frame())
        assert "data:image/jpeg;base64," in page.mock_img_src
        assert page.mock_meta_meter_val.text == "00452.91241"
        assert page.mock_meta_dig_val.text == "00452"
        assert page.mock_meta_ana_val.text == "9124"

        # Test ticker reset
        mock_resp_post = MagicMock()
        mock_resp_post.ok = True
        mock_post.return_value = mock_resp_post

        asyncio.run(page._reset_mock_ticker())
        mock_notify.assert_called_with(
            "Mock camera ticker reset to 100.0", type="positive"
        )


def test_api_console_page_sync_state_from_url():
    page = ApiConsolePage()
    url = "/api/mock_camera?mode=ticker&value=00123.45678&rate=0.02&rotate=45&glare=true&glare_pos=100,200&noise=12&blur=2&brightness=1.2&contrast=1.3&lcd_color=red&lcd_bg=black&needle_color=white&width=800&height=600&digit1=1&analog1=2.5"
    page.sync_state_from_url(url)
    assert page.mock_mode == "ticker"
    assert page.mock_value == "00123.45678"
    assert page.mock_rate == 0.02
    assert page.mock_rotate == 45.0
    assert page.mock_glare is True
    assert page.mock_glare_pos == "100,200"
    assert page.mock_noise == 12.0
    assert page.mock_blur == 2.0
    assert page.mock_brightness == 1.2
    assert page.mock_contrast == 1.3
    assert page.mock_lcd_color == "red"
    assert page.mock_lcd_bg == "black"
    assert page.mock_needle_color == "white"
    assert page.mock_width == 800
    assert page.mock_height == 600
    assert page.mock_res_preset == "800x600"
    assert page.mock_digit_overrides[0] == "1"
    assert page.mock_analog_overrides[0] == "2.5"


def test_api_console_page_execute_mock_query():
    page = ApiConsolePage()
    page.mock_url_display = MagicMock(value="/api/mock_camera?value=00999.88888")
    page.mock_img_elem = MagicMock()
    with patch("gui.page_api_console.ui.notify") as mock_notify:
        asyncio.run(page._execute_mock_query())
        assert page.mock_value == "00999.88888"
        assert (
            "00999.88888" in page.mock_img_src
            or "data:image/jpeg;base64," in page.mock_img_src
        )
        mock_notify.assert_called_with(
            "Camera snapshot updated from query parameters", type="positive"
        )


def test_api_console_page_reset_to_defaults():
    page = ApiConsolePage()
    page.mock_mode = "ticker"
    page.mock_value = "00999.11111"
    page.mock_rotate = 90.0
    page.mock_glare = True
    page.mock_noise = 25.0
    page.mock_width = 1600
    page.mock_height = 1200
    page.mock_res_preset = "1600x1200"
    page.mock_digit_overrides = ["1", "2", "3", "4", "5"]
    page.mock_img_elem = MagicMock()

    with patch("gui.page_api_console.ui.notify") as mock_notify:
        asyncio.run(page._reset_to_defaults())
        assert page.mock_mode == "fixed"
        assert page.mock_value == "00452.91241"
        assert page.mock_rotate == 0.0
        assert page.mock_glare is False
        assert page.mock_noise == 0.0
        assert page.mock_width == 640
        assert page.mock_height == 480
        assert page.mock_res_preset == "640x480"
        assert page.mock_digit_overrides == ["", "", "", "", ""]
        mock_notify.assert_called_with(
            "Mock camera parameters reset to default values", type="positive"
        )


def test_api_console_page_apply_as_active_image_source(mock_callbacks):
    page = ApiConsolePage(callbacks=mock_callbacks)
    with patch("gui.page_api_console.ui.notify") as mock_notify:
        page._apply_as_active_image_source()
        mock_callbacks.get_config.assert_called_once()
        mock_callbacks.save_config_file.assert_called_once()
        mock_callbacks.use_config.assert_called_once()
        mock_notify.assert_called()


def test_api_console_scenario_presets():
    from gui.page_api_console import SCENARIO_PRESETS

    page = ApiConsolePage()
    assert len(SCENARIO_PRESETS) >= 5

    # Test applying first preset
    preset = SCENARIO_PRESETS[1]  # Tilted & Noisy
    with patch("gui.page_api_console.ui.notify") as mock_notify:
        asyncio.run(page._apply_scenario_preset(preset))
        assert page.mock_rotate == 15.0
        assert page.mock_noise == 8.0
        mock_notify.assert_called_with(
            f"Applied scenario: {preset['name']}", type="positive"
        )


def test_api_console_curl_generation_and_image_download():
    from gui.page_api_console import generate_curl_command

    cmd = generate_curl_command(
        "GET", "http://localhost:3000/meter", headers={"Accept": "application/json"}
    )
    assert "curl -X GET" in cmd
    assert "-H 'Accept: application/json'" in cmd
    assert "'http://localhost:3000/meter'" in cmd

    page = ApiConsolePage()
    page._raw_mock_bytes = b"sample_jpg_bytes"
    with (
        patch("gui.page_api_console.ui.download") as mock_dl,
        patch("gui.page_api_console.ui.notify"),
    ):
        page._download_mock_image()
        mock_dl.assert_called_once_with(
            b"sample_jpg_bytes", filename="mock_meter_frame.jpg"
        )


def test_api_console_test_in_engine(mock_callbacks):
    page = ApiConsolePage(callbacks=mock_callbacks)
    mock_result = MagicMock()
    mock_result.value = "00452.91241"
    mock_result.readouts = [
        MagicMock(name="digit1", value="0", confidence=99.2),
        MagicMock(name="analog1", value="9.1", confidence=98.5),
    ]
    mock_callbacks.get_meter_data.return_value = mock_result
    mock_callbacks.get_config.return_value = Config()

    with (
        patch("gui.page_api_console.ui.dialog") as mock_dialog,
        patch("gui.page_api_console.ui.card"),
        patch("gui.page_api_console.ui.notify"),
    ):
        mock_dialog.return_value.__enter__ = MagicMock()
        mock_dialog.return_value.__exit__ = MagicMock()

        # 1. Dedicated mock config mode (default)
        assert page.mock_test_config_mode == "dedicated"
        asyncio.run(page._test_in_digitizer_engine())
        assert mock_callbacks.get_meter_data.call_count == 1
        call_args = mock_callbacks.get_meter_data.call_args
        # Should have passed a generated Config object
        assert isinstance(call_args[0][2], Config)
        assert len(call_args[0][2].digital_readout.cut_images) == 5

        # 2. Active config mode
        page.mock_test_config_mode = "active"
        asyncio.run(page._test_in_digitizer_engine())
        assert mock_callbacks.get_meter_data.call_count == 2
        call_args2 = mock_callbacks.get_meter_data.call_args
        assert call_args2[0][2] is None

        # 3. Dedicated mock config with custom overrides active
        page.mock_test_config_mode = "dedicated"
        custom_cfg = MeterImageGenerator.create_mock_meter_config(width=640, height=480)
        custom_cfg.meter_configs[0].name = "customized_mock"
        page.mock_custom_config = custom_cfg
        page.mock_custom_config_active = True
        asyncio.run(page._test_in_digitizer_engine())
        assert mock_callbacks.get_meter_data.call_count == 3
        call_args3 = mock_callbacks.get_meter_data.call_args
        assert call_args3[0][2] is custom_cfg
        assert call_args3[0][2].meter_configs[0].name == "customized_mock"


def test_api_console_open_mock_config_dialog(mock_callbacks):
    page = ApiConsolePage(callbacks=mock_callbacks)
    with patch("gui.page_api_console.MockConfigDialog") as mock_dialog_cls:
        page._open_mock_config_dialog()
        mock_dialog_cls.assert_called_once()
        dialog_instance = mock_dialog_cls.return_value
        dialog_instance.open.assert_called_once()


def test_api_console_toggle_overlay_rois(mock_callbacks):
    page = ApiConsolePage(callbacks=mock_callbacks)
    assert page.mock_show_rois is False
    mock_event = MagicMock(value=True)
    asyncio.run(page._toggle_mock_show_rois(mock_event))
    assert page.mock_show_rois is True
    assert "data:image/jpeg;base64," in page.mock_img_src


def test_consumption_card(mock_callbacks):
    from datetime import datetime

    from nicegui import ui

    from storage.base import ConsumptionRecord

    # Test empty records
    card = ConsumptionCard(mock_callbacks)
    with ui.column() as container:
        card.render(container)
    mock_callbacks.get_storage.assert_called()

    # Test with records in differential mode (Liters and m3)
    mock_storage = mock_callbacks.get_storage()
    mock_storage.get_consumption.return_value = [
        ConsumptionRecord(
            bucket="2026-09-10",
            start_time=datetime(2026, 9, 10, 0, 0),
            end_time=datetime(2026, 9, 10, 23, 59),
            meter_name="total",
            unit="m3",
            consumption=0.250,
            start_value=300.000,
            end_value=300.250,
            min_value=300.000,
            max_value=300.250,
            reading_count=10,
        ),
        ConsumptionRecord(
            bucket="2026-09-11",
            start_time=datetime(2026, 9, 11, 0, 0),
            end_time=datetime(2026, 9, 11, 23, 59),
            meter_name="total",
            unit="m3",
            consumption=0.300,
            start_value=300.250,
            end_value=300.550,
            min_value=300.250,
            max_value=300.550,
            reading_count=12,
        ),
    ]

    card_diff = ConsumptionCard(mock_callbacks)
    card_diff.view_mode = "differential"
    card_diff.chart_style = "line"
    card_diff.unit_mode = "m3"
    with ui.column() as c_diff:
        card_diff.render(c_diff)

    # Test with records in cumulative mode (meter index)
    card_cum = ConsumptionCard(mock_callbacks)
    card_cum.view_mode = "cumulative"
    with ui.column() as c_cum:
        card_cum.render(c_cum)

    # Test with records in combo mode with Liters (L) unit
    card_combo = ConsumptionCard(mock_callbacks)
    card_combo.view_mode = "combo"
    card_combo.unit_mode = "L"
    with ui.column() as c_combo:
        card_combo.render(c_combo)

    # Test when storage backend is disabled (None)
    mock_callbacks.get_storage.return_value = None
    card_disabled = ConsumptionCard(mock_callbacks)
    with ui.column() as c_dis:
        card_disabled.render(c_dis)


def test_history_table_card(mock_callbacks):
    from datetime import datetime

    from nicegui import ui

    from storage.base import MeterReading, ReadingRecord

    # 1. Test empty records
    card = HistoryTableCard(mock_callbacks)
    with ui.column() as container:
        card.render(container)
    mock_callbacks.get_storage.assert_called()

    # 2. Test with sample records
    mock_storage = mock_callbacks.get_storage()
    records = [
        ReadingRecord(
            id=1,
            timestamp=datetime(2026, 9, 14, 12, 0, 0),
            meters={
                "total": MeterReading(
                    value=452.9124, unit="m3", quality="good", confidence=99.2
                ),
            },
            digital_results={"0": "4", "1": "5", "2": "2"},
            analog_results={"0": "9", "1": "1"},
            error="",
            frame_type="full",
            frame_path="/tmp/frame1.jpg",
            flow_detected=True,
            confidence_scores={"digital_0": 99.0, "analog_0": 98.5},
        ),
        ReadingRecord(
            id=2,
            timestamp=datetime(2026, 9, 14, 12, 5, 0),
            meters={
                "total": MeterReading(
                    value=None, raw_value="00452.9124", quality="error", confidence=0.0
                ),
            },
            digital_results={},
            analog_results={},
            error="Rate of change exceeded limit",
            frame_type=None,
            frame_path=None,
            flow_detected=False,
            confidence_scores={},
        ),
    ]
    mock_storage.get_readings.return_value = records

    # Render with default filters (all)
    card_all = HistoryTableCard(mock_callbacks)
    with ui.column() as c_all:
        card_all.render(c_all)

    # Render with category filter: good
    card_good = HistoryTableCard(mock_callbacks)
    card_good.category_filter = "good"
    with ui.column() as c_good:
        card_good.render(c_good)

    # Render with category filter: anomalies
    card_anom = HistoryTableCard(mock_callbacks)
    card_anom.category_filter = "anomalies"
    with ui.column() as c_anom:
        card_anom.render(c_anom)

    # Render with category filter: flow
    card_flow = HistoryTableCard(mock_callbacks)
    card_flow.category_filter = "flow"
    with ui.column() as c_flow:
        card_flow.render(c_flow)

    # Render with search query
    card_search = HistoryTableCard(mock_callbacks)
    card_search.search_query = "452.9124"
    with ui.column() as c_search:
        card_search.render(c_search)

    # Test open_reading_dialog with and without snapshot frame
    mock_callbacks.get_frame_data_uri.return_value = "data:image/jpeg;base64,AAAA"
    card_all.open_reading_dialog(records[0])

    mock_callbacks.get_frame_data_uri.return_value = None
    card_all.open_reading_dialog(records[1])

    # Test disabled backend
    mock_callbacks.get_storage.return_value = None
    card_disabled = HistoryTableCard(mock_callbacks)
    with ui.column() as c_dis:
        card_disabled.render(c_dis)


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


def test_services_status_card_with_error(mock_callbacks):
    card = ServicesStatusCard(mock_callbacks)
    card.render()

    # Update with poller error state
    poller_err_data = {
        "enabled": True,
        "running": True,
        "interval_seconds": 60,
        "total_runs": 5,
        "successful_runs": 4,
        "failed_runs": 1,
        "last_error": "Could not open model file: Model allocation is null",
        "next_run": "2026-09-14T17:30:00Z",
    }
    mqtt_data = {
        "enabled": True,
        "connected": True,
        "broker": "localhost",
        "port": 1883,
        "topic_prefix": "watermeter",
        "ha_discovery": True,
    }
    card.update_data(poller_err_data, mqtt_data)
    assert (
        card._poller_data["last_error"]
        == "Could not open model file: Model allocation is null"
    )
