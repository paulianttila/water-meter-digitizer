# ⚙️ Configuration & Storage Manual

[🏠 Wiki Home](Home) • [◀ Previous: Integrations & API Reference](Integrations-&-API-Reference) • [Next: Architecture, Neural Networks & Pipeline Deep Dive ▶](Architecture-&-Neural-Networks)

---

This manual provides the comprehensive, authoritative reference for the `config.ini` configuration schema, environment variable overrides, automated configuration history/backups, and SQLite/WebP historical data storage retention policies.

## 🛡️ 1. Configuration History, Backups & Undo

To ensure reliable, fail-safe operation, the **Water Meter Digitizer** includes a built-in configuration versioning and backup subsystem:

1. **Automatic Safety Backups on Save**: Every time `config.ini` is modified via the Web GUI or API, the previous version is saved to `/config/backups/config_<YYYYMMDD_HHMMSS>_<tag>.ini`.
2. **1-Click Undo**: Instantly rollback recent configuration changes with one click from the **Config** tab (`/config`).
3. **Named Checkpoint Snapshots**: Create milestone snapshots before major adjustments (e.g. `pre-recalibration`).
4. **Visual Color-Coded Diffs**: Inspect line additions (`+`) and deletions (`-`) between active configuration and historical backups directly in the Web GUI.

---

## 💾 2. Dual Storage Backends & Retention Policies

The digitizer utilizes a dual-backend architecture designed for low SD card write wear and long-term retention:

### Backends
- **SQLite Storage (`sqlite`)**: Default persistence stored in `/data/meter_history.db`. Utilizes Write-Ahead Logging (`WAL` mode) and connection pooling for concurrent reads and writes.
- **In-Memory Storage (`memory`)**: High-speed ephemeral storage for read-only filesystem containers or temporary test environments.

### Snapshot Storage Strategies & WebP Compression
Historical image frames are compressed into **WebP** format (reducing storage footprint by 75–80% compared to raw JPEG) and stored in `/data/snapshots/`:

- **`smart_tiered`** (Recommended): Retains high-resolution full camera frames for recent days (`RecentFullFrameDays`), keeps lightweight composite ROI strips for longer historical windows (`RoiStripRetentionDays`), captures idle heartbeats, and always archives full frames on anomaly.
- **`change_only`**: Persists frames only when measured meter reading changes.
- **`roi_strips_only`**: Saves compact horizontal composite strips of cropped digit/dial ROIs without storing full camera frames.
- **`full_frames`**: Archives full camera frames on every interval.
- **`disabled`**: Records numerical meter timeseries without saving visual image frames.

### Retention Configuration Example
```ini
[History]
Enabled = True
Backend = sqlite
RetentionDays = 30
MaxRecords = 50000
AutoVacuum = True
PruneInterval = 50

[Snapshots]
Enabled = True
Mode = smart_tiered
Format = webp
Quality = 75
MaxDiskMB = 500.0
RecentFullFrameDays = 2
RoiStripRetentionDays = 14
IdleHeartbeatMinutes = 15
AlwaysSaveOnAnomaly = True
StorageDir = /data/snapshots
```

---

## 📑 3. Full `config.ini` Section Reference

### `[DEFAULT]`
Global application paths, runtime directories, and confidence thresholds.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `LogLevel` | string | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `Timezone` | string | `UTC` | Timezone for timestamps and consumption intervals (e.g. `Europe/Helsinki`, `America/New_York`). |
| `ConfigDir` | string | `/config` | Directory path containing configuration files and reference images. |
| `DataDir` | string | `/data` | Directory path for databases, snapshots, and persistent data. |
| `DigitalModelsDir` | string | `${ConfigDir}/neuralnets/digital` | Directory containing digital digit recognition neural network models. |
| `AnalogModelsDir` | string | `${ConfigDir}/neuralnets/analog` | Directory containing analog needle recognition neural network models. |
| `PreviousValueFile` | string | `${ConfigDir}/prevalue.ini` | File path for persisting previous meter values across readouts. |
| `MinConfidenceThreshold` | float | `60.0` | Global minimum confidence score percentage threshold (0.0–100.0) before marking uncertain digits with `?`. |

---

### `[ImageSource]`
Settings for capturing or loading the source image.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `URL` | string | `file://${ConfigDir}/original.jpg` | Source image URL (e.g. `http://...`, `https://...`, or `file://...`). |
| `Timeout` | integer | `10` | Network request timeout in seconds when retrieving image frames. |
| `MinSize` | integer | `20000` | Minimum image file size in bytes to discard corrupt or partial frames. |

---

### `[Crop]` & `[Resize]`
Optional pre-processing stages to crop and resize the raw image before reference marker alignment.

#### `[Crop]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable image cropping before alignment. |
| `x`, `y` | integer | `0` | Top-left bounding box coordinates in pixels. |
| `w`, `h` | integer | `0` | Width and height of crop bounding box in pixels. |

#### `[Resize]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable image resizing before alignment. |
| `w`, `h` | integer | `0` | Target width and height in pixels for resized frame. |

---

### `[ImageProcessing]`
Color, tone curve, spatial unsharp masking, autocontrast, and specular glare suppression adjustments.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable image processing and enhancement filters. |
| `Contrast` | float | `1.0` | Contrast adjustment factor (1.0 = unchanged). |
| `Brightness` | float | `1.0` | Brightness adjustment factor (1.0 = unchanged). |
| `Color` | float | `1.0` | Color saturation adjustment factor (1.0 = unchanged). |
| `Sharpness` | float | `1.0` | Sharpness enhancement factor (1.0 = unchanged). |
| `GrayScale` | boolean | `False` | Convert camera image to grayscale before processing. |
| `Gamma` | float | `1.0` | Non-linear gamma curve tone adjustment (`0.2`–`3.0`). |
| `SharpnessMode` | string | `standard` | Sharpening algorithm: `standard`, `unsharp_mask`, or `auto`. |
| `UnsharpRadius` | float | `1.0` | Blur radius (sigma) for luminance unsharp masking. |
| `UnsharpAmount` | float | `1.5` | Sharpening strength multiplier for unsharp mask. |
| `UnsharpThreshold` | integer | `3` | Noise coring threshold (0–255) to avoid sharpening camera sensor noise. |
| `AutoSharpenCutImages`| boolean | `False` | Apply spatial edge sharpening individually to cropped ROI sub-images. |
| `AutoContrast` | boolean | `False` | Apply dynamic histogram auto-contrast stretching to full frame. |
| `AutoContrastCutoffLow` | float | `2.0` | Lower histogram percentile cutoff percentage for auto-contrast. |
| `AutoContrastCutoffHigh` | float | `45.0` | Upper histogram percentile cutoff percentage for auto-contrast. |
| `AutoContrastIgnore` | int/None | `None` | Pixel intensity value to ignore during auto-contrast calculation. |
| `AutoContrastCutImages`| boolean | `False` | Apply auto-contrast individually to cropped ROI sub-images. |
| `AutoContrastCutImagesCutoffLow` | float | `2.0` | Lower percentile cutoff for cut ROI auto-contrast. |
| `AutoContrastCutImagesCutoffHigh` | float | `45.0` | Upper percentile cutoff for cut ROI auto-contrast. |
| `AutoContrastCutImagesIgnore` | int/None | `None` | Pixel intensity value to ignore in cut ROI auto-contrast. |
| `GlareSuppressionEnabled` | boolean | `False` | Enable specular glare and reflection suppression. |
| `GlareSuppressionMode` | string | `clahe` | Glare algorithm: `clahe`, `inpaint`, `illumination_normalize`, or `combined`. |
| `GlareInpaintThreshold` | integer | `230` | Luminance threshold (0–255) to detect specular reflection hotspots. |
| `GlareInpaintRadius` | integer | `3` | Inpainting neighborhood radius in pixels (Fast Marching method). |
| `GlareClaheClipLimit` | float | `2.0` | Contrast limiting threshold factor for CLAHE equalization. |
| `GlareClaheGridSize` | integer | `8` | Tile grid division size for CLAHE (e.g. 8 for 8×8 grid). |
| `GlareApplyToCutImages`| boolean | `False` | Apply glare suppression individually to cropped ROI cutouts. |

---

### `[Alignment]` & `[Alignment.refX]`
Geometric 3-point affine transformation locking onto stationary reference markers.

#### `[Alignment]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `RotationAngle` | integer | `0` | Coarse initial rotation angle in degrees (`0`, `90`, `180`, `270`). |
| `Refs` | string | `ref0, ref1, ref2` | Comma-separated list of reference marker section names. |
| `PostRotationAngle` | integer | `0` | Fine-tuning rotation angle in degrees applied after reference alignment. |

#### `[Alignment.ref0]`, `[Alignment.ref1]`, `[Alignment.ref2]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Image` | string | path | File path of cropped reference template image (e.g. `${ConfigDir}/Ref_0.jpg`). |
| `x`, `y` | integer | `0` | Target coordinate in aligned pixel coordinate space. |
| `w`, `h` | integer | `0` | Template dimensions in pixels (`0` = auto-detected from template image file). |

---

### `[Digits]` & `[Analog]`
Neural network ROI extraction for mechanical rolling drums and analog needle dials.

#### `[Digits]` & `[Analog]` Section Level
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `True` | Enable digital / analog ROI recognition. |
| `Names` | string | `digit1, ...` | Comma-separated list of active ROI section names. |
| `Modelfile` | string | path | File path to TensorFlow Lite `.tflite` model. |
| `Model` | string | `auto` | Model family: `auto`, `digital`, `digital100`, `analog`, `analog100`. |
| `DetectNegativeSign` | boolean | `False` | *(Digits only)* Detect minus sign (`-`) on digital meters with reverse flow. |

#### `[Digits.digitX]` & `[Analog.analogX]` Sub-sections
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `x`, `y` | integer | `0` | Top-left X and Y coordinates of ROI bounding box in aligned space. |
| `w`, `h` | integer | `0` | Width and height of ROI bounding box in pixels. |

---

### `[Meters]` & `[Meter.<name>]`
Virtual meter compositions, rate validation, and rollover consistency checking.

#### `[Meters]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Names` | string | `digital, analog, total` | Comma-separated list of logical virtual meter definitions. |

#### `[Meter.<name>]` (e.g. `[Meter.total]`)
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Value` | string | template | Value pattern referencing ROIs (e.g. `${Meter.digital:Value}.${Meter.analog:Value}` or `{digit1}{digit2}.{analog1}`). |
| `ConsistencyEnabled` | boolean | `True` | Enable rate and rollover consistency validation checks. |
| `AllowNegativeRates` | boolean | `False` | Reject decreasing count anomalies when set to `False`. |
| `MaxRateValue` | float | `0.2` | Maximum allowable consumption change per readout interval (`0.0` = disable rate-of-change cap). |
| `MinRateValue` | float | `0.0` | Minimum required consumption change rate threshold when consumption occurs (`0.0` = disabled). |
| `StaleThresholdHours` | float | `0.0` | Hours without consumption change before flagging meter as stale (`0.0` = disabled). |
| `UsePreviousValue` | boolean | `True` | Replace unreadable or mid-roll digits (`N` / `?`) with last known valid reading. |
| `PreValueFromFileMaxAge` | integer | `0` | Max age in minutes to trust previous value from file (`0` = no limit). |
| `UseExtendedResolution` | boolean | `True` | Append fractional sub-digit decimal resolution from analog needle. |
| `Unit` | string | `m³` | Measurement unit string reported in MQTT and API (e.g. `m³`, `L`, `kWh`). |

> [!NOTE]
> **Baseline Persistence & Protection (`prevalue.ini`)**:
> When `UsePreviousValue` is enabled, validated meter readouts are persisted in `prevalue.ini` under each meter section with `time`, `value`, and `lastchange` (the timestamp of the most recent reading value change).
> If a reading contains unreadable digits (`N`), fails rate consistency (`Rate too high` / `Rate too low` / `Negative rate`), or is flagged as `Stale reading`, it is marked invalid (`valid=False`), and `prevalue.ini` is **not updated**, protecting the baseline against corruption until a valid reading is obtained.

---

### `[History]`
Timeseries database backend and retention configuration.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `True` | Enable historical timeseries storage and persistence. |
| `Backend` | string | `sqlite` | Storage backend: `sqlite` (persistent file) or `memory` (ephemeral RAM). |
| `DBUrl` | string | `""` | Optional custom database connection URL (e.g. `sqlite:////data/meter_history.db`). |
| `MaxMemoryMB` | float | `20.0` | Maximum memory threshold in MB for in-memory database or buffers. |
| `MaxRecords` | integer | `50000` | Maximum row limit before oldest records are FIFO pruned (`0` = disable). |
| `RetentionDays` | integer | `30` | Days to retain readings before automated pruning (`0` = retain forever). |
| `AutoVacuum` | boolean | `True` | Enable incremental auto-vacuuming on SQLite database. |
| `PruneInterval` | integer | `50` | Number of write cycles between automated retention pruning runs. |

---

### `[Snapshots]`
Time Machine image frame recording and WebP compression settings.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `True` | Enable historical image frame archival for Time Machine. |
| `Mode` | string | `smart_tiered` | Strategy: `smart_tiered`, `change_only`, `roi_strips_only`, `full_frames`, `disabled`. |
| `Format` | string | `webp` | Image compression format: `webp` or `jpeg`. |
| `Quality` | integer | `75` | Compression quality factor (1–100). |
| `MaxDiskMB` | float | `500.0` | Maximum disk space cap in MB for stored snapshot frames. |
| `RecentFullFrameDays` | integer | `2` | Retention period in days for high-resolution full camera frames. |
| `RoiStripRetentionDays`| integer | `14` | Retention period in days for compact composite ROI strips. |
| `IdleHeartbeatMinutes` | integer | `15` | Maximum interval in minutes between snapshot captures when no flow occurs. |
| `AlwaysSaveOnAnomaly` | boolean | `True` | Always archive full camera frame when OCR error or low confidence occurs. |
| `StorageDir` | string | `/data/snapshots` | Filesystem directory path for compressed snapshot storage. |

---

### `[Poller]`
Automated background scheduling via cron expressions with second-level resolution.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable scheduled background poller. |
| `Cron` | string | `0 */5 * * * *` | Cron schedule expression. Supports 6-field second resolution (`s m h d m wd`) or standard 5-field minute resolution (`m h d m wd` at second `:00`). |
| `RunOnStartup` | boolean | `True` | Trigger an immediate readout cycle upon application startup. |
| `SaveImages` | boolean | `False` | Save intermediate debug images during polled readouts. |
| `RetryIntervalSeconds` | integer | `30` | Retry interval in seconds following a capture failure or outlier detection. |
| `ConsensusReads` | integer | `1` | Number of consecutive reads in sliding window for median temporal consensus filtering (1=disabled, 2–10=active). |

#### Cron Schedule Examples
- `*/15 * * * * *`: Every 15 seconds (at `:00`, `:15`, `:30`, `:45`).
- `0,30 * * * * *`: Twice a minute (at `:00` and `:30`).
- `0 */5 * * * *` or `*/5 * * * *`: Every 5 minutes at second `:00`.
- `0 0 6,18 * * *`: Twice daily at exactly 06:00:00 and 18:00:00.

---

### `[MQTT]`
MQTT telemetry broadcasting and Home Assistant Auto-Discovery.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `True` | Enable MQTT client service. |
| `Broker` | string | `localhost` | MQTT broker hostname or IP address. |
| `Port` | integer | `1883` | MQTT broker port. |
| `Username` | string | `""` | MQTT authentication username (optional). |
| `Password` | string | `""` | MQTT authentication password (optional). |
| `ClientID` | string | `water-meter-digitizer` | Client identifier presented to MQTT broker. |
| `TopicPrefix` | string | `watermeter` | Base MQTT topic prefix for published readings and status. |
| `KeepAlive` | integer | `60` | MQTT keepalive ping interval in seconds. |
| `TLS` | boolean | `False` | Enable TLS/SSL connection encryption. |
| `Retain` | boolean | `True` | Publish telemetry messages with MQTT retain flag. |
| `HomeAssistantDiscovery`| boolean | `True` | Publish Home Assistant MQTT auto-discovery configuration topics. |
| `DiscoveryPrefix` | string | `homeassistant` | Home Assistant MQTT discovery topic prefix. |
| `DeviceName` | string | `Water Meter Digitizer` | Friendly device name reported in Home Assistant. |
| `DeviceID` | string | `water_meter_digitizer` | Unique device identifier reported in Home Assistant. |

---

### `[ZeroFlowMonitor]`
Continuous water flow tracking and continuous leak alarm engine.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable zero-flow tracking & continuous leak detection. |
| `MeterName` | string | `total` | Target meter name to monitor for continuous flow. |
| `ValueType` | string | `cumulative` | Reading type: `cumulative` (volume deltas) or `flow_rate` (instantaneous flow). |
| `ContinuousFlowHours` | float | `2.0` | Uninterrupted flow duration threshold in hours before triggering alert. |
| `MinLeakVolume` | float | `0.010` | Minimum accumulated volume in $m^3$ during continuous flow to flag leak. |
| `FlowThreshold` | float | `0.001` | Minimum delta or flow rate (in meter units) to count as active flow. |
| `ResolveDebounceCount` | integer | `2` | Consecutive zero-flow readings required to auto-resolve active leak alert. |
| `MaxHistoryEvents` | integer | `50` | Maximum historical leak events to retain in memory log. |

---

## 🌐 4. Environment Variable Overrides (`METER_*`)

Any parameter in `config.ini` can be overridden via environment variables using Pydantic Settings:

| Environment Variable | Target Parameter | Example |
| :--- | :--- | :--- |
| `CONFIG_FILE` | Root INI File Path | `/config/config.ini` |
| `METER_LOG_LEVEL` | `[DEFAULT] LogLevel` | `DEBUG` |
| `METER_IMAGESOURCE_URL` | `[ImageSource] URL` | `http://192.168.1.50/capture` |
| `METER_MQTT_BROKER` | `[MQTT] Broker` | `192.168.1.100` |
| `METER_MQTT_PORT` | `[MQTT] Port` | `1883` |
| `METER_MQTT_TOPIC_PREFIX` | `[MQTT] TopicPrefix` | `watermeter` |
| `METER_POLLER_CRON` | `[Poller] Cron` | `*/15 * * * * *` |
| `TZ` | Container Timezone | `Europe/Helsinki` |

---

[🏠 Wiki Home](Home) • [◀ Previous: Integrations & API Reference](Integrations-&-API-Reference) • [Next: Architecture, Neural Networks & Pipeline Deep Dive ▶](Architecture-&-Neural-Networks)
