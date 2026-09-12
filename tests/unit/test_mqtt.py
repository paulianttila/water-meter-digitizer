from unittest.mock import MagicMock

from configuration import MQTT
from data_classes import MeterConfig
from mqtt.client import MQTTService
from mqtt.discovery import build_homeassistant_discovery_payloads
from processor.digitizer import MeterResult, MeterValue
from version import __version__


def test_homeassistant_discovery_payload_generation():
    mqtt_cfg = MQTT(
        enabled=True,
        topic_prefix="watermeter",
        discovery_prefix="homeassistant",
        device_id="water_meter_digitizer",
        device_name="Water Meter Digitizer",
    )
    meters = [
        MeterConfig(name="main", format="{d1}", unit="m³"),
        MeterConfig(name="garden", format="{d2}", unit="L"),
    ]

    payloads = build_homeassistant_discovery_payloads(mqtt_cfg, meters)
    # 2 sensors per meter (value, conf) + 2 system sensors + 3 leak sensors = 9
    assert len(payloads) == 9
    assert payloads[0][1]["device"]["sw_version"] == __version__

    topics = [p[0] for p in payloads]
    assert "homeassistant/sensor/water_meter_digitizer/main_value/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/main_confidence/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/garden_value/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/last_error/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/processing_time/config" in topics
    assert (
        "homeassistant/binary_sensor/water_meter_digitizer/leak_alert/config" in topics
    )
    assert "homeassistant/sensor/water_meter_digitizer/leak_status/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/flow_duration/config" in topics

    # Inspect main value sensor config
    main_val_payload = next(
        p[1]
        for p in payloads
        if p[0] == "homeassistant/sensor/water_meter_digitizer/main_value/config"
    )
    assert main_val_payload["name"] == "Water Meter Digitizer Main"
    assert main_val_payload["state_topic"] == "watermeter/main/value"
    assert main_val_payload["state_class"] == "total_increasing"
    assert main_val_payload["device_class"] == "water"
    assert main_val_payload["unit_of_measurement"] == "m³"
    assert main_val_payload["device"]["identifiers"] == ["water_meter_digitizer"]


def test_mqtt_service_publishing():
    mqtt_cfg = MQTT(
        enabled=True,
        broker="localhost",
        port=1883,
        topic_prefix="watermeter",
        retain=True,
    )
    service = MQTTService(
        config=mqtt_cfg,
        meter_configs=[MeterConfig(name="main", format="{d1}", unit="m³")],
    )

    mock_client = MagicMock()
    service._client = mock_client
    service.is_connected = True

    res = MeterResult(
        meters=[
            MeterValue(
                name="main",
                value="123.456",
                unit="m³",
                quality="good",
                confidence=99.2,
            )
        ],
        digital_results={"d1": "1"},
        analog_results={"a1": "2"},
        error="",
    )

    service.publish_meter_result(res, processing_time_sec=1.23)

    # Verify calls
    published_topics = [call[1]["topic"] for call in mock_client.publish.call_args_list]
    assert "watermeter/main/value" in published_topics
    assert "watermeter/main/confidence" in published_topics
    assert "watermeter/main/attributes" in published_topics
    assert "watermeter/main/json" in published_topics
    assert "watermeter/error" in published_topics
    assert "watermeter/processing_time" in published_topics
    assert "watermeter/readout/json" in published_topics

    # Check value payload
    value_call = next(
        call
        for call in mock_client.publish.call_args_list
        if call[1]["topic"] == "watermeter/main/value"
    )
    assert value_call[1]["payload"] == "123.456"
    assert value_call[1]["retain"] is True


def test_mqtt_service_status():
    mqtt_cfg = MQTT(enabled=True, broker="mqtt.home", port=1883)
    service = MQTTService(config=mqtt_cfg)
    status = service.get_status()

    assert status["enabled"] is True
    assert status["broker"] == "mqtt.home"
    assert status["connected"] is False


def test_mqtt_on_connect_fail():
    mqtt_cfg = MQTT(enabled=True, broker="nonexistent.host", port=1883)
    service = MQTTService(config=mqtt_cfg)
    assert service.is_connected is False
    assert service._connect_failed_logged is False

    service._on_connect_fail(None, None)
    assert service.is_connected is False
    assert service._connect_failed_logged is True

    # Reconnect success resets flag
    service._on_connect(None, None, None, 0)
    assert service.is_connected is True
    assert service._connect_failed_logged is False
