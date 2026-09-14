# Setup Wizard Calibration Manual

The **Setup Wizard** (`/gui` or the **Setup** tab) is an interactive 9-step calibration workflow that guides you through capturing a baseline camera frame, aligning it against reference markers, defining digit bounding boxes, and deploying the configuration.

---

## 🪜 Step-by-Step Calibration Workflow

```
[Step 1: Download Image] ──▶ [Step 2: Initial Rotate] ──▶ [Step 3: Reference Points]
                                                                    │
[Step 6: Analog ROIs]   ◀── [Step 5: Digital ROIs]   ◀── [Step 4: Image Adjust]
       │
       ▼
[Step 7: Meter Definitions] ──▶ [Step 8: Services & MQTT] ──▶ [Step 9: Review & Save]
```

---

### Step 1: Download Image
- Enter your camera snapshot URL (e.g. `http://192.168.1.50/capture` or `file:///data/meter.jpg`).
- Configure network timeout (1–60s) and minimum byte size to prevent saving truncated frames.
- Click **Download** to capture the reference image.

---

### Step 2: Initial Rotate
- Rotate the image in 90° increments or fine-tune with arbitrary angle sliders until the meter numbers and dials are horizontally and vertically upright.

---

### Step 3: Reference Points (Alignment Markers)
- Define **exactly 3 high-contrast stationary reference markers** on the meter face to enable affine 2D geometric alignment.
- The digitizer automatically crops the template marker files (e.g., `${ConfigDir}/ref0.jpg`, `${ConfigDir}/ref1.jpg`, `${ConfigDir}/ref2.jpg`) and tracks their $(x, y)$ target coordinates.

#### 🎯 Best Practices for Reference Markers (3-Point Affine Alignment)
To achieve sub-pixel (0 to <2 px) alignment accuracy across camera vibrations, thermal drift, and lens shifts:

1. **Spatial Geometry (Form a Large Triangle)**:
   - Place 3 markers across the frame forming a **wide, non-collinear triangle** (e.g. top-left logo, top-right bolt/screw, bottom-center dial boundary).
   - *Why*: Three points along a straight line cannot mathematically resolve 2D rotation, tilt, or scale changes. A wide triangle maximizes spatial leverage across the entire frame.
2. **Stationary & High-Contrast Features**:
   - Choose static, high-contrast visual features: manufacturer logos, serial number text labels, dial frame corner markings, or casing screws.
   - ⚠️ **Never place markers on moving elements**: Avoid rolling odometer wheels, rotating needle dials, pointers, or areas obscured by water droplets / condensation.
3. **Keep Safety Margins from Frame Edges**:
   - Keep marker bounding boxes at least **20–30 pixels away from the outer image borders**.
   - *Why*: If the camera vibrates or shifts physically, markers too close to the boundary may be clipped outside the field of view, causing template matching to fail.
4. **Optimal Marker Dimensions**:
   - Recommended template size is **40×40 px to 90×90 px** (proportional to image resolution).
   - *Why*: Tiny templates (<20 px) lack unique feature texture and risk false matches elsewhere on the meter; overly large templates increase CPU template matching time without adding precision.
5. **Glare & Lighting Immunity**:
   - Position markers away from direct LED flash specular highlights or reflective glass glare hot spots.

---

### Step 4: Image Adjustments & Alignment
- **⚡ Auto Enhance**: One-click analysis calculating optimal gamma, contrast, brightness, and sharpness parameters based on scene lighting and blur.
- **Environment Presets**: Quick profiles for common environments (*Crisp Text*, *Basement / Dim*, *Reflective Glass*, *Reset Defaults*).
- **Tonal & Gamma Curves**: Non-linear gamma curve slider (`0.2`–`3.0`) for recovering shadow/midtone details without blowing out specular highlights.
- **Luminance Unsharp Masking**: Advanced spatial edge sharpening in CIELAB color space ($L$ channel only) with noise coring threshold to eliminate color fringing and sensor noise.
- **Live Rec.709 Histogram**: Real-time luminance distribution area chart with shadow and highlight clipping percentage monitors.
- **Focus Metric**: Real-time dial focus clarity score derived from Laplacian variance.
- **Glare Suppression**: CLAHE or inpainting to eliminate LED flash hot spots on glossy glass.
- **Test Alignment**: Verify that the 3-point affine transformation locks onto reference markers accurately.

---

### Step 5: Digital Region of Interest (ROIs)
- Draw bounding boxes over mechanical odometer digits or digital LCD segments (`digit1`, `digit2`, `digit3`, ...).
- Order from left (Most Significant Digit) to right (Least Significant Digit).
- **Negative Sign Detection**: Enable `DetectNegativeSign` to recognize minus signs (`-`) on digital water meters displaying reverse or negative flow.
- **Sharpen Cut Images (ROIs)**: Optionally apply unsharp masking and autocontrast individually to cropped digit images before neural network inference.
- Select the neural network model (e.g. `dig-class11_1701_s2.tflite` or `dig-class100_0168_s2_q.tflite`).
- Use canvas alignment tools: **Align Top/Bottom/Left/Right**, **Distribute Evenly**, and **Select All**.

---

### Step 6: Analog Region of Interest (ROIs)
- Draw circular/square bounding boxes centered on rotating analog needle dials (`analog1`, `analog2`, `analog3`, ...).
- Order dials from largest unit ($0.1$) to smallest unit ($0.0001$).
- Select the analog model (e.g. `ana-cont_1209_s2.tflite`).

---

### Step 7: Meters Definition
- Define virtual meters combining the ROIs using bracket syntax:
  - Total Meter: `{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}`
- Configure **Consistency Checking**:
  - `Allow Negative Rates`: `False` (rejects backward count glitches).
  - `Max Rate Value`: Set max physical flow per readout interval (e.g., `0.2 m³`).
  - `Use Extended Resolution`: Enable fractional sub-digit decimal calculation.

---

### Step 8: Services & Integrations
- Enable the **Automated Background Poller** (e.g., capture every `60` seconds).
- Configure **MQTT Broker** connection, topic prefix (`watermeter`), and Home Assistant Auto-Discovery.

---

### Step 9: Final Review, Save & Deploy
- Review the generated `config.ini` in the embedded editor.
- Click **Check Syntax** to validate INI integrity.
- Click **Save Config** to save `config.ini` and write reference images to disk.
- Click **Take In Use** to hot-reload the active running digitizer without restarting the container!
