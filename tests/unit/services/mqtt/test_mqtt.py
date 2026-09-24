import ssl
from unittest.mock import MagicMock, patch

from configuration import MQTT
from data_classes import MeterConfig
from processor.digitizer import MeterResult, MeterValue
from services.mqtt.client import MQTTService
from services.mqtt.discovery import build_homeassistant_discovery_payloads
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
    assert main_val_payload["device"]["manufacturer"] == "Water Meter Digitizer"


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


def test_mqtt_service_publishing_when_disconnected():
    mqtt_cfg = MQTT(enabled=True, broker="localhost", port=1883)
    service = MQTTService(config=mqtt_cfg)
    mock_client = MagicMock()
    service._client = mock_client
    service.is_connected = False

    res = MeterResult(
        meters=[MeterValue(name="main", value="100.0", unit="m³")],
        error="",
    )

    # All publish methods should safely no-op when disconnected
    service.publish_meter_result(res)
    service.publish_error("Test error")
    service.publish_discovery()
    service.publish_zero_flow_status({"state": "OK"})

    mock_client.publish.assert_not_called()


def test_mqtt_service_stop_when_disconnected():
    mqtt_cfg = MQTT(enabled=True, broker="localhost", port=1883)
    service = MQTTService(config=mqtt_cfg)
    mock_client = MagicMock()
    service._client = mock_client
    service.is_connected = False

    service.stop()

    # Disconnect & loop_stop should be called, but offline message should not be published
    mock_client.publish.assert_not_called()
    mock_client.disconnect.assert_called_once()
    mock_client.loop_stop.assert_called_once()
    assert service.is_connected is False


def test_mqtt_service_psk_configuration():
    mqtt_cfg = MQTT(
        enabled=True,
        tls_psk_identity="test_user",
        tls_psk="0123456789abcdef",
    )
    service = MQTTService(config=mqtt_cfg)
    assert service._client is not None
    status = service.get_status()
    assert status["has_psk"] is True
    assert status["qos"] == 1
    assert status["protocol"] == "3.1.1"


def test_mqtt_service_psk_via_env_variable(monkeypatch):
    """Verify Docker 12-factor environment variable injection for PSK."""
    from config.main import Config

    monkeypatch.setenv("METER_MQTT__TLS_PSK", "a1b2c3d4e5f6")
    monkeypatch.setenv("METER_MQTT__TLS_PSK_IDENTITY", "docker_meter_node")
    monkeypatch.setenv("METER_MQTT__ENABLED", "true")

    cfg = Config()
    assert cfg.mqtt.tls_psk == "a1b2c3d4e5f6"
    assert cfg.mqtt.tls_psk_identity == "docker_meter_node"
    assert cfg.mqtt.get_resolved_psk() == "a1b2c3d4e5f6"

    service = MQTTService(config=cfg.mqtt)
    assert service.get_status()["has_psk"] is True


def test_mqtt_service_psk_via_docker_secret_file(tmp_path):
    """Verify Docker runtime secret file mount (e.g. /run/secrets/mqtt_psk)."""
    secret_file = tmp_path / "mqtt_psk"
    secret_file.write_text("fedcba6543210987\n")

    mqtt_cfg = MQTT(
        enabled=True,
        tls_psk_identity="docker_secret_node",
        tls_psk_file=str(secret_file),
    )
    assert mqtt_cfg.get_resolved_psk() == "fedcba6543210987"

    service = MQTTService(config=mqtt_cfg)
    assert service.get_status()["has_psk"] is True


def test_mqtt_service_advanced_tls_options(tmp_path):
    ca_cert = tmp_path / "ca.crt"
    ca_cert.write_text("dummy ca cert")
    client_cert = tmp_path / "client.crt"
    client_cert.write_text("dummy client cert")
    client_key = tmp_path / "client.key"
    client_key.write_text("dummy client key")

    mqtt_cfg = MQTT(
        enabled=True,
        tls=True,
        tls_ca_cert=str(ca_cert),
        tls_insecure=True,
        tls_certfile=str(client_cert),
        tls_keyfile=str(client_key),
    )
    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        service = MQTTService(config=mqtt_cfg)
        mock_client.tls_set.assert_called_once()
        _, kwargs = mock_client.tls_set.call_args
        assert kwargs["ca_certs"] == str(ca_cert)
        assert kwargs["certfile"] == str(client_cert)
        assert kwargs["keyfile"] == str(client_key)
        assert kwargs["cert_reqs"] == ssl.CERT_NONE
        mock_client.tls_insecure_set.assert_called_once_with(True)

        stat = service.get_status()
        assert stat["tls"] is True
        assert stat["tls_insecure"] is True


def test_mqtt_service_configurable_qos():
    mqtt_cfg = MQTT(
        enabled=True,
        broker="localhost",
        port=1883,
        qos=2,
    )
    service = MQTTService(config=mqtt_cfg)
    mock_client = MagicMock()
    service._client = mock_client
    service.is_connected = True

    res = MeterResult(
        meters=[MeterValue(name="main", value="200.0", unit="m³")],
        error="",
    )
    service.publish_meter_result(res)

    for call in mock_client.publish.call_args_list:
        assert call[1]["qos"] == 2

    # publish error
    service.publish_error("fail")
    assert mock_client.publish.call_args[1]["qos"] == 2


def test_mqtt_service_protocol_versions():
    cfg_5 = MQTT(enabled=True, protocol="5.0")
    svc_5 = MQTTService(config=cfg_5)
    assert svc_5.get_status()["protocol"] == "5.0"

    cfg_31 = MQTT(enabled=True, protocol="3.1")
    svc_31 = MQTTService(config=cfg_31)
    assert svc_31.get_status()["protocol"] == "3.1"
