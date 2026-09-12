# Configuration Reference (`config.ini`)

The digitizer is configured via an INI file (default location: `/config/config.ini`). All settings can be edited through the Web GUI Config Editor or by modifying the file directly.

---

## 📑 Section-by-Section Reference

### `[DEFAULT]`
- `LogLevel`: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `Timezone`: Local timezone string (e.g. `Europe/Helsinki`, `UTC`).
- `PreValueFile`: Path to previous baseline file (default: `/config/prevalue.ini`).

### `[TakeImage]`
- `RawImagesLocation`: Local directory to save raw captured frames.
- `Url`: HTTP or file snapshot endpoint (e.g. `http://192.168.1.50/capture`).
- `Timeout`: Download request timeout in seconds (default: `10`).
- `MinImageSize`: Minimum valid payload size in bytes (default: `10000`).

### `[Alignment]`
- `InitialRotate`: Initial rotation in degrees applied to raw image (e.g. `0.0`, `90.0`, `180.0`).
- `Flip`: Image mirror flip (`none`, `horizontal`, `vertical`).
- `RefImages`: List of 2 or 3 stationary reference marker points (`ref0`, `ref1`, `ref2`).
- `Contrast`, `Brightness`, `Sharpness`, `Color`: Image enhancement factors (default: `1.0`).
- `GlareSuppression`: Enable anti-reflective filtering (`True` / `False`).
- `GlareMode`: Algorithm (`clahe` or `inpaint`).

### `[Digital_Readout]` & `[Analog_Readout]`
- `Model`: Path to neural network `.tflite` model.
- `PoolSize`: Number of concurrent LiteRT worker interpreter instances (default: `2`).
- `CutImages`: List of coordinate bounding boxes (`name`, `x`, `y`, `w`, `h`).

### `[Meter_<name>]` (e.g. `[Meter_total]`)
- `Format`: Formatting string combining ROIs (e.g. `{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}`).
- `Unit`: Display unit string (e.g. `m³`, `L`, `gal`).
- `ConsistencyEnabled`: Enable rate jump and negative flow rejection (`True` / `False`).
- `AllowNegativeRates`: Allow decreasing meter readings (`False` for standard water meters).
- `MaxRateValue`: Maximum plausible volume consumed per interval (e.g. `0.2`).
- `UsePreviousValue`: Fallback to cached previous value on digit obstruction (`True`).
- `UseExtendedResolution`: Enable sub-digit fractional interpolation (`True`).

### `[MQTT]`
- `Enabled`: Enable MQTT client service (`True` / `False`).
- `Broker`: IP address or hostname of MQTT broker (e.g. `192.168.1.100`).
- `Port`: MQTT port (default: `1883`).
- `User`, `Password`: MQTT authentication credentials.
- `TopicPrefix`: Base topic name (default: `watermeter`).
- `HomeassistantDiscovery`: Auto-publish Home Assistant discovery payloads (`True`).

### `[Poller]`
- `Enabled`: Enable automated background timer scheduler (`True` / `False`).
- `Interval`: Polling period in seconds (e.g. `60`).

### `[Storage]`
- `Backend`: Persistence engine (`sqlite` or `memory`).
- `RetentionDays`: Number of days of historical readings to keep (default: `365`).
- `MaxRecords`: FIFO record limit (default: `100000`).
- `SnapshotMode`: Snapshot recording tier (`all`, `anomalies_only`, `disabled`).
- `MaxSnapshotDiskMb`: Hard disk quota in MB for snapshot frames.
