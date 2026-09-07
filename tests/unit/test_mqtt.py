from unittest.mock import MagicMock

from configuration import MQTT
from data_classes import MeterConfig
from mqtt.discovery import build_homeassistant_discovery_payloads
from mqtt.client import MQTTService
from processor.digitizer import MeterResult, MeterValue


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

    payloads = build_homeassistant_discovery_payloads(mqtt_cfg, meters, version="8.0.0")
    assert (
        len(payloads) == 6
    )  # 2 sensors per meter (value, conf) + 2 system sensors (error, proc_time)

    topics = [p[0] for p in payloads]
    assert "homeassistant/sensor/water_meter_digitizer/main_value/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/main_confidence/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/garden_value/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/last_error/config" in topics
    assert "homeassistant/sensor/water_meter_digitizer/processing_time/config" in topics

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
