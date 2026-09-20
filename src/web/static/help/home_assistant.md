### Home Assistant MQTT Auto-Discovery & Integrations

The digitizer automatically announces entities to Home Assistant when MQTT discovery is enabled:

- **Auto-Discovery Prefix**: `homeassistant/sensor/watermeter/`
- **Main Water Sensor**: State topic with unit (`m³`), `device_class: water`, and `state_class: total_increasing`.
- **Diagnostic Entities**: Camera reachability, inference latency, uptime, and zero-flow leak alerts.
- **Consumption Analytics**: Directly compatible with Home Assistant's Energy Dashboard.
