# 🪜 Setup Wizard & Calibration Manual

The **Setup Wizard** (accessible via the **Setup** tab at `/setup`) is an interactive 9-step guided workflow that steps you through acquiring a baseline frame, aligning geometric reference markers, tuning contrast & sharpness, drawing neural network ROIs, configuring virtual meters, and deploying live settings.

---

## 🧭 9-Step Calibration Flow Overview

```
[Step 1: Download Image]
       │
       ▼
[Step 2: Initial Rotate]
       │
       ▼
[Step 3: Reference Points]
       │
       ▼
[Step 4: Image Adjust]
       │
       ▼
[Step 5: Digital ROIs]
       │
       ▼
[Step 6: Analog ROIs]
       │
       ▼
[Step 7: Meter Definitions]
       │
       ▼
[Step 8: Services & MQTT]
       │
       ▼
[Step 9: Review & Deploy]
```

---

## 📋 Step-by-Step Instructions

### Step 1: Download Image
- **Camera URL**: Enter your snapshot URL (e.g. `http://192.168.1.50/capture` or `file:///data/meter.jpg`).
- **Network Timeout & Safety**: Configure HTTP timeout (1–60s) and minimum byte threshold to prevent partial frame writes.
- **Action**: Click **Download** to capture and store the reference image.

---

### Step 2: Initial Rotate
- Rotate the image in 90° increments or use the fine-tuning angle slider until all meter numbers and dials are horizontally and vertically upright.

---

### Step 3: Reference Points (Geometric Marker Alignment)
- Define **exactly 3 high-contrast stationary reference markers** across the meter face.
- The digitizer automatically crops template files (`${ConfigDir}/ref0.jpg`, `ref1.jpg`, `ref2.jpg`) and tracks their $(x, y)$ coordinates to compute a 2D affine transformation matrix on every subsequent capture.

#### 🎯 Best Practices for Reference Markers (3-Point Affine Alignment)
1. **Wide Non-Collinear Triangle**: Place the 3 markers across the frame forming a large triangle (e.g., top-left logo, top-right bolt/screw, bottom-center dial rim).
   > [!IMPORTANT]
   > Three points in a straight line cannot mathematically resolve 2D rotation or scale changes. A wide triangle maximizes geometric stability.
2. **Stationary Landmarks Only**: Use permanent casing features (screws, rivets, logos, dial borders). **Never** place markers on rolling digit drums or rotating needle dials.
3. **Safety Margins**: Keep marker boxes at least 20–30 px away from the outer image borders to avoid edge clipping during camera vibration.
4. **Template Sizing**: Recommended size is **40×40 px to 90×90 px**. Overly small templates (<20 px) risk false matches; overly large templates increase CPU time.
5. **Glare Avoidance**: Place markers in areas free from specular LED glare hotspots.

---

### Step 4: Image Adjustments & Focus Metric
- **⚡ Auto Enhance**: One-click analysis calculating optimal gamma, contrast, brightness, and sharpness parameters.
- **Environment Presets**: Fast presets (*Crisp Text*, *Basement / Dim*, *Reflective Glass*, *Reset Defaults*).
- **Gamma & Contrast**: Non-linear gamma curve slider (`0.2`–`3.0`) for recovering shadow details without washing out bright highlights.
- **Luminance Unsharp Masking**: Advanced spatial edge sharpening in CIELAB color space ($L$ channel only) with noise coring threshold.
- **Live Rec.709 Histogram**: Real-time luminance area chart with shadow and highlight clipping indicators.
- **Focus Metric**: Real-time clarity score derived from Laplacian variance.
- **Test Alignment**: Verify that the 3-point affine transformation locks onto reference markers accurately.

---

### Step 5: Digital Region of Interest (ROIs)
- Draw bounding boxes over mechanical odometer digits or digital LCD segments (`digit1`, `digit2`, `digit3`, ...).
- **Ordering**: Order from left (Most Significant Digit) to right (Least Significant Digit).
- **Negative Sign Detection**: Enable `DetectNegativeSign` to recognize minus signs (`-`) for reverse flow meters.
- **Model Selection**: Select `dig-class11_1701_s2.tflite` or `dig-class100_0168_s2_q.tflite`.
- **Canvas Alignment Tools**: Use **Align Top/Bottom/Left/Right**, **Distribute Evenly**, and **Select All** to standardize digit heights and spacing.

---

### Step 6: Analog Region of Interest (ROIs)
- Draw circular/square bounding boxes centered on rotating analog needle dials (`analog1`, `analog2`, `analog3`, ...).
- **Ordering**: Order dials from largest unit ($0.1$) to smallest unit ($0.0001$).
- **Model Selection**: Select `ana-cont_1209_s2.tflite`.

---

### Step 7: Meters Definition & Consistency Rules
- Define virtual meters combining the ROIs using bracket syntax:
  ```ini
  [Meter.main]
  Digits = {digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}
  ```
- **Consistency Engine Options**:
  - `Allow Negative Rates`: `False` (prevents backward count glitches).
  - `Max Rate Value`: Set maximum allowable volume per readout interval (e.g., `0.2 m³`).
  - `Use Extended Resolution`: Enable fractional sub-digit decimal calculation.

---

### Step 8: Services & Integrations
- **Poller**: Enable automated background interval capture (e.g., every `60` seconds).
- **MQTT**: Configure broker host, port, topic prefix (`watermeter`), and Home Assistant Auto-Discovery.

---

### Step 9: Final Review, Save & Live Deploy
- Review generated `config.ini` in the embedded editor.
- Click **Check Syntax** to validate INI integrity.
- Click **Save Config** to persist `config.ini` and write reference images to disk.
- Click **Take In Use** to hot-reload the running digitizer instantly without container restart!

---

## 🎨 Interactive Canvas Controls & Shortcuts

| Action | Control / Shortcut | Description |
| :--- | :--- | :--- |
| **Draw Box** | Click & Drag | Click and drag on canvas to define new marker or ROI. |
| **Select ROI** | Left Click | Selects the active ROI box for resizing or repositioning. |
| **Nudge Position** | Arrow Keys ($\uparrow \downarrow \leftarrow \rightarrow$) | Precise 1-pixel positional adjustment. |
| **Fast Nudge** | Shift + Arrow Keys | 10-pixel positional shift. |
| **Batch Align** | Toolbar Buttons | Standardize Top, Bottom, Width, or Height across selected ROIs. |
| **Coordinates** | Hover | Real-time $(X, Y)$ pixel coordinates in footer bar. |

---

## ⏭️ Next Step

Explore the **[Dashboard, Features & Tools Guide](Dashboard-&-Features-Guide.md)** to monitor live readouts, set up continuous leak detection, or inspect historical readings with Time Machine.
