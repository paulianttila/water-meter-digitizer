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
- Define **2 or 3 high-contrast stationary reference markers** on the meter face (such as manufacturer logos, dial frame corners, or mounting screws).
- *Tip*: Do not place reference points on moving needles, dials, or rolling numbers.
- The digitizer automatically crops the template marker files to `/config/ref0.jpg`, `/config/ref1.jpg`, and `/config/ref2.jpg`.

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
