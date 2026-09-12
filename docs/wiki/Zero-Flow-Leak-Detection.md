# Zero-Flow Leak Detection

The **Zero-Flow Leak Detector** monitors continuous non-stop water consumption over extended time windows to detect running toilets, leaky pipe fittings, dripping garden hoses, or appliance failures.

---

## 🔬 How Zero-Flow Leak Detection Works

In standard residential and commercial properties, water usage is intermittent—there should always be quiet periods (e.g., overnight) where zero water is consumed for at least 15–30 minutes.

If the digitizer detects continuous uninterrupted flow exceeding a configurable duration threshold, it automatically triggers a leak alert.

```
Flow:   ██████           ████                    ████████████████████████████
Time:   10:00           12:00                    01:00              03:00
State:  [OK]             [OK]                    [SUSPECTED_LEAK] ──▶ [LEAK_ALERT!]
         ▲                ▲                                               │
         └────────────────┴────── Quiet Zero-Flow Windows                 ▼
                                  (Resets continuous timer)          MQTT Alarm
```

---

## ⚙️ Configuration (`config.ini`)

Add or update the `[ZeroFlow]` section in your `config.ini`:

```ini
[ZeroFlow]
Enabled = True
MeterName = total
# Alert if water flows continuously without stopping for 120 minutes (2 hours)
ContinuousFlowMinutes = 120
# Threshold for suspected leak warning (default: 60 minutes)
SuspectedLeakMinutes = 60
# Minimum delta to consider water active (filters sensor noise/vibration)
FlowThreshold = 0.001
# Quiet window required to resolve an active leak (default: 15 minutes)
ResolutionQuietMinutes = 15
```

---

## 🔔 Home Assistant & MQTT Alerts

When enabled, the tracker automatically broadcasts state over MQTT:

- **State Topic**: `watermeter/leak/state` (`OK`, `SUSPECTED_LEAK`, `LEAK_ALERT`)
- **Binary Sensor Topic**: `homeassistant/binary_sensor/water_meter_digitizer/leak_alert/state` (`ON` / `OFF`)
- **Attributes**:
  - `continuous_flow_duration_seconds`: Active flow duration
  - `current_flow_rate`: Current flow in units/interval
  - `peak_flow_rate`: Peak rate recorded during active event

### Manual Reset via REST API
If you performed planned water work (e.g. filling a pool), you can reset the active leak timer immediately:

```bash
curl -X POST http://<digitizer-ip>:3000/leak/reset
```
