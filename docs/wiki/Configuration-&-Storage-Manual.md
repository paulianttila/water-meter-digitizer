# ⚙️ Configuration & Storage Manual

This manual provides the comprehensive reference for the `config.ini` configuration schema, environment variable overrides, automated configuration history/backups, and SQLite/WebP historical data storage retention policies.

---

## 🛡️ 1. Configuration History, Backups & Undo

To ensure reliable, fail-safe operation, the **Water Meter Digitizer** includes a built-in configuration versioning and backup subsystem:

1. **Automatic Safety Backups on Save**: Every time `config.ini` is modified via the Web GUI or API, the previous version is saved to `/config/backups/config_<YYYYMMDD_HHMMSS>_<tag>.ini`.
2. **1-Click Undo**: Instantly rollback recent configuration changes with one click from the **Config** tab.
3. **Named Checkpoint Snapshots**: Create milestone snapshots before major adjustments (e.g. `pre-recalibration`).
4. **Visual Color-Coded Diffs**: Inspect line additions (`+`) and deletions (`-`) between active configuration and historical backups directly in the Web GUI.

---

## 💾 2. Dual Storage Backends & Retention Policies

The digitizer utilizes a dual-backend architecture designed for low SD card write wear and long-term retention:

### Backends
- **SQLite Storage (`sqlite`)**: Default persistence stored in `/data/meter_history.db`. Utilizes Write-Ahead Logging (`WAL` mode) and connection pooling for concurrent reads and writes.
- **In-Memory Storage (`memory`)**: High-speed ephemeral storage for read-only filesystem containers or temporary test environments.

### Snapshot Recording Modes & WebP Compression
- Historical frame images are compressed into **WebP** format (reducing storage footprint by 75–80% compared to raw JPEG) and stored in binary blobs within SQLite.
- **Modes**:
  - `all`: Persist a visual snapshot on every readout interval.
  - `anomalies_only` (Recommended): Persist frames only when flow anomalies, vision confidence drops, or leak alerts occur.
  - `disabled`: Only record numerical meter readings without saving visual frames.

### Automatic Disk Pruning Policies
```ini
[Storage]
Backend = sqlite
RetentionDays = 365
MaxRecords = 100000
MaxSnapshotDiskMb = 500
```

---

## 📑 3. Full `config.ini` Section Reference

### `[DEFAULT]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `LogLevel` | string | `INFO` | Verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `Timezone` | string | `UTC` | Timezone (e.g. `Europe/Helsinki`, `America/New_York`). |
| `ConfigDir` | string | `/config` | Directory containing configuration and reference files. |
| `DataDir` | string | `/data` | Directory containing persistent database (`meter_history.db`). |
| `MinConfidenceThreshold` | float | `50.0` | Minimum confidence percentage (0–100) before marking digit `?`. |

### `[ImageSource]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `URL` | string | `""` | Snapshot endpoint (e.g. `http://192.168.1.100/capture` or `file:///data/meter.jpg`). |
| `Timeout` | integer | `30` | Network request timeout in seconds. |
| `MinSize` | integer | `10000` | Minimum image size in bytes to discard corrupt frames. |

### `[ImageProcessing]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `False` | Enable image filter adjustments. |
| `Gamma` | float | `1.0` | Non-linear gamma curve tone adjustment (`0.2`–`3.0`). |
| `Contrast` | float | `1.0` | Linear contrast multiplier. |
| `Brightness` | float | `1.0` | Linear brightness multiplier. |
| `AutoContrast` | boolean | `False` | Dynamic histogram contrast stretching. |
| `UnsharpMask` | boolean | `False` | Spatial edge sharpening in CIELAB color space. |
| `GlareSuppression` | boolean | `False` | Enable optical glare suppression (`clahe` or `inpaint`). |

### `[Alignment]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `InitialRotate` | integer | `0` | Upright rotation angle in degrees. |
| `SearchFieldX`, `SearchFieldY` | integer | `20` | Max template search offset in pixels. |
| `MatchingThreshold` | float | `0.6` | Minimum template matching correlation score. |

### `[NeuralNetworks]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PoolSize` | integer | `2` | Number of concurrent LiteRT interpreter workers in pool. |

### `[Digits]` & `[Analog]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Enabled` | boolean | `True` | Enable digital / analog ROI extraction. |
| `Names` | string | `digit1, ...` | Comma-separated list of active ROI definitions. |
| `Model` | string | `auto` | Model type (`auto`, `digital`, `digital100`, `analog`). |
| `Modelfile` | string | path | Path to `.tflite` model file. |

### `[Meters]` & `[Meter.<name>]`
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `Value` | string | template | ROI substitution pattern (e.g. `{digit1}{digit2}.{analog1}`). |
| `ConsistencyEnabled` | boolean | `True` | Enable predecessor rollover validation. |
| `AllowNegativeRates` | boolean | `False` | Reject decreasing count anomalies. |
| `MaxRateValue` | float | `0.2` | Maximum allowable volume delta per interval. |
| `UseExtendedResolution` | boolean | `True` | Enable fractional sub-digit decimal calculation. |

### `[Poller]`, `[MQTT]`, `[ZeroFlowMonitor]`
| Section | Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| `[Poller]` | `IntervalSeconds` | `300` | Automated capture interval in seconds. |
| `[MQTT]` | `Broker` | `localhost` | MQTT broker hostname or IP. |
| `[MQTT]` | `HomeAssistantDiscovery` | `True` | Publish Home Assistant sensor auto-discovery configs. |
| `[ZeroFlowMonitor]` | `ContinuousFlowHours` | `2.0` | Max uninterrupted flow duration before leak alert. |

---

## ⏭️ Next Step

Understand the vision engine and mathematical algorithms in the **[Core Engine & Architecture Deep Dive](Architecture-&-Neural-Networks.md)**.
