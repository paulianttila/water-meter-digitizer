# 🏡 Integrations & API Reference

[🏠 Wiki Home](Home) • [◀ Previous: Dashboard, Features & Tools Guide](Dashboard-&-Features-Guide) • [Next: Configuration & Storage Manual ▶](Configuration-&-Storage-Manual)

---

The **Water Meter Digitizer** is designed for seamless integration into smart home systems and custom automation workflows via **Home Assistant MQTT Auto-Discovery**, **openHAB 3/4**, **Structured MQTT Topics**, and a comprehensive **REST API**.

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

### Example Lovelace Mini-Graph Card
Using the popular `custom:mini-graph-card`:
```yaml
type: custom:mini-graph-card
name: 💧 Water Flow Rate
entities:
  - entity: sensor.water_meter_digitizer_flow_rate
    name: Flow Rate
    color: '#00e5ff'
line_width: 2
hours_to_show: 24
points_per_hour: 4
show:
  fill: fade
  extrema: true
  labels: true
color_thresholds:
  - value: 0.0
    color: '#22c55e'
  - value: 0.05
    color: '#eab308'
  - value: 0.20
    color: '#ef4444'
```

---

## 🏠 2. openHAB 3 / 4 Integration

For openHAB deployments using the Generic MQTT Binding:

### Things Configuration (`watermeter.things`)
```java
Bridge mqtt:broker:myBroker [ host="192.168.1.100", port=1883 ] {
    Thing topic watermeter "Water Meter Digitizer" {
        Channels:
            Type number : total_value "Total Reading" [
                stateTopic="watermeter/total/value"
            ]
            Type number : flow_rate "Flow Rate" [
                stateTopic="watermeter/total/rate"
            ]
            Type number : confidence "Vision Confidence" [
                stateTopic="watermeter/total/confidence"
            ]
            Type switch : leak_alert "Leak Alert" [
                stateTopic="watermeter/leak/detected",
                on="true",
                off="false"
            ]
            Type string : status "System Availability" [
                stateTopic="watermeter/status"
            ]
    }
}
```

### Items Configuration (`watermeter.items`)
```java
Number:VolumeWater WaterMeter_Total "Cumulative Reading [%.3f m³]" <water> { channel="mqtt:topic:myBroker:watermeter:total_value" }
Number:VolumetricFlowRate WaterMeter_FlowRate "Current Flow Rate [%.4f m³/h]" <flow> { channel="mqtt:topic:myBroker:watermeter:flow_rate" }
Number WaterMeter_Confidence "Vision Confidence [%.1f %%]" <qualityofservice> { channel="mqtt:topic:myBroker:watermeter:confidence" }
Switch WaterMeter_LeakAlert "Continuous Leak Alarm" <alarm> { channel="mqtt:topic:myBroker:watermeter:leak_alert" }
String WaterMeter_Status "Digitizer Status [%s]" <status> { channel="mqtt:topic:myBroker:watermeter:status" }
```

---

## 📡 3. MQTT Topic & Telemetry Schema

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
  "warning": "",
  "valid": true,
  "meters": [
    {
      "name": "total",
      "value": "00452.91241",
      "unprocessed_value": "00452.91241",
      "quality": "good",
      "confidence": 94.7,
      "min_confidence": 94.7,
      "filled_digits": 0,
      "valid": true,
      "warning": "",
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

## 🔌 4. REST API Reference

Interactive API documentation and schema inspection are available live at:
- **Swagger UI**: `http://<digitizer-ip>:3000/docs`
- **ReDoc**: `http://<digitizer-ip>:3000/redoc`
- **Interactive API Console**: `http://<digitizer-ip>:3000/api_console`

### Primary Endpoints

#### 1. Digitization & Meter Readout
- **`GET /meter`**: Trigger capture from camera, run neural inference, update history, and publish to MQTT.
  - Query params: `format=json|value|raw`, `saveimages=true`, `url=<override_url>`.
  - Returns `HTTP 503` if neural network model files fail to load (`ModelLoadError`).
  - Example: `curl "http://localhost:3000/meter?format=json"`
- **`GET /api/meter/previous_value`**: Retrieve all baseline readings from `prevalue.ini`, including `last_change` timestamp and configured rate/stale thresholds.
- **`GET /set_previous_value`**: Set or adjust the baseline reading for a meter (`name=total&value=00452.91241`).
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
- **`GET /poller/status`**: Active polling cron schedule, next/last run timestamps, consensus window size/buffer, and execution counters.
- **`GET /mqtt/status`**: Broker connection health and message statistics.

#### 5. System Health & Probes
- **`GET /health`**: Full diagnostic report (RSS memory, CPU, cache hits, model latencies).
- **`GET /healthcheck`**: Lightweight Docker/Kubernetes container probe (`Health - OK`).
- **`GET /version`**: Semantic versioning and build information.

---

[🏠 Wiki Home](Home) • [◀ Previous: Dashboard, Features & Tools Guide](Dashboard-&-Features-Guide) • [Next: Configuration & Storage Manual ▶](Configuration-&-Storage-Manual)
