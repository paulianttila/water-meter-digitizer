# Smart Home Integrations (Home Assistant, openHAB, & Custom)

The **Water Meter Digitizer** is designed for seamless integration into home automation platforms using standard protocols: **MQTT**, **Home Assistant MQTT Auto-Discovery**, **openHAB MQTT Binding**, and **REST API / Webhooks**.

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
2. Trigger a readout or start the service.
3. In Home Assistant, navigate to **Settings ➔ Devices & Services ➔ MQTT**.
4. The **Water Meter Digitizer** device will be discovered automatically with all entities configured.

### Discovered Entities
| Entity ID | Type | Device Class | State Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sensor.water_meter_digitizer_total` | Sensor | `water` | `total_increasing` | Cumulative volume reading (`m³` or `L`). |
| `sensor.water_meter_digitizer_flow_rate` | Sensor | `volume_flow_rate` | `measurement` | Current water flow rate (`m³/h` or `L/min`). |
| `sensor.water_meter_digitizer_confidence` | Sensor | `power_factor` | `measurement` | Vision model classification confidence (`%`). |
| `binary_sensor.water_meter_digitizer_leak_alert` | Binary Sensor | `problem` / `moisture` | - | Active zero-flow continuous leak alert (`ON`/`OFF`). |
| `sensor.water_meter_digitizer_system_status` | Diagnostic | - | - | Health status (`healthy`, `degraded`, `unhealthy`). |

### Home Assistant Energy & Water Dashboard
1. Open **Settings ➔ Dashboards ➔ Energy**.
2. Under **Water Consumption**, click **Add Water Source**.
3. Select `sensor.water_meter_digitizer_total`.
4. Click **Save** to track hourly/daily water usage alongside electricity and solar metrics.

### Example Lovelace Cards
```yaml
type: vertical-stack
cards:
  - type: entities
    title: 💧 Main Water Meter
    entities:
      - entity: sensor.water_meter_digitizer_total
        name: Cumulative Reading
      - entity: sensor.water_meter_digitizer_flow_rate
        name: Flow Rate
      - entity: sensor.water_meter_digitizer_confidence
        name: Vision Confidence
      - entity: binary_sensor.water_meter_digitizer_leak_alert
        name: Continuous Leak Alert
  - type: history-graph
    title: Water Flow History (24h)
    hours_to_show: 24
    entities:
      - entity: sensor.water_meter_digitizer_flow_rate
```

---

## 🟠 2. openHAB Integration

openHAB connects to the digitizer via the standard **MQTT Binding**.

### Thing Configuration (`watermeter.things`)
Create a Generic MQTT Thing connected to your MQTT Bridge:

```yaml
Thing mqtt:topic:watermeter "Water Meter Digitizer" (mqtt:broker:myBroker) {
    Channels:
        Type number : total_value "Water Meter Total" [ stateTopic="watermeter/total/value" ]
        Type number : flow_rate   "Current Flow Rate" [ stateTopic="watermeter/total/rate" ]
        Type number : confidence  "Vision Confidence" [ stateTopic="watermeter/total/confidence" ]
        Type string : leak_state  "Leak Alert State"  [ stateTopic="watermeter/leak/state" ]
        Type string : status      "System Status"     [ stateTopic="watermeter/status" ]
}
```

### Items Definition (`watermeter.items`)
```java
Number:Volume          WaterMeter_Total       "Water Meter Total [%.3f m³]"       <water>       { channel="mqtt:topic:watermeter:total_value", stateDescription=""[pattern="%.3f m³"] }
Number:VolumeFlowRate  WaterMeter_FlowRate    "Water Flow Rate [%.3f m³/h]"       <flow>        { channel="mqtt:topic:watermeter:flow_rate" }
Number                 WaterMeter_Confidence  "Vision Confidence [%.1f %%]"       <qualityofservice> { channel="mqtt:topic:watermeter:confidence" }
String                 WaterMeter_LeakState   "Leak Alert [%s]"                   <alarm>       { channel="mqtt:topic:watermeter:leak_state" }
String                 WaterMeter_Status      "Device Availability [%s]"          <status>      { channel="mqtt:topic:watermeter:status" }
```

### Sitemap Example (`default.sitemap`)
```java
sitemap default label="Home Automation" {
    Frame label="Utility Monitoring" {
        Text item=WaterMeter_Total icon="water"
        Text item=WaterMeter_FlowRate icon="flow"
        Text item=WaterMeter_Confidence icon="qualityofservice"
        Text item=WaterMeter_LeakState icon="alarm" valuecolor=[=="LEAK_ALERT"="red", =="SUSPECTED_LEAK"="orange", =="OK"="green"]
    }
}
```

---

## 🟢 3. Node-RED, Prometheus & Custom Automations

### MQTT Subscriptions
Any custom script or broker consumer can subscribe to the topic hierarchy:
- `watermeter/total/value` (Plain float/string)
- `watermeter/readout/json` (Full telemetry JSON dictionary)

### REST Polling
Automations without an MQTT broker can poll the JSON endpoint:
```bash
curl -s "http://<digitizer-ip>:3000/meter?format=json"
```
