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
| **Config** | `build` | Raw INI configuration editor with syntax validation, 1-click Undo, snapshots, and color diffs. |
| **Baselines** | `tune` | Previous meter baseline editor with fallback value management. |
| **API Console** | `terminal` | Interactive REST endpoint debugger and dedicated procedural Mock Camera Studio. |
| **Help / About** | `help` | Interactive keyboard/mouse guide and single-source-of-truth versioning telemetry. |

---

## ⚡ 6. API Console & Studio
 
The **API Console** tab is divided into three specialized workspaces:

### REST Endpoints Explorer
- **Categorized Endpoint Selector**: Grouped endpoints with color-coded HTTP method badges (`GET` / `POST` / `PUT` / `DELETE`):
  - 🟢 **System & Diagnostics**: `/health`, `/healthcheck`, `/version`
  - 🔵 **Meter & Digitization**: `/meter`, `/reload`, `/get_previous_values`
  - 🟣 **Poller & MQTT Services**: `/poller/status`, `/poller/trigger`, `/mqtt/status`
  - 🟠 **Leak Protection & History**: `/leak/status`, `/leak/reset`, `/history/consumption`, `/history/records`
  - 🔴 **Mock Camera Generator**: `/api/mock_camera`, `/api/mock_camera/reset`
- **Dynamic Request Builder**: Interactive method selector, path builder, and request body payload editor.
- **Multi-View Response Inspector**:
  - **Response Body**: Formatted JSON, rendered HTML, or text stream.
  - **Response Headers**: Structured table of HTTP response headers (`Content-Type`, `X-Mock-...`, `Date`, etc.).
  - **cURL Command**: 1-click `Copy cURL` command generator ready for terminal execution.
  - **Request History**: Chronological log of executed requests with latency and HTTP status indicators.
- **Telemetry Bar**: Live response latency (`⚡ 12ms`), payload size (`1.4 KB`), and status code badge (`HTTP 200 OK`).

### Mock Camera Studio
- **Procedural Simulation Engine**: Real-time generation of realistic water meter dial/drum images with full parameter control:
  - **Feed Modes**: `fixed`, `ticker`, `random`, `flow`
  - **Optical Distortions**: Rotation skew (-180° to +180°), specular glare hotspot with intensity tuning, sensor noise (0-30%), lens blur (0-5px), brightness, and contrast.
  - **Visual Themes**: Digit drum foreground/background color combinations, needle colors, standard resolution presets (VGA, SVGA, XGA, UXGA, or custom).
  - **Individual Overrides**: Per-digit drum overrides (D1–D5) and per-dial needle overrides (A1–A4).
- **Scenario Presets Library**: 1-click real-world presets:
  - *Clean Daytime*, *Tilted & Noisy Sensor*, *Harsh Specular Glare*, *Dim Cellar / Low Light*, *High-Speed Dynamic Flow*, *Transitioning Digit Drum*.
- **Digitizer Engine Testing**: 1-click **"Test in Engine"** button to feed the generated frame directly into the active recognition pipeline and inspect model predictions, confidence scores, and latency.
- **One-Click Actions**: "Download JPG", "Copy Mock URL", "Reset Defaults", "Reset Ticker", and "Set as [ImageSource] URL".

### Swagger UI & OpenAPI Documentation
- Embedded interactive Swagger UI interface rendering live OpenAPI documentation.
- Try out any endpoint with interactive parameter inputs, sample payloads, and response header inspection.
- Quick toolbar actions to open `/docs` or `/redoc` in a new browser tab and download the raw OpenAPI specification JSON (`/openapi.json`).


---

## 📊 1. Meter Dashboard View

The **Meter** page is divided into four functional sub-views:

### Live Readout
- **Auto-Refresh & Pipeline Freshness Toolbar**:
  - Configurable auto-polling interval (`Off`, `5s`, `10s`, `30s`, `60s`).
  - Freshness timestamp indicator (e.g. `Updated 18:30:05` with live pulse dot) and pipeline latency badge (`⚡ 124ms`).
  - 1-click "Trigger Poller" button to force an instant background poll and MQTT broadcast.
- **Hero Readout Cards & Flow Status**:
  - Shows formatted primary readings (e.g. `00452.91241 m³`) in bold monospaced typography with gradient badges.
  - 1-click **Copy Reading** button.
  - Active flow indicator badge (`💧 Flow Active` vs `⏸️ Zero-Flow Idle`) with continuous flow duration timer.
  - Neural network confidence ratings (`99.2% • Good`).
- **Multi-Stage Processing Pipeline Inspector**:
  - In-place stage switcher toggle: **Final Processed**, **ROI Overlays**, **Cropped**, **Aligned**, **Rotated**, and **Original Source**.
  - High-resolution "Inspect ROIs" full-screen dialog with color-coded legend for reference markers, digital counters, and analog dials.
- **Interactive Digit & Dial Counter Zoom Cards**:
  - Colorized counter drum cards and analog needle dials with individual confidence scores.
  - Click on any digit or dial thumbnail to open an enlarged modal view with neural prediction confidence meters.

### Time Machine (Visual Frame Scrubber)
- **Chronological Timeline**: Drag the timeline slider or click play to scrub across recorded snapshot frames from past to present.
- **Side-by-Side Visual Diff**: Compare historical captures directly against the latest live frame with structural similarity metrics (SSIM).
- **Difference Heatmap**: Displays an amplified visual diff highlighting what moved (e.g., fast spinning dial needles or transitioning drum wheels).

### Consumption Analytics & Charts
- **Interactive Multi-Axis Charting**:
  - **Combo (Dual-Axis) Mode**: Displays periodic volume usage bars on the primary (left) axis along with cumulative meter index reading curve on the secondary (right) axis.
  - **Differential Mode**: Focuses on periodic consumption spikes with bar or smooth spline line views.
  - **Cumulative Mode**: Focuses on total meter index progression over time.
- **Smart Unit Toggle**: Switch instantly between **Liters (`L`)** (scaled $\times 1000$ for human-relatable domestic volumes) and **Cubic Meters (`m³`)**.
- **Benchmark Lines & Peak Markers**: ECharts `markLine` highlights average period consumption, while `markPoint` pins peak usage events.
- **Summary KPI Bar**:
  - **Total Consumption**: Total volume used in selected range with dynamic **period-over-period % trend badges** (e.g., `-12.5% vs prior`).
  - **Average Rate**: Average consumption per hour, day, week, or month.
  - **Peak in Period**: Highest recorded consumption bucket with timestamp callout.
  - **Estimated Monthly**: 30-day extrapolated baseline estimate.
- **Time Aggregations & Ranges**: Filter by **Hourly**, **Daily**, **Weekly**, or **Monthly** buckets across **7 Days**, **14 Days**, **30 Days**, **90 Days**, or **All Time**.
- **Data Export & Actions**: 1-click **CSV Export** button to download full aggregated consumption data, plus demo history seeding and history reset.

### Readings Log
- **Searchable & Filterable Historical Log**:
  - **Live Search**: Instant real-time text query filtering across timestamps, meter readouts, segmented digit/dial values, and error strings.
  - **Category Quick Toggles**: Filter records by **All**, **Good Only**, **Anomalies / Errors**, **Flow Active**, and **Snapshots Only**.
  - **Configurable Time Ranges & Limits**: Filter by 24 Hours, 7 Days, 14 Days, 30 Days, or All Time, with 50 to 1000 row limits.
- **Summary KPI Strip**: Displays Total Records, Health Success Rate (% Good), Average Neural Model Confidence, and Flow & Snapshot counters.
- **Visual Status & Readout Badges**:
  - Distinct colored badge chips for digital drums (cyan) and analog dials (amber).
  - Flow activity badge (`💧 Active` vs `⏸️ Idle`).
  - Color-scaled neural network confidence and quality tags.
- **Deep Inspection & Snapshot Modal**: Click the inspect icon on any row to open a full breakdown dialog containing:
  - High-resolution camera snapshot frame preview (when archived).
  - Individual digit and analog needle dial classification confidence scores (`99.0%`, etc.).
  - Meter readouts and raw unprocessed values.
  - Formatted error messages and expandable raw JSON viewer.
- **Data Export Suite**: 1-click **CSV** and **JSON** download buttons for historical auditing, dataset export, or reporting.


---

## 🩺 2. Services & System Diagnostics View

The **Services** tab provides unified system health telemetry:
- **System Health Card**: CPU load, memory RSS footprint, system uptime, and cache hit ratios.
- **Zero-Flow Leak Card**: Current continuous flow timer, flow state (`OK`, `SUSPECTED_LEAK`, `LEAK_ALERT`), and manual reset trigger.
- **Service Status Card**: Background poller scheduler interval, run counter, next execution countdown, and MQTT connection status with last published topic lists.


---

## 🛠️ 4. Configuration Editor View

The **Config** tab provides full runtime parameter control with safety checkpoints and hot-reloading:
- **Dual View Modes**:
  - **Raw INI Code Mode**: Direct monospaced syntax editor with instant syntax verification.
  - **Visual Section Explorer**: Structured card grid organizing parameters by system module (`[TakeImage]`, `[Alignment]`, `[Meters]`, `[MQTT]`, `[Poller]`, `[ZeroFlowTracker]`, etc.) with quick copy badges.
- **Zero-Downtime Hot-Reload**: Apply modified configuration directly into live background threads and web workers without restarting the Docker container or FastAPI daemon.
- **Snapshot & Visual Diff Suite**:
  - **Automatic Safety Backups**: Automatically creates timestamped checkpoints before every save.
  - **Manual Snapshots**: Take tagged snapshots (e.g. `Pre-Calibration`, `Night-Tuning`).
  - **Line-by-Line Diffs**: Color-coded unified diff view (emerald for additions, rose for deletions, cyan for section blocks).
  - **1-Click Restore**: Instant revert to any historical snapshot.
- **Editor Status Bar & Quick Actions**: Real-time line count, file size, dirty-state indicator (`● Unsaved Changes` vs `✓ Synced with Disk`), clipboard copy, and file download.


---

## ⚖️ 5. Baseline & Previous Values Manager View

The **Baselines** tab manages fallback references and sanity baselines in `prevalue.ini`:
- **Meter Baseline Hero Cards**:
  - Displays configured meters, active fallback status (`🟢 Fallback Active` vs `⚪ Standby`), and timestamp of last calibration.
  - Compares saved baseline against the latest live digitizer reading with real-time drift telemetry (e.g. `+0.2500 m³ accumulated`).
  - 1-click **"Sync Live"** action directly on each meter card.
- **Interactive Calibration & Stepper Drawer**:
  - Rapid adjustment steppers (`+0.001`, `+0.01`, `+0.1`, `+1.0`, `+10.0`, `-1.0`, `-0.1`).
  - One-click presets: **"Use Live Value"**, **"Reset to 0.000"**.
  - Negative value validation and drift error prevention.
- **Searchable Baselines Table & Raw Inspector**:
  - Instant search across meter names, baseline readings, and timestamps.
  - 1-click **Export CSV** download.
  - **Inspect Raw prevalue.ini** dialog with syntax formatting and clipboard copy.

---

## ℹ️ 7. Help & About Documentation Suite

The **Help** and **About** tabs provide an interactive knowledge base, live hardware telemetry, and documentation links:

### Help & Documentation
- **Categorized Sub-Tabs**:
  - 📋 **Setup Wizard (9 Steps) & Pipeline Architecture**: Visual 5-stage pipeline breakdown (Capture ➔ Alignment ➔ Inference ➔ Consistency ➔ Export) followed by detailed stage-by-stage wizard walkthrough.
  - 🎯 **Marker Best Practices**: Triangle geometry, landmark rigidity, subpixel stability, and glare prevention guidelines.
  - ⌨️ **Canvas & Shortcuts**: Interactive bounding box creation, coordinate tracking, batch alignment, and nudge keys.
  - 🔌 **Integrations & Services**: MQTT topics, Home Assistant auto-discovery, consumption history API, and REST endpoints.
  - ❓ **Troubleshooting & FAQ**: Common questions and resolutions (unreadable digits marked with `?`, decreasing rate rejections, camera reachability, and landmark stability).
- **Support Diagnostic Bundle**: 1-click modal to copy or download a GitHub-ready Markdown bundle with system specs, memory usage, camera reachability, and model telemetry.

### About & System Diagnostics
- **Hero & Documentation Wiki Link**: Direct link to the complete project wiki documentation (`https://github.com/paulianttila/water-meter-digitizer/wiki`).
- **Live System Telemetry Grid**: Real-time cards displaying Application Version (`v{VERSION}`), Python runtime environment, LiteRT neural engine status, NiceGUI framework version, process RSS/peak memory usage, and system uptime.

---

## 👏 Kudos & Acknowledgments

Special thanks to **[jomjol](https://github.com/jomjol)** for pioneering water meter neural digitization and providing the trained `.tflite` neural network models used by this project:
- [neural-network-analog-needle-readout](https://github.com/jomjol/neural-network-analog-needle-readout)
- [neural-network-digital-counter-readout](https://github.com/jomjol/neural-network-digital-counter-readout)

