# REST API Reference

The **Water Meter Digitizer** provides a clean REST API built on FastAPI. Interactive Swagger documentation is available at **`http://<digitizer-ip>:3000/docs`** and **`http://<digitizer-ip>:3000/api_console`**.

---

## 🎯 Core Endpoints

### 1. Meter Readout (`GET /meter`)
Triggers capture from configured camera URL, runs neural inference, updates storage, and publishes to MQTT.

- **Query Parameters**:
  - `format`: `json` (default), `value` (plain string for total meter), or `html` (rendered view).
  - `meter`: Specific meter name (e.g. `total`).
  - `saveimages`: `true` to persist intermediate rotated, aligned, and cut ROI frames.
- **Example**:
  ```bash
  curl "http://localhost:3000/meter?format=json"
  ```

---

### 2. Historical Data & Consumption (`GET /history/...`)

- **`GET /history/readings`**:
  Query raw historical readings within a time window.
  - Query parameters: `meter_name`, `start`, `end`, `limit`.

- **`GET /history/consumption`**:
  Aggregated consumption deltas per time interval.
  - Query parameters: `meter_name=total`, `interval=hourly|daily|weekly`, `start`, `end`.

- **`GET /history/timeline`**:
  Chronological historical frame snapshots for Time Machine visual scrubbing.
  - Query parameters: `limit=50`, `offset=0`, `anomalies_only=false`, `frames_only=true`.

- **`GET /history/frame/{reading_id}/image`**:
  Retrieve raw JPEG/WebP image bytes for a recorded snapshot frame.

- **`GET /history/frame/{reading_id}/diff_image?compare_id={id}`**:
  Retrieve difference heatmap visual comparison between two frame IDs.

---

### 3. Leak Monitor (`/leak/...`)

- **`GET /leak/status`**: Return current zero-flow tracking state and active flow duration.
- **`POST /leak/reset`**: Reset active continuous flow timer immediately to `OK`.

---

### 4. Health & System (`/health`, `/healthcheck`, `/system/...`)

- **`GET /health`**: Comprehensive JSON health telemetry (uptime, CPU, RSS memory MB, cache hit rates, model statuses).
- **`GET /healthcheck`**: Lightweight Docker/Kubernetes readiness probe returning `Health - OK`.
- **`GET /mqtt/status`**: Active MQTT broker connection status and last published topic table.
- **`POST /poller/trigger`**: Force an immediate execution of the background poller cycle.
