# MQTT Topic & Payload Reference

The **Water Meter Digitizer** publishes structured telemetry over MQTT for simple integration into any automation engine (Home Assistant, openHAB, Node-RED, ioBroker, or custom scripts).

---

## 📡 Topic Hierarchy (Default Prefix: `watermeter/`)

| Topic | Example Payload | Retained | Description |
| :--- | :--- | :--- | :--- |
| `watermeter/status` | `online` / `offline` | Yes | LWT (Last Will and Testament) availability topic. |
| `watermeter/<meter_name>/value` | `00452.91241` | Yes | Latest processed meter reading value. |
| `watermeter/<meter_name>/rate` | `0.015` | Yes | Flow rate calculated against previous interval. |
| `watermeter/<meter_name>/confidence` | `98.6` | Yes | Minimum neural network classification confidence (%). |
| `watermeter/<meter_name>/json` | `{"value": 452.91, ...}` | Yes | Structured JSON record for the individual meter. |
| `watermeter/readout/json` | *(See schema below)* | Yes | Comprehensive full-system readout JSON payload. |
| `watermeter/leak/state` | `OK` / `LEAK_ALERT` | Yes | Zero-flow leak monitor status. |
| `watermeter/leak/attributes` | `{"flow_seconds": 120, ...}` | Yes | Extended telemetry for leak events. |

---

## 📋 Comprehensive Readout Schema (`watermeter/readout/json`)

```json
{
  "timestamp": "2026-09-12T11:25:07+03:00",
  "error": "",
  "meters": [
    {
      "name": "total",
      "value": "00452.91241",
      "unprocessed_value": "00452.91241",
      "confidence": 96.2,
      "rate": 0.000,
      "unit": "m³"
    }
  ],
  "digital_results": {
    "digit1": "0",
    "digit2": "0",
    "digit3": "4",
    "digit4": "5",
    "digit5": "2"
  },
  "analog_results": {
    "analog1": "9",
    "analog2": "1",
    "analog3": "2",
    "analog4": "4"
  },
  "confidence_scores": {
    "digit1": 85.2,
    "digit2": 91.3,
    "digit3": 99.9,
    "digit4": 90.9,
    "digit5": 100.0,
    "analog1": 99.2,
    "analog2": 98.9,
    "analog3": 100.0,
    "analog4": 100.0
  }
}
```
