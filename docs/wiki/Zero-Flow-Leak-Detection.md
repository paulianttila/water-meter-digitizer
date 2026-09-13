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

Add or update the `[ZeroFlowMonitor]` section in your `config.ini`:

```ini
[ZeroFlowMonitor]
Enabled = True
# Name of the meter to track (defined under [Meters])
MeterName = total
# Type of reading: 'cumulative' (app computes flow rate from volume deltas) or 'flow_rate' (reading is already instantaneous flow rate, e.g. m3/h)
ValueType = cumulative
# Alert if water flows continuously without stopping for 2.0 hours
ContinuousFlowHours = 2.0
# Minimum accumulated volume in m3 before triggering alert (prevents false alerts on micro-jitter)
MinLeakVolume = 0.010
# Flow threshold to consider flow active (in m3 delta for cumulative, or m3/h for flow_rate)
FlowThreshold = 0.001
# Consecutive zero-flow readings required to resolve an active leak alert
ResolveDebounceCount = 2
# Maximum number of historical leak events to retain in memory
MaxHistoryEvents = 50
```

### Flow Rate vs Cumulative Mode

- **Cumulative Mode (`ValueType = cumulative`)**:
  Used with standard cumulative odometer/dial meters (e.g. Total $m^3$).
  - Instantaneous flow rate is calculated as: $Q = \frac{\Delta v}{\Delta t} \times 3600\,\text{s/h}$.
  - Zero-flow test: $\Delta v \le \text{FlowThreshold}$.
  - Leak alert triggers when continuous flow duration $\ge \text{ContinuousFlowHours}$ **and** $\text{current\_flow\_volume} \ge \text{MinLeakVolume}$.

- **Flow Rate Mode (`ValueType = flow_rate`)**:
  Used with meters that directly report instantaneous water flow rate (e.g. $m^3/\text{h}$).
  - Reading is used directly as flow rate: $Q = \text{meter\_value}$.
  - Volume is integrated over time using trapezoidal numerical integration: $\Delta v = \frac{Q_t + Q_{t-1}}{2} \times \frac{\Delta t}{3600}$.
  - Zero-flow test: $Q \le \text{FlowThreshold}$.
  - Leak alert triggers when continuous flow duration $\ge \text{ContinuousFlowHours}$ **and** integrated volume $\ge \text{MinLeakVolume}$.

---

## 🔔 Home Assistant & MQTT Alerts

When enabled, the tracker automatically broadcasts state over MQTT:

- **State Topic**: `watermeter/leak/status` (JSON payload with `state`, `current_flow_rate`, `current_flow_duration_minutes`, `current_flow_volume`, `value_type`, `recent_events`)
- **Binary Sensor Discovery**: `homeassistant/binary_sensor/water_meter_digitizer/leak_alert/config` (`ON` when `LEAK_DETECTED`, `OFF` when `OK` or `FLOW_ACTIVE`)
- **Sensors Discovery**:
  - Continuous flow duration sensor (`min`)
  - Leaked volume sensor ($m^3$)
  - Instantaneous flow rate sensor ($m^3/\text{h}$)

### Manual Reset via REST API
If you performed planned water work (e.g. filling a pool), you can reset the active leak timer immediately:

```bash
curl -X POST http://<digitizer-ip>:3000/leak/reset
```

