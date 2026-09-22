# 🧭 Dashboard, Features & Tools Guide

[🏠 Wiki Home](Home) • [◀ Previous: Setup Wizard & Calibration Manual](Setup-Wizard-&-Calibration) • [Next: Integrations & API Reference ▶](Integrations-&-API-Reference)

---

The **Water Meter Digitizer** provides a modern, responsive web application served on port `3000` (accessible by default at `http://localhost:3000`). This guide covers the main monitoring views, historical Time Machine playback, Zero-Flow continuous leak detection, and the built-in Mock Camera Studio.

## 🧭 Navigation & Core Tabs Overview

The dashboard features a responsive layout where the left navigation sidebar automatically collapses into an icon-only mode on mobile and narrow screen widths.

| Tab | Purpose |
| :--- | :--- |
| **Meter** | Live dashboard, primary metrics, confidence badges, cropped dial previews, consumption charts, and Time Machine scrubber. |
| **Services** | Telemetry overview, Zero-Flow Leak Monitor status, background Poller, and MQTT service controls. |
| **Setup** | 9-step interactive visual wizard for camera calibration, marker alignment, and ROI definition. |
| **Config** | Raw INI configuration editor with syntax validation, 1-click Undo, snapshots, and color diffs. |
| **Baselines** | Previous meter baseline editor with fallback value management. |
| **API Console** | Interactive REST endpoint debugger and dedicated procedural Mock Camera Studio. |
| **About / Help** | System telemetry metrics, versioning information, and visual workflow cheat-sheets. |

---

## 📊 1. Meter Dashboard

The **Meter** page is the primary live monitoring view:

### Live Readout & Hero Metric Cards
- **Live Value & Quality Badges**: Large typography displaying the recognized readout alongside status and diagnostic badges:
  - **Minimum Confidence (`min_confidence`)**: Displayed as the primary percentage badge (representing the lowest individual component confidence), with full details (`Min: X% • Avg: Y%`) in the tooltip.
  - **Quality Badge**: Categorizes the readout status (`GOOD` in green, `WARNING` in amber, or `UNCERTAIN` in slate).
  - **Predecessor Filled Badge (`🔁 N filled`)**: Displayed when ambiguous or rolling drum digits were recovered and filled from the last validated reading.
  - **Inline Validation Alerts**: Displays an amber warning message under the reading if consistency rules are violated (e.g. `⚠️ Stale reading (no change for 24.0h)` or `⚠️ Rate too high (0.250)`).
- **Auto-Refresh & Latency**: Real-time poll freshness counter, live pulse indicator, and inference latency badge (`⚡ 124ms`).
- **Cropped Digit & Dial Previews**: Visual strip displaying every extracted drum digit and analog needle dial alongside individual model classifications and confidence scores.

### Consumption Analytics & Interval Graphs
- Interactive hourly, daily, and weekly consumption charts powered by SQLite historical records.
- Delta volume indicators and flow rate statistics ($m^3/\text{h}$ and $L/\text{min}$).

---

## 🕰️ 2. Time Machine & Visual Frame Scrubber

The **Time Machine** sub-tab allows scrubbing backward through every historically recorded frame:

```
[◀◀ -1h] [◀ Prev Frame] ────●───────────────────── [Next Frame ▶] [▶▶ Latest]
                           2026-09-14 14:32:10
```

### Key Capabilities:
- **Interactive Timeline Slider**: Seek to any exact historical timestamp.
- **Side-by-Side Comparison**: Compare the historical capture against the live camera feed side-by-side.
- **SSIM Difference Heatmap**: Computes Structural Similarity Index (SSIM) and renders a color-coded heatmap highlighting physical meter movement or shifts.
- **Metadata Inspection**: View exact model confidence, flow rate, and leak status at that precise point in time.

---

## 💧 3. Zero-Flow Continuous Leak Detection

The **Zero-Flow Leak Detector** monitors continuous non-stop water consumption over extended time windows to detect running toilets, dripping pipe fittings, or burst pipes.

```
Flow:   ██████           ████                    ████████████████████████████
Time:   10:00           12:00                    01:00              03:00
State:  [OK]             [OK]                    [SUSPECTED_LEAK] ──▶ [LEAK_ALERT!]
         ▲                ▲                                               │
         └────────────────┴────── Quiet Zero-Flow Windows                 ▼
                                  (Resets continuous timer)          MQTT / UI Alarm
```

### How It Works:
1. In residential and commercial properties, water usage is intermittent—there should always be quiet periods (e.g., overnight) with zero flow for at least 15–30 minutes.
2. If continuous uninterrupted flow exceeds the configured duration threshold (`ContinuousFlowHours`), a leak alert is raised.
3. The alert triggers UI warnings and emits MQTT topic `<prefix>/leak_detected = true`.

### Configuration (`config.ini`):
```ini
[ZeroFlowMonitor]
Enabled = True
MeterName = total
ValueType = cumulative
# Alert if water flows continuously without stopping for 2.0 hours
ContinuousFlowHours = 2.0
# Minimum accumulated volume in m3 before triggering alert (prevents false alerts on micro-jitter)
MinLeakVolume = 0.010
# Flow threshold to consider flow active (in m3 delta)
FlowThreshold = 0.001
# Consecutive zero-flow readings required to resolve an active leak alert
ResolveDebounceCount = 2
```

---

## ⚡ 4. REST API Console & Mock Camera Studio

Accessible via the **API Console** tab (`/api_console`):

### REST Endpoints Explorer
- Categorized endpoint selector (System, Meter, Poller, Leak, Mock Camera).
- Dynamic payload body editor and response viewer (JSON, Headers, Request History).
- 1-Click **Copy cURL** generator for terminal replication.
- Embedded **Swagger UI & OpenAPI Specification** (`/docs` and `/openapi.json`).

### Mock Camera Studio (Procedural Simulator)
- Generate photorealistic synthetic meter frames without needing physical hardware:
  - **Feed Modes**: `fixed`, `ticker` (increments flow over time), `random`, `flow`.
  - **Optical Distortions**: Rotation skew (-180° to +180°), specular glare hotspot with intensity tuning, sensor noise (0–30%), lens blur (0–5px).
  - **Preset Scenarios**: *Clean Daytime*, *Tilted & Noisy Sensor*, *Harsh Specular Glare*, *Dim Cellar*, *High-Speed Dynamic Flow*.
  - **1-Click "Test in Engine"**: Passes the generated mock frame into the active recognition pipeline to inspect predictions and confidence scores.

---

[🏠 Wiki Home](Home) • [◀ Previous: Setup Wizard & Calibration Manual](Setup-Wizard-&-Calibration) • [Next: Integrations & API Reference ▶](Integrations-&-API-Reference)
