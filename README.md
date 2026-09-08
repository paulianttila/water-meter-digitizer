# Water Meter Digitizer

Automatically read analog and digital utility meters using a camera, image processing, and neural network inference. The system captures an image from a configured camera URL, aligns it against reference markers, crops the individual digit/needle ROIs, runs them through CNN models via Google LiteRT runtime, and returns the final meter readings via a REST API and a modern web dashboard.

> This is a completely rewritten, modernized fork of the original [jomjol](https://github.com/jomjol) version (archived 2021).

---

## Features

### 💧 Universal Meter Reading
- **Mixed Meter Support** — Simultaneously reads mechanical odometer rolling digits, digital LCD counters, and circular analog needle dials in a single frame.
- **Intelligent Digit Correction** — Automatically fixes ambiguous, half-turned numbers at roll-over boundaries using adjacent dial positions.
- **High-Precision Resolution** — Optional fractional sub-digit decimal calculation for fine-grained flow and leak detection.
- **Automatic Image Alignment** — Corrects camera tilt, vibration, and rotation shifts against visual reference markers.
- **Data Integrity & Fallbacks** — Rejects impossible rate spikes, guards against negative flow, and safely falls back to cached baseline readings when digits are obscured.

### 🏡 Smart Home & Cloud Connectivity
- **Native Home Assistant Integration** — Instant zero-configuration sensor discovery over MQTT with native energy/water dashboard compatibility.
- **Automated Background Poller** — Built-in scheduler periodically captures and publishes readings without external cron scripts.
- **Open Standards & REST API** — Clean structured JSON endpoints for easy integration with openHAB, Node-RED, Prometheus, Grafana, or custom automations.

### 📊 Modern Web Dashboard & Setup
- **Interactive Visual Setup Wizard (`/gui`)** — Intuitive step-by-step alignment tool to easily define reference markers and digit bounding boxes.
- **Glassmorphic Web Dashboard (`/`)** — Live meter status, real-time telemetry, model confidence indicators, and one-click API explorer.
- **Interactive Consumption Charts** — Visual breakdown of hourly, daily, and weekly water usage with customizable time ranges.
- **Diagnostics & Telemetry** — Real-time camera latency, system uptime, and memory utilization monitors.

### 🚀 Edge & Container Ready
- **Lightweight & Fast** — High-performance on-device neural network inference optimized for low-power edge devices (e.g., Raspberry Pi).
- **Docker Ready** — Official multi-architecture (x86_64, ARM64) container images with integrated health check probes.
- **Resilient Storage** — Dual-mode persistence with automatic in-memory failover for read-only or immutable container environments.

> 💡 *For architectural diagrams, neural network specifications, and developer documentation, see [DEVELOPER.md](DEVELOPER.md).*

---

## Quick Start

### Docker Compose

```yaml
services:
  watermeter-digitizer:
    container_name: ${NAME:-water-meter-digitizer}
    image: ${IMAGE:-paulianttila/water-meter-digitizer:latest}
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    environment:
      - TZ=Europe/Helsinki
      - METER_LOG_LEVEL=INFO
    volumes:
      - ${DIR_DATA:-.}/config:/config
      - ${DIR_DATA:-.}/data:/data
    ports:
      - 3000:3000
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:3000/healthcheck')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "2m"
        max-file: "2"
```

```bash
docker compose up -d
```

The web dashboard is available at **http://localhost:3000**.

### Run Locally (development with `uv`)

```bash
# Install dependencies
uv sync

# Point to configuration and run
export CONFIG_FILE=$(pwd)/config/config.ini
uv run python src/main.py
```

---

## Web Interfaces

- **`/` — API Explorer & Status Page**: Real-time summary of configured meters, last reading timestamps, interactive API documentation, and live preview.
- **`/gui` — NiceGUI Web Dashboard**:
  - **Setup Wizard**: 9-step guided calibration flow (image capture, cropping/resizing, image processing, reference marker alignment, ROI bounding-box tuning, meter calculation setup, and background poller / MQTT / storage configuration).
  - **Config Editor**: Direct visual and raw configuration editing with schema validation.

---

## REST API

All endpoints are served on port `3000`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API Explorer & Status landing page (HTML) |
| `GET` | `/gui` | NiceGUI Web Dashboard & Setup Wizard |
| `GET` | `/meter?format=json` | Trigger a readout, return JSON result |
| `GET` | `/meter?format=html` | Trigger a readout, return formatted HTML result |
| `GET` | `/meter?url=<cam_url>` | Override the camera URL for a single readout |
| `GET` | `/meter?saveimages=true` | Save intermediate images to memory cache for debugging |
| `GET` | `/roi` | Show current ROI overlays on the live aligned image |
| `GET` | `/image/{image}` | Stream an image from in-memory cache (e.g. `original.jpg`, `aligned.jpg`, `roi.jpg`, `{roi_name}.jpg`) |
| `GET` | `/image_tmp/{image}` | Backward-compatible alias for `/image/{image}` |
| `GET` | `/setPreviousValue?name=<n>&value=<v>` | Manually set the stored previous value for a meter |
| `GET` | `/reload` | Reload configuration from disk |
| `GET` | `/version` | Return app version information as JSON |
| `GET` | `/health` | Rich JSON diagnostics: camera latency, memory, cache hit ratio, models, uptime |
| `GET` | `/healthcheck` | Liveness check, returns `Health - OK` |
| `GET` | `/poller/status` | Current background poller status, last run, and next run schedule |
| `POST` | `/poller/trigger` | Trigger an immediate background readout cycle |
| `GET` | `/mqtt/status` | MQTT connection status, broker details, and topic prefix |
| `GET` | `/history/consumption?meter=<m>&interval=<i>&days=<d>&cumulative=<b>` | Aggregated consumption buckets (`hourly`, `daily`, `weekly`), with optional cumulative running total |
| `GET` | `/history/readings?meter=<m>&limit=<n>` | Recent raw meter readings history |
| `GET` | `/history/stats` | Storage backend health, memory usage, and tracked meter statistics |
| `POST` | `/history/seed?days=<d>&meter=<m>&base_val=<b>` | Seed synthetic readings history for testing |
| `POST` | `/history/clear` | Clear all stored history readings |
| `GET` | `/exit` | Graceful shutdown |

### Example JSON Responses

#### Health & Diagnostics (`/health`)

```json
{
  "status": "healthy",
  "uptime": {
    "uptime_seconds": 1245.8,
    "uptime_human": "20m 45s",
    "started_at": "2026-09-05T15:10:00.000000+00:00"
  },
  "camera": {
    "url": "http://192.168.1.100/capture",
    "reachable": true,
    "latency_ms": 14.2,
    "status_code": 200,
    "error": null
  },
  "memory": {
    "rss_mb": 68.4,
    "peak_rss_mb": 74.2,
    "platform": "darwin"
  },
  "cache": {
    "hits": 45,
    "misses": 3,
    "total_requests": 48,
    "hit_ratio_percent": 93.75,
    "current_size": 12,
    "max_size": 50,
    "ttl_seconds": 300.0,
    "cached_keys": ["original", "aligned", "digit1", "digit2", "analog1"]
  },
  "models": {
    "digital": {
      "enabled": true,
      "path": "/config/neuralnets/digital/class100/dig-class100_0168_s2_q.tflite",
      "exists": true,
      "size_bytes": 172832,
      "metrics": {
        "inferences": 24,
        "avg_inference_ms": 14.5,
        "min_inference_ms": 11.2,
        "max_inference_ms": 22.8,
        "last_inference_ms": 13.9,
        "last_inference_at": "2026-09-07T18:30:15.123456+00:00",
        "pool_size": 4,
        "created_instances": 2,
        "available_instances": 2,
        "active_inferences": 0,
        "input_shape": [1, 32, 20, 3],
        "output_shape": [1, 100],
        "quantized": true
      }
    },
    "analog": {
      "enabled": true,
      "path": "/config/neuralnets/analog/continuous/ana-cont_1209_s2.tflite",
      "exists": true,
      "size_bytes": 145920,
      "metrics": {
        "inferences": 24,
        "avg_inference_ms": 15.8,
        "min_inference_ms": 12.1,
        "max_inference_ms": 25.4,
        "last_inference_ms": 15.1,
        "last_inference_at": "2026-09-07T18:30:15.234567+00:00",
        "pool_size": 4,
        "created_instances": 2,
        "available_instances": 2,
        "active_inferences": 0,
        "input_shape": [1, 32, 32, 3],
        "output_shape": [1, 2],
        "quantized": false
      }
    },
    "total_inferences": 48,
    "avg_inference_ms": 15.15
  },
  "system": {
    "version": "8.0.0",
    "python_version": "3.11.13",
    "platform": "Darwin-24.0.0"
  }
}
```

#### Meter Readout (`/meter?format=json`)

```json
{
  "meters": [
    {
      "name": "main",
      "value": "00452.91241",
      "unit": "m³",
      "quality": "good",
      "confidence": 96.2
    }
  ],
  "digital_results": {
    "digit1": "0.0",
    "digit2": "0.0",
    "digit3": "4.0",
    "digit4": "4.9",
    "digit5": "2.6"
  },
  "analog_results": {
    "analog1": "0.00",
    "analog2": "0.90",
    "analog3": "2.50",
    "analog4": "4.10"
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
  },
  "error": ""
}
```

---

## Configuration

The system is configured via an INI file format (default `/config/config.ini`), which can also be overridden using environment variables via Pydantic Settings.

### Environment Variables

Settings can be specified either through the INI file or directly via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_FILE` | `/config/config.ini` | Path to the active configuration INI file |
| `TZ` | — | Container timezone (e.g. `Europe/Helsinki`) |
| `METER_LOG_LEVEL` | `INFO` | Override global logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `METER_CONFIG_DIR` | `/config` | Override base configuration directory |
| `METER_DATA_DIR` | `/data` | Override data directory (for SQLite database storage) |
| `METER_LOG_DIR` | `/log` | Override log directory |
| `METER_IMAGE_SOURCE__URL` | `""` | Override camera image source URL |
| `METER_IMAGE_SOURCE__TIMEOUT` | `30` | Override image download timeout in seconds |

> **Tip**: Any configuration key can be overridden using the `METER_<SECTION>__<KEY>` naming convention (e.g. `METER_IMAGE_PROCESSING__ENABLED=true`).

---

### `[DEFAULT]`
Global application paths and logging configuration.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `LogLevel` | string | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ConfigDir` | string | `/config` | Directory containing configuration files and reference images. |
| `DataDir` | string | `/data` | Dedicated directory containing persistent runtime database files (`history.db`). |
| `DigitalModelsDir` | string | `${ConfigDir}/neuralnets/digital` | Directory containing TFLite models for digital digits. |
| `AnalogModelsDir` | string | `${ConfigDir}/neuralnets/analog` | Directory containing TFLite models for analog needles. |
| `PreviousValueFile` | string | `${ConfigDir}/prevalue.ini` | File used to persist previous meter values across readouts. |
| `MinConfidenceThreshold` | float | `50.0` | Minimum confidence percentage (0.0–100.0) required to accept digit/needle reading before invalidating (`N`). |

---

### `[ImageSource]`
Settings for capturing or loading the source image.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `URL` | string | `""` | Camera URL (e.g. `http://192.168.1.100/capture` or `file://${ConfigDir}/original.jpg`). Local `file://` paths are restricted to configured asset directories (`ConfigDir`, `DataDir`, and workspace root) for security. |
| `Timeout` | integer | `30` | Network request timeout in seconds. |
| `MinSize` | integer | `10000` | Minimum image size in bytes to discard corrupted/partial frames. |

---

### `[Crop]` & `[Resize]`
Optional pre-processing to crop and resize the raw image before alignment.

**`[Crop]`**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable or disable cropping. |
| `x` | integer | `0` | Top-left X coordinate of the crop area. |
| `y` | integer | `0` | Top-left Y coordinate of the crop area. |
| `w` | integer | `0` | Width of the crop area. |
| `h` | integer | `0` | Height of the crop area. |

**`[Resize]`**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable or disable resizing. |
| `w` | integer | `0` | Target resized width in pixels. |
| `h` | integer | `0` | Target resized height in pixels. |

---

### `[ImageProcessing]`
Color, contrast, brightness, and autocontrast enhancements.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable image filter adjustments. |
| `Contrast` | float | `1.0` | Contrast multiplier (`1.0` = unchanged). |
| `Brightness` | float | `1.0` | Brightness multiplier (`1.0` = unchanged). |
| `Color` | float | `1.0` | Color saturation multiplier (`1.0` = unchanged). |
| `Sharpness` | float | `1.0` | Sharpness multiplier (`1.0` = unchanged). |
| `GrayScale` | boolean | `False` | Convert image to grayscale. |
| `AutoContrast` | boolean | `False` | Apply histogram autocontrast to the full image. |
| `AutoContrastCutoffLow` | float | `2` | Lower percentile cutoff for full-image autocontrast. |
| `AutoContrastCutoffHigh` | float | `45` | Upper percentile cutoff for full-image autocontrast. |
| `AutoContrastIgnore` | int/None | `None` | Pixel intensity to ignore during full-image autocontrast. |
| `AutoContrastCutImages` | boolean | `False` | Apply autocontrast to individual ROI cropped images before inference. |
| `AutoContrastCutImagesCutoffLow` | float | `2` | Lower percentile cutoff for cropped ROI autocontrast. |
| `AutoContrastCutImagesCutoffHigh` | float | `45` | Upper percentile cutoff for cropped ROI autocontrast. |
| `AutoContrastCutImagesIgnore` | int/None | `None` | Pixel intensity to ignore for cropped ROI autocontrast. |
| `GlareSuppressionEnabled` | boolean | `False` | Enable specular glare and reflection suppression on glossy meter glass. |
| `GlareSuppressionMode` | string | `clahe` | Glare filtering mode: `clahe` (local contrast), `inpaint` (specular mask fill), `illumination_normalize` (division filter), or `combined`. |
| `GlareInpaintThreshold` | int | `230` | Luminance threshold (0–255) for detecting specular flash hotspots. |
| `GlareInpaintRadius` | int | `3` | Neighborhood radius in pixels for Fast Marching (Telea) inpainting. |
| `GlareClaheClipLimit` | float | `2.0` | Contrast limiting threshold factor for CLAHE. |
| `GlareClaheGridSize` | int | `8` | Tile grid size for CLAHE (e.g. `8` for 8x8 grid). |
| `GlareApplyToCutImages` | boolean | `False` | Apply glare suppression individually to cropped digit/pointer ROI images. |


---

### `[Alignment]`
Affine transformation using reference markers to correct rotation and perspective shifts.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `RotationAngle` | float | `0.0` | Coarse rotation in degrees (`0`, `90`, `180`, `270`). |
| `Refs` | string | `""` | Comma-separated list of reference image section names (e.g. `ref0, ref1, ref2`). |
| `PostRotationAngle` | float | `0.0` | Fine-tuning post-rotation angle in degrees (e.g. `0.5`). |

**`[Alignment.<ref_name>]`** (For each reference in `Refs`):
| Parameter | Type | Description |
|---|---|---|
| `image` | string | Path to the reference marker image file (e.g. `${ConfigDir}/Ref_ZR_x99_y219.jpg`). |
| `x` | integer | Target upper-left X coordinate of the marker in aligned space. |
| `y` | integer | Target upper-left Y coordinate of the marker in aligned space. |
| `w` | integer | Width of the reference image (optional; 0 reads actual image dimensions). |
| `h` | integer | Height of the reference image (optional; 0 reads actual image dimensions). |

---

### `[Digits]` (Digital Counter)
Settings for digital odometer drum or LCD digit recognition.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable digital digit recognition. |
| `names` | string | `""` | Comma-separated list of digit ROI names (e.g. `digit1, digit2, digit3`). |
| `Modelfile` | string | `""` | Path to the TensorFlow Lite model file (`.tflite`). |
| `Model` | string | `auto` | Model type: `auto`, `digital` (0–9 + invalid), or `digital100` (continuous 0–99). |

**`[Digits.<digit_name>]`** (For each digit in `names`):
| Parameter | Type | Description |
|---|---|---|
| `x` | integer | Upper-left X coordinate of the digit ROI. |
| `y` | integer | Upper-left Y coordinate of the digit ROI. |
| `w` | integer | Width of the digit ROI. |
| `h` | integer | Height of the digit ROI. |

---

### `[Analog]` (Analog Needles)
Settings for circular analog needle / dial recognition.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable analog needle recognition. |
| `names` | string | `""` | Comma-separated list of needle ROI names (e.g. `analog1, analog2, analog3`). |
| `Modelfile` | string | `""` | Path to the TensorFlow Lite model file (`.tflite`). |
| `Model` | string | `auto` | Model type: `auto`, `analog` (continuous 0–10), or `analog100` (high-res 0–9.99). |

**`[Analog.<analog_name>]`** (For each analog dial in `names`):
| Parameter | Type | Description |
|---|---|---|
| `x` | integer | Upper-left X coordinate of the needle ROI. |
| `y` | integer | Upper-left Y coordinate of the needle ROI. |
| `w` | integer | Width of the needle ROI. |
| `h` | integer | Height of the needle ROI. |

---

### `[Meters]`
Defines output meters, value formatting, consistency checks, and units.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Names` | string | `""` | Comma-separated list of meter definition names (e.g. `digital, analog, total`). |

**`[Meter.<meter_name>]`** (For each meter in `Names`):
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Value` | string | `""` | Template string referencing digit/analog names (e.g. `{digit1}{digit2}.{analog1}`). Supports interpolation (e.g. `${Meter.digital:Value}.${Meter.analog:Value}`). |
| `ConsistencyEnabled` | boolean | `False` | Enable rate validation against the previous stored reading. |
| `AllowNegativeRates` | boolean | `False` | If `False`, decreasing counter readings are rejected. |
| `MaxRateValue` | float | `0.0` | Maximum allowed change since the last valid reading. |
| `UsePreviousValue` | boolean | `False` | Replace unreadable digits (`N`) with the last known good value (`UsePreviuosValue` is also supported for backward compatibility). |
| `PreValueFromFileMaxAge` | integer | `0` | Maximum age of persisted previous value in minutes (`0` = no limit). |
| `UseExtendedResolution` | boolean | `False` | Append fractional sub-digit decimal from the last analog needle. |
| `Unit` | string | `""` | Measurement unit displayed in API and GUI (e.g. `m³`, `kWh`). |

---

### `[History]`
Settings for SQLAlchemy-backed historical reading retention, SQLite database storage, and consumption aggregation.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `True` | Enable recording historical meter readings. |
| `Backend` | string | `sqlite` | Storage backend (`sqlite`, `memory`, or custom SQLAlchemy backend). |
| `DBUrl` | string | `""` | Optional SQLAlchemy database connection string (e.g. `sqlite:////data/history.db`, `postgresql://user:pass@host/db`). When blank, uses SQLite in `DataDir`. |
| `RetentionDays` | integer | `30` | Number of days to retain historical readings before automated time-based pruning (`0` to disable). |
| `MaxRecords` | integer | `50000` | Maximum number of readings retained before oldest-first FIFO row pruning (`0` to disable). |
| `AutoVacuum` | boolean | `True` | Automatically execute SQLite incremental vacuuming after deletions to recover disk space. |
| `PruneInterval` | integer | `50` | Number of recorded readings between automated background pruning cycles. |
| `MaxMemoryMB` | float | `20.0` | In-memory cache memory limit threshold (for in-memory mode). |

---

### `[Poller]`
Internal background scheduler for periodic meter readouts.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable internal background poller task. |
| `IntervalSeconds` | integer | `300` | Time interval between automatic readouts in seconds (e.g. `300` = 5 minutes). |
| `RunOnStartup` | boolean | `True` | Execute an immediate readout cycle when the application starts. |
| `SaveImages` | boolean | `False` | Save intermediate debug images to in-memory cache during background poll. |
| `RetryIntervalSeconds` | integer | `30` | Delay before retrying after a camera capture or processing failure. |

---

### `[MQTT]`
MQTT publisher with native Home Assistant Auto-Discovery and openHAB support.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable MQTT publishing. |
| `Broker` | string | `localhost` | MQTT broker hostname or IP address. |
| `Port` | integer | `1883` | MQTT broker port (`1883` standard, `8883` TLS). |
| `Username` | string | `""` | Optional username for MQTT broker authentication. |
| `Password` | string | `""` | Optional password for MQTT broker authentication. |
| `ClientID` | string | `water-meter-digitizer` | MQTT client identifier. |
| `TopicPrefix` | string | `watermeter` | Base MQTT topic prefix (e.g. `watermeter/main/value`, `watermeter/status`). |
| `KeepAlive` | integer | `60` | MQTT keepalive interval in seconds. |
| `TLS` | boolean | `False` | Enable TLS encryption. |
| `Retain` | boolean | `True` | Publish meter readings with MQTT retain flag. |
| `HomeAssistantDiscovery` | boolean | `True` | Automatically publish Home Assistant MQTT Auto-Discovery payloads. |
| `DiscoveryPrefix` | string | `homeassistant` | Home Assistant MQTT discovery topic prefix. |
| `DeviceName` | string | `Water Meter Digitizer` | Device name displayed in Home Assistant device registry. |
| `DeviceID` | string | `water_meter_digitizer` | Unique device identifier for Home Assistant entity mapping. |

---

### `[ZeroFlowMonitor]`
Continuous flow monitoring & automated leak detection with auto-resolution.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable continuous flow leak monitoring. |
| `MeterName` | string | `total` | Name of the logical meter to track for continuous flow. |
| `ContinuousFlowHours` | float | `2.0` | Hours of uninterrupted non-zero flow required before flagging a leak. |
| `MinLeakVolume` | float | `0.010` | Minimum volume consumed during continuous flow window (filters optical jitter). |
| `FlowThreshold` | float | `0.001` | Minimum change between readings (in meter units) to count as active flow. |
| `ResolveDebounceCount` | integer | `2` | Number of consecutive zero readings required to auto-resolve active alert. |
| `MaxHistoryEvents` | integer | `50` | Maximum completed leak event logs retained in memory. |


---

### Complete Example `config.ini`

```ini
[DEFAULT]
LogLevel=INFO
ConfigDir=/config
DataDir=/data
DigitalModelsDir=${ConfigDir}/neuralnets/digital
AnalogModelsDir=${ConfigDir}/neuralnets/analog
PreviousValueFile=${ConfigDir}/prevalue.ini
MinConfidenceThreshold=50.0

[ImageSource]
URL=http://192.168.1.100/capture_with_flashlight
Timeout=15
MinSize=20000

[Crop]
Enabled=False
x=0
y=0
w=640
h=480

[Resize]
Enabled=False
w=640
h=480

[ImageProcessing]
Enabled=False
Contrast=1.0
Brightness=1.0
Color=1.0
Sharpness=1.0
GrayScale=False
AutoContrast=False
AutoContrastCutoffLow=2
AutoContrastCutoffHigh=45
AutoContrastIgnore=None
AutoContrastCutImages=True
AutoContrastCutImagesCutoffLow=2
AutoContrastCutImagesCutoffHigh=45
AutoContrastCutImagesIgnore=None

[Alignment]
RotationAngle=180
Refs=ref0, ref1, ref2
PostRotationAngle=0.0

[Alignment.ref0]
image=${ConfigDir}/Ref_ZR_x99_y219.jpg
x=99
y=219

[Alignment.ref1]
image=${ConfigDir}/Ref_m3_x512_y117.jpg
x=512
y=117

[Alignment.ref2]
image=${ConfigDir}/Ref_x0_x301_y386.jpg
x=301
y=386

[Digits]
Enabled=True
names=digit1, digit2, digit3, digit4, digit5
Modelfile=${DigitalModelsDir}/class100/dig-class100_0168_s2_q.tflite
Model=auto

[Digits.digit1]
x=215
y=97
w=42
h=75

[Digits.digit2]
x=273
y=97
w=42
h=75

[Digits.digit3]
x=332
y=97
w=42
h=75

[Digits.digit4]
x=390
y=97
w=42
h=75

[Digits.digit5]
x=446
y=97
w=42
h=75

[Analog]
Enabled=True
names=analog1, analog2, analog3, analog4
Modelfile=${AnalogModelsDir}/continuous/ana-cont_1209_s2.tflite
Model=auto

[Analog.analog1]
x=491
y=307
w=115
h=115

[Analog.analog2]
x=417
y=395
w=115
h=115

[Analog.analog3]
x=303
y=424
w=115
h=115

[Analog.analog4]
x=163
y=358
w=115
h=115

[Meters]
Names=digital, analog, total

[Meter.digital]
Value={digit1}{digit2}{digit3}{digit4}{digit5}
ConsistencyEnabled=False

[Meter.analog]
Value={analog1}{analog2}{analog3}{analog4}
UseExtendedResolution=False
ConsistencyEnabled=False

[Meter.total]
Value=${Meter.digital:Value}.${Meter.analog:Value}
UsePreviousValue=True
UseExtendedResolution=True
ConsistencyEnabled=True
AllowNegativeRates=False
MaxRateValue=0.2
Unit=m³

[History]
Enabled=True
Backend=sqlite
RetentionDays=30
MaxRecords=50000
AutoVacuum=True
PruneInterval=50

[Poller]
Enabled=True
IntervalSeconds=300
RunOnStartup=True
SaveImages=False
RetryIntervalSeconds=30

[MQTT]
Enabled=True
Broker=localhost
Port=1883
Username=
Password=
ClientID=water-meter-digitizer
TopicPrefix=watermeter
KeepAlive=60
TLS=False
Retain=True
HomeAssistantDiscovery=True
DiscoveryPrefix=homeassistant
DeviceName=Water Meter Digitizer
DeviceID=water_meter_digitizer
```

---

## CNN Models

Four model types are supported. The active type is selected via the `Modelfile` setting or detected automatically from the model's output shape:

| Model type | Outputs | Description |
|------------|---------|-------------|
| `analog` | 2 | Analog needle, continuous 0–10 output |
| `analog100` | 100 | Analog needle, higher-resolution 0–9.99 output |
| `digital` | 11 | Digital digit, 0–9 + invalid |
| `digital100` | 100 | Digital digit, continuous 0–99 |

Models are executed using Google LiteRT (`ai-edge-litert`), providing high-performance quantized and floating-point inference across CPU, GPU, and NPU delegates.

---

## Architecture

```
Camera URL
    │
    ▼
ImageProcessor          ← download, rotate, align, crop ROIs
    │
    ├─ analog images ──► InterpreterPool ──► AnalogNeedleCNN   (LiteRT) ─┐
    └─ digital images ─► InterpreterPool ──► DigitalCounterCNN (LiteRT) ┘
                                                                         │
                                                                         ▼
                                                                 DigitizerProcessor
                                                                   • predecessor correction
                                                                   • extended resolution
                                                                   • consistency check
                                                                   • previous value fill-in
                                                                         │
                                                                         ▼
                                                                    MeterResult  ──► REST API / NiceGUI Dashboard
```

---

## License

See [LICENSE.md](LICENSE.md).
