from unittest.mock import MagicMock

from configuration import Config
from gui.step_services import ServicesStep


def test_services_step_load_and_apply():
    step = ServicesStep(name="Services", set_image_callback=MagicMock())

    # Mock UI elements
    step.poller_enabled = MagicMock(value=False)
    step.poller_interval = MagicMock(value=300)
    step.poller_run_on_startup = MagicMock(value=True)
    step.poller_save_images = MagicMock(value=False)
    step.poller_retry_interval = MagicMock(value=30)

    step.mqtt_enabled = MagicMock(value=False)
    step.mqtt_broker = MagicMock(value="localhost")
    step.mqtt_port = MagicMock(value=1883)
    step.mqtt_username = MagicMock(value="")
    step.mqtt_password = MagicMock(value="")
    step.mqtt_client_id = MagicMock(value="water-meter-digitizer")
    step.mqtt_topic_prefix = MagicMock(value="watermeter")
    step.mqtt_keepalive = MagicMock(value=60)
    step.mqtt_tls = MagicMock(value=False)
    step.mqtt_retain = MagicMock(value=True)
    step.mqtt_ha_discovery = MagicMock(value=True)
    step.mqtt_discovery_prefix = MagicMock(value="homeassistant")
    step.mqtt_device_name = MagicMock(value="Water Meter Digitizer")
    step.mqtt_device_id = MagicMock(value="water_meter_digitizer")

    step.history_enabled = MagicMock(value=True)
    step.history_backend = MagicMock(value="sqlite")
    step.history_retention_days = MagicMock(value=30)
    step.history_max_records = MagicMock(value=50000)
    step.history_auto_vacuum = MagicMock(value=True)
    step.history_prune_interval = MagicMock(value=50)

    step.data_dir = MagicMock(value="/data")
    step.min_confidence_threshold = MagicMock(value=50.0)

    step.zero_flow_enabled = MagicMock(value=False)
    step.zero_flow_meter_name = MagicMock(value="total")
    step.zero_flow_hours = MagicMock(value=2.0)
    step.zero_flow_min_volume = MagicMock(value=0.010)
    step.zero_flow_threshold = MagicMock(value=0.001)
    step.zero_flow_debounce_count = MagicMock(value=2)
    step.zero_flow_max_history = MagicMock(value=50)

    # Test load from config
    config = Config()
    config.poller.enabled = True
    config.poller.interval_seconds = 600
    config.mqtt.enabled = True
    config.mqtt.broker = "192.168.1.50"
    config.history.retention_days = 60
    config.min_confidence_threshold = 75.0
    config.zero_flow_monitor.enabled = True
    config.zero_flow_monitor.continuous_flow_hours = 3.5

    step.load_from_config(config)

    assert step.poller_enabled.value is True
    assert step.poller_interval.value == 600
    assert step.mqtt_enabled.value is True
    assert step.mqtt_broker.value == "192.168.1.50"
    assert step.history_retention_days.value == 60
    assert step.min_confidence_threshold.value == 75.0
    assert step.zero_flow_enabled.value is True
    assert step.zero_flow_hours.value == 3.5

    # Test apply to config
    new_config = Config()
    step.poller_enabled.value = True
    step.poller_interval.value = 120
    step.mqtt_enabled.value = True
    step.mqtt_broker.value = "mqtt.local"
    step.history_backend.value = "memory"
    step.history_retention_days.value = 14
    step.data_dir.value = "/custom_data"
    step.min_confidence_threshold.value = 80.0
    step.zero_flow_enabled.value = True
    step.zero_flow_hours.value = 4.0
    step.zero_flow_min_volume.value = 0.020

    step.apply_to_config(new_config)

    assert new_config.poller.enabled is True
    assert new_config.poller.interval_seconds == 120
    assert new_config.mqtt.enabled is True
    assert new_config.mqtt.broker == "mqtt.local"
    assert new_config.history.retention_days == 14
    assert new_config.data_dir == "/custom_data"
    assert new_config.min_confidence_threshold == 80.0
    assert new_config.zero_flow_monitor.enabled is True
    assert new_config.zero_flow_monitor.continuous_flow_hours == 4.0
    assert new_config.zero_flow_monitor.min_leak_volume == 0.020
