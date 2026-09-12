# Web Dashboard Tour

The **Water Meter Digitizer** provides a modern glassmorphic web dashboard served on port `3000` (accessible by default at `http://localhost:3000`).

---

## 🧭 Navigation & Core Tabs

The top navigation bar provides instant access to all functional areas:

| Tab | Icon | Purpose |
| :--- | :--- | :--- |
| **Meter** | `speed` | Live dashboard, consumption charts, Time Machine frame scrubber, and intermediate ROI inspection. |
| **Services** | `dns` | Telemetry overview, Zero-Flow Leak Monitor status, background Poller, and MQTT service controls. |
| **Setup** | `settings` | 9-step interactive visual wizard for camera calibration, marker alignment, and ROI definition. |
| **Config** | `manufacturing` | Raw INI configuration editor with syntax validation, 1-click Undo, snapshots, and color diffs. |
| **Baselines** | `history` | Previous meter baseline editor with fallback value management. |
| **API Console** | `code` | Live interactive Swagger/OpenAPI documentation and REST request tester. |
| **Help / About** | `help` | Interactive keyboard/mouse guide and single-source-of-truth versioning telemetry. |

---

## 📊 1. Meter Dashboard View

The **Meter** page is divided into three functional sub-views:

### Values (Live Meter Cards)
- **Live Metric Cards**: Shows formatted readings (e.g. `00452.91241 m³`), calculated flow rate (`0.000 m³/h`), unit, timestamp, and duration.
- **ROI Confidence Badges**: Displays color-coded neural network confidence scores (e.g. `99.2%`, `85.4%`) for individual digital drums and analog needle dials.
- **Inspect ROI Modal**: Click on any ROI pill to open high-resolution zoomed crops of the segmented digit and its raw model classification score distribution.

### Statistics & Consumption Charts
- Aggregates recorded consumption deltas into **Hourly**, **Daily**, or **Weekly** time buckets.
- Toggle between bar charts (period deltas) and cumulative curves (running total).
- Custom time window filters (Last 24 Hours, Last 7 Days, Last 30 Days, Custom range).

### Time Machine (Visual Frame Scrubber)
- **Chronological Timeline**: Drag the timeline slider or click play to scrub across recorded snapshot frames from past to present.
- **Side-by-Side Visual Diff**: Compare historical captures directly against the latest live frame with structural similarity metrics (SSIM).
- **Difference Heatmap**: Displays an amplified visual diff highlighting what moved (e.g., fast spinning dial needles or transitioning drum wheels).

---

## 🩺 2. Services & System Diagnostics View

The **Services** tab provides unified system health telemetry:
- **System Health Card**: CPU load, memory RSS footprint, system uptime, and cache hit ratios.
- **Zero-Flow Leak Card**: Current continuous flow timer, flow state (`OK`, `SUSPECTED_LEAK`, `LEAK_ALERT`), and manual reset trigger.
- **Service Status Card**: Background poller scheduler interval, run counter, next execution countdown, and MQTT connection status with last published topic lists.
