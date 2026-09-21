"""Unit tests for MQTT Home Assistant auto-discovery payloads and MQTTService lifecycle."""

from unittest.mock import MagicMock, patch

from configuration import MQTT
from data_classes import MeterConfig
from leak.models import LeakEvent, LeakState, ZeroFlowStatus
from mqtt.client import MQTTService
from mqtt.discovery import build_homeassistant_discovery_payloads


def test_discovery_payload_device_classes():
    mqtt_cfg = MQTT(
        enabled=True,
        topic_prefix="watermeter",
        device_id="digitizer_test",
        device_name="Digitizer Test",
    )

    # Test distinct meter units / names mapped to appropriate device_class
    meters = [
        MeterConfig(name="water_main", format="{d1}", unit="m3"),
        MeterConfig(name="gas_meter", format="{d1}", unit="ccf"),
        MeterConfig(name="power_meter", format="{d1}", unit="kWh"),
        MeterConfig(name="generic_dial", format="{d1}", unit="counts"),
    ]

    payloads = build_homeassistant_discovery_payloads(mqtt_cfg, meters)
    payload_dict = {topic: p for topic, p in payloads}

    water_p = payload_dict[
        "homeassistant/sensor/digitizer_test/water_main_value/config"
    ]
    assert water_p["device_class"] == "water"
    assert water_p["icon"] == "mdi:water"

    gas_p = payload_dict["homeassistant/sensor/digitizer_test/gas_meter_value/config"]
    assert gas_p["device_class"] == "gas"
    assert gas_p["icon"] == "mdi:fire"

    power_p = payload_dict[
        "homeassistant/sensor/digitizer_test/power_meter_value/config"
    ]
    assert power_p["device_class"] == "energy"
    assert power_p["icon"] == "mdi:lightning-bolt"

    generic_p = payload_dict[
        "homeassistant/sensor/digitizer_test/generic_dial_value/config"
    ]
    assert generic_p["icon"] == "mdi:gauge"


def test_discovery_empty_meter_fallback():
    mqtt_cfg = MQTT(enabled=True, device_id="default_dev")
    # Empty meter configs list
    payloads = build_homeassistant_discovery_payloads(mqtt_cfg, [])
    topics = [t for t, _ in payloads]
    assert "homeassistant/sensor/default_dev/main_value/config" in topics


def test_mqtt_service_lifecycle_and_callbacks():
    mqtt_cfg = MQTT(
        enabled=True,
        broker="mqtt.local",
        port=8883,
        username="user1",
        password="pwd",
        tls=True,
        homeassistant_discovery=True,
    )

    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        service = MQTTService(config=mqtt_cfg)
        assert service._client is not None
        mock_client.username_pw_set.assert_called_once_with(
            username="user1", password="pwd"
        )
        mock_client.tls_set.assert_called_once()
        mock_client.will_set.assert_called_once()

        # Test start
        service.start()
        mock_client.connect_async.assert_called_once_with(
            host="mqtt.local", port=8883, keepalive=60
        )
        mock_client.loop_start.assert_called_once()

        # Test _on_connect (success)
        service._on_connect(mock_client, None, None, 0)
        assert service.is_connected is True

        # Test _on_disconnect
        service._on_disconnect(mock_client, None, None, 0)
        assert service.is_connected is False

        # Test _on_connect (failure code)
        service._on_connect(mock_client, None, None, 5)
        assert service.is_connected is False

        # Test stop
        service.is_connected = True
        service.stop()
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert service.is_connected is False


def test_mqtt_service_publish_zero_flow_status():
    from datetime import datetime

    mqtt_cfg = MQTT(enabled=True, topic_prefix="watermeter")
    service = MQTTService(config=mqtt_cfg)

    mock_client = MagicMock()
    service._client = mock_client
    service.is_connected = True

    now = datetime.now().astimezone()
    status = ZeroFlowStatus(
        enabled=True,
        state=LeakState.LEAK_DETECTED,
        meter_name="total",
        current_flow_duration_seconds=3600.0,
        current_flow_volume=0.050,
        active_event=LeakEvent(
            event_id="leak-test-1",
            start_time=now,
            meter_name="total",
            initial_value=100.0,
            current_value=100.05,
            leaked_volume=0.05,
            duration_seconds=3600.0,
        ),
    )

    service.publish_zero_flow_status(status)

    published_topics = [call[1]["topic"] for call in mock_client.publish.call_args_list]
    assert "watermeter/leak/alert" in published_topics
    assert "watermeter/leak/state" in published_topics
    assert "watermeter/leak/duration" in published_topics
    assert "watermeter/leak/status" in published_topics

    # Check alert payload is "ON" when LEAK_DETECTED
    alert_call = next(
        call
        for call in mock_client.publish.call_args_list
        if call[1]["topic"] == "watermeter/leak/alert"
    )
    assert alert_call[1]["payload"] == "ON"


def test_mqtt_service_status_dictionary():
    mqtt_cfg = MQTT(enabled=True, broker="broker.local", port=1883)
    service = MQTTService(config=mqtt_cfg)
    service.is_connected = True
    service.last_published_topics = {"watermeter/total/value": "123.45"}

    stat = service.get_status()
    assert stat["enabled"] is True
    assert stat["connected"] is True
    assert stat["broker"] == "broker.local"
    assert stat["port"] == 1883
    assert stat["last_published_topics"]["watermeter/total/value"] == "123.45"
