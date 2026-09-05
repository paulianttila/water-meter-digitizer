# Water Meter Digitizer

Automatically read analog and digital utility meters using a camera, image processing, and neural network inference. The system captures an image from a configured camera URL, aligns it against reference markers, crops the individual digit/needle ROIs, runs them through CNN models via Google LiteRT runtime, and returns the final meter readings via a REST API and a modern web dashboard.

> This is a completely rewritten, modernized fork of the original [jomjol](https://github.com/jomjol) version (archived 2021).

---

## Features

- **Google LiteRT Runtime** — fast, low-latency neural network inference powered by `ai-edge-litert` on Python 3.11.
- **Modern Web Dashboard & Wizard (`/gui`)** — interactive 8-step setup wizard, live ROI alignment editor, and configuration manager powered by NiceGUI 3.16.
- **Interactive API Explorer (`/`)** — landing page with real-time meter status, JSON viewer, and one-click endpoint testing.
- **In-Memory Image Cache (`/image/{name}`)** — thread-safe bounded LRU + TTL image caching in memory, eliminating disk thrashing and temporary file mounts.
- **Pydantic v2 Configuration** — strict type validation and hierarchical `METER_*` environment variable overrides powered by `pydantic-settings`.
- **Mixed Meter Support** — read combinations of analog needle dials and digital LCD/odometer drum digits in a single image.
- **Four CNN Model Types** — `analog`, `analog100`, `digital`, `digital100` (auto-detected from model output shape).
- **Predecessor-Based Digit Correction** — uses adjacent wheel positions to correct ambiguous readings at digit roll-over boundaries.
- **Extended Resolution** — optionally appends a fractional sub-digit decimal from the last analog needle wheel.
- **Consistency Checking** — rejects spurious readings that exceed configured rate limits or go negative.
- **Previous Value Fallback** — replaces unreadable digits (`N`) with the last known valid reading.
- **Docker Ready** — multi-arch (x86_64, ARM64) container with integrated healthchecks.

---

## Quick Start

### Docker Compose

```yaml
services:
  watermeter-system:
    container_name: ${NAME:-water-meter-system}
    image: ${IMAGE:-paulianttila/water-meter-system:latest}
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    environment:
      - TZ=Europe/Helsinki
      - METER_LOG_LEVEL=INFO
    volumes:
      - ${DIR_DATA:-.}/config:/config
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

The web dashboard is available at **http://localhost:3000/gui**, and the API explorer is at **http://localhost:3000**.

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
  - **Setup Wizard**: 8-step guided calibration flow (image capture, cropping/resizing, image processing, reference marker alignment, ROI bounding-box tuning, and meter calculation setup).
  - **Config Editor**: Direct visual and raw configuration editing with schema validation.
  - **Log Viewer**: Real-time application log stream with level filtering.

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
      "path": "/config/neuralnets/digital/dig-class100_0168_s2_q.tflite",
      "exists": true,
      "size_bytes": 172832
    },
    "analog": {
      "enabled": true,
      "path": "/config/neuralnets/analog/ana-cont_1209_s2.tflite",
      "exists": true,
      "size_bytes": 145920
    }
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
    { "name": "main", "value": "00452.91241", "unit": "m³" }
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
| `LogDir` | string | `/log` | Directory for log files. |
| `DigitalModelsDir` | string | `${ConfigDir}/neuralnets/digital` | Directory containing TFLite models for digital digits. |
| `AnalogModelsDir` | string | `${ConfigDir}/neuralnets/analog` | Directory containing TFLite models for analog needles. |
| `PreviousValueFile` | string | `${ConfigDir}/prevalue.ini` | File used to persist previous meter values across readouts. |

---

### `[ImageSource]`
Settings for capturing or loading the source image.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `URL` | string | `""` | Camera URL (e.g. `http://192.168.1.100/capture` or `file://${ConfigDir}/original.jpg`). |
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
| `UsePreviuosValue` | boolean | `False` | Replace unreadable digits (`N`) with the last known good value. |
| `PreValueFromFileMaxAge` | integer | `0` | Maximum age of persisted previous value in minutes (`0` = no limit). |
| `UseExtendedResolution` | boolean | `False` | Append fractional sub-digit decimal from the last analog needle. |
| `Unit` | string | `""` | Measurement unit displayed in API and GUI (e.g. `m³`, `kWh`). |

---

### Complete Example `config.ini`

```ini
[DEFAULT]
LogLevel=INFO
ConfigDir=/config
LogDir=/log
DigitalModelsDir=${ConfigDir}/neuralnets/digital
AnalogModelsDir=${ConfigDir}/neuralnets/analog
PreviousValueFile=${ConfigDir}/prevalue.ini

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
Modelfile=${DigitalModelsDir}/dig-class100_0168_s2_q.tflite
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
Modelfile=${AnalogModelsDir}/ana-cont_1209_s2.tflite
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
UsePreviuosValue=True
UseExtendedResolution=True
ConsistencyEnabled=True
AllowNegativeRates=False
MaxRateValue=0.2
Unit=m³
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
    ├─ analog images ──► AnalogNeedleCNN   (LiteRT) ─┐
    └─ digital images ─► DigitalCounterCNN (LiteRT) ┘
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
