### 9-Step Setup Wizard Progression

Complete the setup wizard sequentially from Step 1 to Step 9:

- **Step 1: Download Image** — Enter camera snapshot URL (`http://`, `https://`, or `file://`), timeout, and minimum byte size. Test network reachability live.
- **Step 2: Initial Rotate** — Rotate coarse 90° increments (0°, 90°, 180°, 270°) so meter numbers and circular dials are oriented naturally upright.
- **Step 3: Reference Markers** — Mark exactly 3 high-contrast visual anchors (screws, dial center pins, logo corners) forming a wide triangle for affine alignment.
- **Step 4: Image Adjustments** — Fine-tune rotation angle (e.g. 0.5°), test affine alignment, and configure contrast, sharpness, and AutoContrast preprocessing.
- **Step 5: Digital ROIs** — Draw tight bounding boxes around mechanical roller digits (D1–D5), select CNN models, and test classification inference.
- **Step 6: Analog ROIs** — Draw bounding boxes around circular needle dials (A1–A4), select CNN models, and test continuous angle detection.
- **Step 7: Meters Definition** — Define composite meters (e.g. `total = {D1}{D2}{D3}.{A1}{A2}{A3}{A4}`), physical flow rate limits, and starting baseline values.
- **Step 8: Services & Poller** — Configure background poller interval, MQTT telemetry topics, Home Assistant auto-discovery, and zero-flow leak tracker.
- **Step 9: Final Review & Save** — Inspect compiled INI configuration, save reference template images, and apply settings live to the running digitizer.
