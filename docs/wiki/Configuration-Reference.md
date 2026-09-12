# Configuration Reference (`config.ini`)

The **Water Meter Digitizer** is configured via an INI file (default location: `/config/config.ini`), which can also be overridden using environment variables via Pydantic Settings.

Every time the configuration is saved from the Web GUI or Setup Wizard, an automatic timestamped backup is preserved in `/config/backups/`.

---

## 📑 Section-by-Section Reference

### `[DEFAULT]`
Global application paths and logging configuration.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `LogLevel` | string | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `Timezone` | string | `UTC` | Container and log timestamp timezone (e.g. `Europe/Helsinki`, `America/New_York`). |
| `ConfigDir` | string | `/config` | Directory containing configuration files and reference images. |
| `DataDir` | string | `/data` | Dedicated directory containing persistent runtime database files (`history.db`). |
| `DigitalModelsDir` | string | `${ConfigDir}/neuralnets/digital` | Directory containing LiteRT/TFLite models for digital digits. |
| `AnalogModelsDir` | string | `${ConfigDir}/neuralnets/analog` | Directory containing LiteRT/TFLite models for analog needles. |
| `PreviousValueFile` | string | `${ConfigDir}/prevalue.ini` | File used to persist previous meter values across readouts. |
| `MinConfidenceThreshold` | float | `50.0` | Minimum confidence percentage (0.0–100.0) required to accept digit/needle reading before invalidating (`N`). |

---

### `[ImageSource]`
Settings for capturing or loading the source image.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `URL` | string | `""` | Camera URL (e.g. `http://192.168.1.100/capture` or `file://${ConfigDir}/original.jpg`). Local `file://` paths are restricted to configured asset directories for security. |
| `Timeout` | integer | `30` | Network request timeout in seconds. |
| `MinSize` | integer | `10000` | Minimum image size in bytes to discard corrupted/partial frames. |

---

### `[Crop]` & `[Resize]`
Optional pre-processing to crop and resize the raw image before alignment.

**`[Crop]`**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable or disable cropping. |
| `x`, `y`, `w`, `h` | integer | `0` | Crop bounding box coordinates and dimensions. |

**`[Resize]`**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable or disable resizing. |
| `w`, `h` | integer | `0` | Target resized width and height in pixels. |

---

### `[ImageProcessing]`
Color, contrast, brightness, and glare suppression adjustments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable image filter adjustments. |
| `Contrast` | float | `1.0` | Contrast multiplier (`1.0` = unchanged). |
| `Brightness` | float | `1.0` | Brightness multiplier (`1.0` = unchanged). |
| `Color` | float | `1.0` | Color saturation multiplier (`1.0` = unchanged). |
| `Sharpness` | float | `1.0` | Sharpness multiplier (`1.0` = unchanged). |
| `GrayScale` | boolean | `False` | Convert image to grayscale. |
| `AutoContrast` | boolean | `False` | Apply histogram autocontrast to the full image. |
| `AutoContrastCutoffLow` | float | `2.0` | Lower percentile cutoff for full-image autocontrast. |
| `AutoContrastCutoffHigh` | float | `45.0` | Upper percentile cutoff for full-image autocontrast. |
| `AutoContrastCutImages` | boolean | `False` | Apply autocontrast to individual ROI cropped images before inference. |
| `GlareSuppressionEnabled` | boolean | `False` | Enable specular glare and reflection suppression on glossy meter glass. |
| `GlareSuppressionMode` | string | `clahe` | Glare filtering mode: `clahe`, `inpaint`, `illumination_normalize`, or `combined`. |
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

**`[Alignment.<ref_name>]`** (For each reference marker):
- `Image`: Path to the reference marker image file (e.g. `${ConfigDir}/ref0.jpg`).
- `x`, `y`: Target upper-left coordinate in aligned space.
- `w`, `h`: Width and height (0 reads actual file dimensions).

---

### `[Digits]` & `[Analog]`
Settings for mechanical rolling odometer drums, digital LCD counters, and circular analog needle dials.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable recognition. |
| `Names` | string | `""` | Comma-separated list of ROI names (e.g. `digit1, digit2` or `analog1, analog2`). |
| `Modelfile` | string | `""` | Path to the LiteRT/TFLite model file. |
| `Model` | string | `auto` | Model type (`auto`, `digital`, `digital100`, `analog`, `analog100`). |

**`[Digits.<name>]`** / **`[Analog.<name>]`**:
- `x`, `y`, `w`, `h`: Bounding box coordinates and dimensions for each ROI.

---

### `[Meters]`
Defines logical output meters, string formatting, rate validation, and units.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Names` | string | `""` | Comma-separated list of meter names (e.g. `digital, analog, total`). |

**`[Meter.<name>]`**:
| Parameter | Type | Default | Description |
|---|---|---|---|
| `Value` | string | `""` | Template string referencing digit/analog names (e.g. `{digit1}{digit2}.{analog1}`). |
| `ConsistencyEnabled` | boolean | `False` | Enable rate validation against the previous stored reading. |
| `AllowNegativeRates` | boolean | `False` | If `False`, decreasing counter readings are rejected. |
| `MaxRateValue` | float | `0.0` | Maximum allowed change since the last valid reading. |
| `UsePreviousValue` | boolean | `False` | Replace unreadable digits (`N`) with the last known good value. |
| `PreValueFromFileMaxAge` | integer | `0` | Maximum age of persisted previous value in minutes (`0` = no limit). |
| `UseExtendedResolution` | boolean | `False` | Append fractional sub-digit decimal from the last analog needle. |
| `Unit` | string | `""` | Measurement unit displayed in API and GUI (e.g. `m³`, `L`). |

---

### `[History]` & `[Snapshots]`
Historical readings retention, SQLite database storage, and Time Machine snapshot archival.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `True` | Enable recording historical readings. |
| `Backend` | string | `sqlite` | Storage backend (`sqlite` or `memory`). |
| `RetentionDays` | integer | `30` | Number of days to retain historical readings before automated pruning. |
| `MaxRecords` | integer | `50000` | Maximum number of readings retained before oldest-first FIFO row pruning. |
| `AutoVacuum` | boolean | `True` | Automatically execute SQLite incremental vacuuming after deletions. |
| `SnapshotMode` | string | `anomalies_only` | Snapshot recording tier (`all`, `anomalies_only`, `disabled`). |
| `MaxSnapshotDiskMb` | float | `500.0` | Disk space budget in MB for snapshot storage. |

---

### `[Poller]`
Internal background scheduler for periodic automated readouts.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable internal background poller task. |
| `IntervalSeconds` | integer | `300` | Time interval between automatic readouts in seconds. |
| `RunOnStartup` | boolean | `True` | Execute an immediate readout cycle when the application starts. |
| `SaveImages` | boolean | `False` | Save intermediate debug images to in-memory cache during background poll. |
| `RetryIntervalSeconds` | integer | `30` | Delay before retrying after a camera capture failure. |

---

### `[MQTT]`
MQTT publisher with native Home Assistant Auto-Discovery and openHAB support.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable MQTT publishing. |
| `Broker` | string | `localhost` | MQTT broker hostname or IP address. |
| `Port` | integer | `1883` | MQTT broker port. |
| `Username`, `Password` | string | `""` | Optional MQTT credentials. |
| `TopicPrefix` | string | `watermeter` | Base MQTT topic prefix. |
| `Retain` | boolean | `True` | Publish meter readings with MQTT retain flag. |
| `HomeAssistantDiscovery` | boolean | `True` | Automatically publish Home Assistant MQTT Auto-Discovery payloads. |

---

### `[ZeroFlow]` (or `[ZeroFlowMonitor]`)
Continuous flow monitoring & automated leak detection.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `Enabled` | boolean | `False` | Enable continuous flow leak monitoring. |
| `MeterName` | string | `total` | Logical meter name to track for continuous flow. |
| `ContinuousFlowMinutes` | integer | `120` | Minutes of uninterrupted non-zero flow before triggering leak alarm. |
| `FlowThreshold` | float | `0.001` | Minimum change between readings to count as active flow. |
| `ResolutionQuietMinutes` | integer | `15` | Quiet zero-flow duration required to auto-resolve active alert. |

---

## 🌐 Dynamic Environment Variable Overrides (`METER_*`)

Any parameter in `config.ini` can be overridden via environment variables using the `METER_` prefix (with double underscores `__` for nested section keys):

| Environment Variable | Overrides Key | Example Value |
|---|---|---|
| `METER_LOG_LEVEL` | `[DEFAULT] LogLevel` | `DEBUG` |
| `METER_IMAGE_SOURCE__URL` | `[ImageSource] URL` | `http://192.168.1.50/capture` |
| `METER_IMAGE_SOURCE__TIMEOUT` | `[ImageSource] Timeout` | `15` |
| `METER_POLLER__ENABLED` | `[Poller] Enabled` | `True` |
| `METER_POLLER__INTERVAL_SECONDS` | `[Poller] IntervalSeconds` | `60` |
| `METER_MQTT__ENABLED` | `[MQTT] Enabled` | `True` |
| `METER_MQTT__BROKER` | `[MQTT] Broker` | `192.168.1.100` |
| `METER_MQTT__HOMEASSISTANT_DISCOVERY` | `[MQTT] HomeAssistantDiscovery` | `True` |
| `METER_ZERO_FLOW_MONITOR__ENABLED` | `[ZeroFlow] Enabled` | `True` |
| `METER_ZERO_FLOW_MONITOR__CONTINUOUS_FLOW_HOURS` | `[ZeroFlow] ContinuousFlowMinutes` | `2.0` |

---

## 📋 Complete Example `config.ini`

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
URL=http://192.168.1.100/capture
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
Image=${ConfigDir}/ref0.jpg
x=99
y=219

[Alignment.ref1]
Image=${ConfigDir}/ref1.jpg
x=512
y=117

[Alignment.ref2]
Image=${ConfigDir}/ref2.jpg
x=301
y=386

[Digits]
Enabled=True
Names=digit1, digit2, digit3, digit4, digit5
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
Names=analog1, analog2, analog3, analog4
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
