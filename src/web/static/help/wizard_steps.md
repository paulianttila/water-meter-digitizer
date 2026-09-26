### 10-Step Setup Wizard Progression

Complete the setup wizard sequentially from Step 1 to Step 10:

- **Step 1: Meter Type** — Select a hardware model or archetype (Axioma, Kamstrup, Diehl, Honeywell V200, Itron, or generic presets configured in `config/meter_types/`) to auto-generate centered ROIs, virtual meter configurations, and optimal CNN models.
- **Step 2: Download Image** — Enter camera snapshot URL (`http://`, `https://`, `file://`, or bundled template image `model://...`), timeout, and minimum byte size. Test network reachability live.
- **Step 3: Initial Rotate** — Rotate coarse 90° increments (0°, 90°, 180°, 270°) so meter numbers and circular dials are oriented naturally upright.
- **Step 4: Reference Markers** — Mark exactly 3 high-contrast visual anchors (screws, dial center pins, logo corners) forming a wide triangle for affine alignment.
- **Step 5: Image Adjustments** — Fine-tune rotation angle (e.g. 0.5°), test affine alignment, and configure contrast, sharpness, and AutoContrast preprocessing.
- **Step 6: Digital ROIs** — Align bounding boxes around mechanical roller digits (D1–D5) or LCD numbers, select CNN models, and test classification inference.
- **Step 7: Analog ROIs** — Align bounding boxes around circular needle dials (A1–A4), select CNN models, and test continuous angle detection.
- **Step 8: Meters Definition** — Define composite meters (e.g. `total = {D1}{D2}{D3}.{A1}{A2}{A3}{A4}`), physical flow rate limits, and starting baseline values.
- **Step 9: Services & Poller** — Configure background poller interval, MQTT telemetry topics, Home Assistant auto-discovery, and zero-flow leak tracker.
- **Step 10: Final Review & Save** — Inspect compiled INI configuration, save reference template images, and apply settings live to the running digitizer.
