# 🏡 Integrations & API Reference

The **Water Meter Digitizer** is designed for seamless integration into smart home systems and custom automation workflows via **Home Assistant MQTT Auto-Discovery**, **openHAB**, **Structured MQTT Topics**, and a comprehensive **REST API**.

---

## 🏡 1. Home Assistant Integration

### Zero-Configuration via MQTT Auto-Discovery
1. Enable MQTT Discovery in `config.ini`:
   ```ini
   [MQTT]
   Enabled = True
   Broker = 192.168.1.100
   Port = 1883
   TopicPrefix = watermeter
   HomeassistantDiscovery = True
   ```
2. Start the service. In Home Assistant, navigate to **Settings ➔ Devices & Services ➔ MQTT**.
3. The **Water Meter Digitizer** device will be automatically discovered with pre-configured sensor entities.

### Discovered Home Assistant Entities
| Entity ID | Type | Device Class | State Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sensor.water_meter_digitizer_total` | Sensor | `water` | `total_increasing` | Cumulative water volume (`m³` or `L`). |
| `sensor.water_meter_digitizer_flow_rate` | Sensor | `volume_flow_rate` | `measurement` | Instantaneous flow rate (`m³/h` or `L/min`). |
| `sensor.water_meter_digitizer_confidence` | Sensor | `power_factor` | `measurement` | Neural vision model confidence (`%`). |
| `binary_sensor.water_meter_digitizer_leak_alert` | Binary Sensor | `problem` / `moisture` | - | Zero-flow continuous leak alert (`ON`/`OFF`). |
| `sensor.water_meter_digitizer_system_status` | Diagnostic | - | - | Overall system health (`healthy`, `degraded`). |

### Home Assistant Energy & Water Dashboard
1. Open **Settings ➔ Dashboards ➔ Energy**.
2. Under **Water Consumption**, click **Add Water Source**.
3. Select `sensor.water_meter_digitizer_total`.
4. Click **Save** to track hourly and daily water usage charts.

---

## 📡 2. MQTT Topic & Telemetry Schema

All telemetry is published under the configured `TopicPrefix` (default: `watermeter/`):

| Topic | Example Payload | Retained | Description |
| :--- | :--- | :--- | :--- |
| `<prefix>/status` | `online` / `offline` | Yes | LWT (Last Will and Testament) availability topic. |
| `<prefix>/<meter_name>/value` | `00452.91241` | Yes | Processed, validated numerical meter reading. |
| `<prefix>/<meter_name>/raw` | `00452.91241` | Yes | Raw uncorrected vision readout string. |
| `<prefix>/<meter_name>/rate` | `0.015` | Yes | Computed flow rate per time delta. |
| `<prefix>/<meter_name>/confidence` | `98.6` | Yes | Lowest individual neural classification confidence (%). |
| `<prefix>/<meter_name>/json` | `{"value": 452.91, ...}` | Yes | Structured JSON payload for the specific meter. |
| `<prefix>/readout/json` | *(See JSON schema below)* | Yes | Comprehensive full-system telemetry payload. |
| `<prefix>/leak/state` | `OK` / `LEAK_ALERT` | Yes | Zero-flow continuous leak monitor state. |
| `<prefix>/leak/detected` | `false` / `true` | Yes | Boolean leak alarm indicator. |

### Comprehensive Readout JSON Payload (`<prefix>/readout/json`)
```json
{
  "timestamp": "2026-09-14T18:30:00+03:00",
  "error": "",
  "meters": [
    {
      "name": "total",
      "value": "00452.91241",
      "unprocessed_value": "00452.91241",
      "confidence": 98.4,
      "rate": 0.0025,
      "unit": "m³"
    }
  ],
  "digital_results": {
    "digit1": "0", "digit2": "0", "digit3": "4", "digit4": "5", "digit5": "2"
  },
  "analog_results": {
    "analog1": "9", "analog2": "1", "analog3": "2", "analog4": "4"
  },
  "confidence_scores": {
    "digit1": 95.2, "digit2": 96.1, "digit3": 99.8, "digit4": 94.7, "digit5": 100.0,
    "analog1": 99.2, "analog2": 98.9, "analog3": 100.0, "analog4": 100.0
  }
}
```

---

## 🔌 3. REST API Reference

Interactive API documentation and schema inspection are available live at:
- **Swagger UI**: `http://<digitizer-ip>:3000/docs`
- **ReDoc**: `http://<digitizer-ip>:3000/redoc`
- **Interactive API Console**: `http://<digitizer-ip>:3000/api_console`

### Primary Endpoints

#### 1. Digitization & Meter Readout
- **`GET /meter`**: Trigger capture from camera, run neural inference, update history, and publish to MQTT.
  - Query params: `format=json|value|html`, `meter=total`, `saveimages=true`.
  - Example: `curl "http://localhost:3000/meter?format=json"`
- **`POST /readout`**: Trigger instantaneous digitization and return parsed JSON.

#### 2. Historical Analytics & Time Machine
- **`GET /history/consumption`**: Query aggregated usage deltas.
  - Query params: `meter_name=total`, `interval=hourly|daily|weekly`, `start=<iso>`, `end=<iso>`.
- **`GET /history/readings`**: Query raw chronological meter records.
- **`GET /history/timeline`**: Chronological frames for Time Machine visual scrubber.
- **`GET /history/frame/{id}/image`**: Retrieve raw WebP/JPEG snapshot image.
- **`GET /history/frame/{id}/diff_image?compare_id={compare_id}`**: Retrieve SSIM visual difference heatmap.

#### 3. Zero-Flow Leak Monitoring
- **`GET /leak/status`**: Current leak tracker state, active flow duration, and volume.
- **`POST /leak/reset`**: Manually acknowledge and reset active continuous flow timer.

#### 4. Service & Poller Control
- **`POST /poller/trigger`**: Force immediate background polling cycle.
- **`GET /poller/status`**: Active polling interval and next execution timestamp.
- **`GET /mqtt/status`**: Broker connection health and message statistics.

#### 5. System Health & Probes
- **`GET /health`**: Full diagnostic report (RSS memory, CPU, cache hits, model latencies).
- **`GET /healthcheck`**: Lightweight Docker/Kubernetes container probe (`Health - OK`).
- **`GET /version`**: Semantic versioning and build information.

---

## ⏭️ Next Step

Read the **[Configuration & Storage Manual](Configuration-&-Storage-Manual.md)** to configure storage backends, automated backups, and snapshot retention limits.
