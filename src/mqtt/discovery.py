from typing import Any

from configuration import MQTT
from data_classes import MeterConfig
from version import __version__


def build_homeassistant_discovery_payloads(
    mqtt_config: MQTT,
    meter_configs: list[MeterConfig],
    version: str = __version__,
) -> list[tuple[str, dict[str, Any]]]:
    """Generate Home Assistant MQTT Auto-Discovery topics and configuration payloads."""
    payloads: list[tuple[str, dict[str, Any]]] = []
    device_id = mqtt_config.device_id or "water_meter_digitizer"
    device_name = mqtt_config.device_name or "Water Meter Digitizer"
    prefix = mqtt_config.topic_prefix or "watermeter"
    disc_prefix = mqtt_config.discovery_prefix or "homeassistant"

    device_block = {
        "identifiers": [device_id],
        "name": device_name,
        "model": "AI Edge Water Meter Digitizer",
        "sw_version": version,
    }

    # If no meters are configured yet, create discovery for a default "main" meter
    meters_to_publish = (
        meter_configs
        if meter_configs
        else [MeterConfig(name="main", format="", unit="m³")]
    )

    for meter in meters_to_publish:
        meter_slug = meter.name.lower().replace(" ", "_")
        unit = meter.unit if meter.unit else "m³"

        # Determine device class based on unit or meter name
        unit_lower = unit.lower()
        if (
            "gal" in unit_lower
            or "m3" in unit_lower
            or "m³" in unit_lower
            or "l" in unit_lower
            or "water" in meter_slug
        ):
            device_class = "water"
            icon = "mdi:water"
        elif "gas" in meter_slug or "gas" in unit_lower:
            device_class = "gas"
            icon = "mdi:fire"
        elif "kwh" in unit_lower or "wh" in unit_lower or "energy" in meter_slug:
            device_class = "energy"
            icon = "mdi:lightning-bolt"
        else:
            device_class = "water"
            icon = "mdi:gauge"

        # 1. Main Reading Value Sensor
        value_topic = f"{disc_prefix}/sensor/{device_id}/{meter_slug}_value/config"
        value_payload: dict[str, Any] = {
            "name": f"{device_name} {meter.name.title()}",
            "unique_id": f"{device_id}_{meter_slug}_value",
            "state_topic": f"{prefix}/{meter.name}/value",
            "json_attributes_topic": f"{prefix}/{meter.name}/attributes",
            "availability_topic": f"{prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline",
            "unit_of_measurement": unit,
            "device_class": device_class,
            "state_class": "total_increasing",
            "icon": icon,
            "device": device_block,
        }
        payloads.append((value_topic, value_payload))

        # 2. Confidence Sensor (Diagnostic)
        conf_topic = f"{disc_prefix}/sensor/{device_id}/{meter_slug}_confidence/config"
        conf_payload: dict[str, Any] = {
            "name": f"{device_name} {meter.name.title()} Confidence",
            "unique_id": f"{device_id}_{meter_slug}_confidence",
            "state_topic": f"{prefix}/{meter.name}/confidence",
            "availability_topic": f"{prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline",
            "unit_of_measurement": "%",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "icon": "mdi:percent-outline",
            "device": device_block,
        }
        payloads.append((conf_topic, conf_payload))

    # 3. System Error Sensor (Diagnostic)
    error_topic = f"{disc_prefix}/sensor/{device_id}/last_error/config"
    error_payload: dict[str, Any] = {
        "name": f"{device_name} Last Error",
        "unique_id": f"{device_id}_last_error",
        "state_topic": f"{prefix}/error",
        "availability_topic": f"{prefix}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "entity_category": "diagnostic",
        "icon": "mdi:alert-circle-outline",
        "device": device_block,
    }
    payloads.append((error_topic, error_payload))

    # 4. Processing Time Sensor (Diagnostic)
    proc_topic = f"{disc_prefix}/sensor/{device_id}/processing_time/config"
    proc_payload: dict[str, Any] = {
        "name": f"{device_name} Processing Time",
        "unique_id": f"{device_id}_processing_time",
        "state_topic": f"{prefix}/processing_time",
        "availability_topic": f"{prefix}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "unit_of_measurement": "s",
        "state_class": "measurement",
        "entity_category": "diagnostic",
        "icon": "mdi:timer-outline",
        "device": device_block,
    }
    payloads.append((proc_topic, proc_payload))

    # 5. Leak Alert Binary Sensor
    leak_alert_topic = f"{disc_prefix}/binary_sensor/{device_id}/leak_alert/config"
    leak_alert_payload: dict[str, Any] = {
        "name": f"{device_name} Leak Alert",
        "unique_id": f"{device_id}_leak_alert",
        "state_topic": f"{prefix}/leak/alert",
        "availability_topic": f"{prefix}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device_class": "problem",
        "icon": "mdi:water-alert",
        "device": device_block,
    }
    payloads.append((leak_alert_topic, leak_alert_payload))

    # 6. Leak Status Sensor
    leak_status_topic = f"{disc_prefix}/sensor/{device_id}/leak_status/config"
    leak_status_payload: dict[str, Any] = {
        "name": f"{device_name} Leak Status",
        "unique_id": f"{device_id}_leak_status",
        "state_topic": f"{prefix}/leak/state",
        "json_attributes_topic": f"{prefix}/leak/status",
        "availability_topic": f"{prefix}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "icon": "mdi:water-check",
        "device": device_block,
    }
    payloads.append((leak_status_topic, leak_status_payload))

    # 7. Continuous Flow Duration Sensor
    flow_dur_topic = f"{disc_prefix}/sensor/{device_id}/flow_duration/config"
    flow_dur_payload: dict[str, Any] = {
        "name": f"{device_name} Continuous Flow Duration",
        "unique_id": f"{device_id}_flow_duration",
        "state_topic": f"{prefix}/leak/duration",
        "availability_topic": f"{prefix}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "unit_of_measurement": "min",
        "state_class": "measurement",
        "icon": "mdi:timer-sand",
        "device": device_block,
    }
    payloads.append((flow_dur_topic, flow_dur_payload))

    return payloads
