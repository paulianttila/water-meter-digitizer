# 🪜 Setup Wizard & Calibration Manual

[🏠 Wiki Home](Home) • [◀ Previous: Getting Started & Hardware Guide](Getting-Started-&-Hardware) • [Next: Dashboard, Features & Tools Guide ▶](Dashboard-&-Features-Guide)

---

The **Setup Wizard** (accessible via the **Setup** tab at `/setup`) is an interactive 10-step guided workflow that steps you through acquiring a baseline frame, selecting your meter archetype with auto-populated ROIs and CNN models, aligning geometric reference markers, tuning contrast & sharpness, positioning neural network ROIs, configuring virtual meters, and deploying live settings.

## 🧭 10-Step Calibration Flow Overview

```
[Step 1: Meter Type (Presets & CNN)]
       │
       ▼
[Step 2: Download Image]
       │
       ▼
[Step 3: Initial Rotate]
       │
       ▼
[Step 4: Reference Points]
       │
       ▼
[Step 5: Image Adjust]
       │
       ▼
[Step 6: Digital ROIs]
       │
       ▼
[Step 7: Analog ROIs]
       │
       ▼
[Step 8: Meter Definitions]
       │
       ▼
[Step 9: Services & MQTT]
       │
       ▼
[Step 10: Review & Deploy]
```

---

## 📋 Step-by-Step Instructions

### Step 1: Meter Type Selection & Guided Presets
- **Searchable Dropdown & Category Filters**: Search through predefined meter models or filter by category (*Smart*, *Mechanical*, *Generic Archetypes*, or *Custom*):
  - **Axioma Qalcosonic W1**: European smart ultrasonic meter with cumulative total and instant flow registers. Pre-selects `class11` with negative flow detection.
  - **Generic Archetypes**: LCD Cumulative, LCD Total + Flow, Mechanical 5+4, Drums Only, and Custom (Manual blank canvas).
- **Adjustable Counts**: Fine-tune the number of integer digits, decimal digits, analog dials, or engineering units (`m³`, `L`, `gal`, `kWh`).
- **Neural Network Recommendations**: View recommended neural network models and architectures matched to your physical hardware.
- **Live Preview**: Inspect generated virtual meter format strings before continuing.
- **Adding & Contributing Meter Models**: You can introduce new meter models without touching code by adding a single INI file into `config/meter_types/` (see `config/meter_types/README.md` and `_template.ini`). Each file defines `[Template]` metadata, default counts, declarative format templates (`"{digits}.{decimals}"` or `"{digits}.{analogs}"`), CNN model preferences, and standard configuration sections that automatically inherit default parameters. Because each model is in its own file, community PRs never conflict with one another!
- **Preset Hot-Reloading**: Clicking the reload button (or reloading the page) instantly discovers newly added or edited `.ini` preset files and faceplate images from `config/meter_types/` without restarting the application.

---

### Step 2: Download Image
- **Camera URL**: Enter your snapshot URL (e.g. `http://192.168.1.50/capture`, `file:///data/meter.jpg`, or select a bundled template model image like `model://axioma_qalcosonic_w1` or `model://mock_camera` from the dropdown). If an image exists for the selected preset, it is pre-populated automatically. You can also use the reload button next to the URL input to refresh available template images on demand.
- **Network Timeout & Safety**: Configure HTTP timeout (1–60s) and minimum byte threshold to prevent partial frame writes.
- **Action**: Click **Download** to capture and store the reference image.

---

### Step 3: Initial Rotate
- Rotate the image in 90° increments (`-90°`, `180°`, `+90°`) or reset rotation until all meter numbers and dials are horizontally and vertically upright.
- **✨ Align to Model Template**: If you selected a meter model preset in Step 1, click **Align to Model Template** to open the interactive alignment dialog on your upright photo. Pan (via mouse drag, arrow keys, or buttons) and scale (mouse wheel zoom to cursor, HUD buttons, or sliders) your camera picture directly underneath fixed template ROIs (alignment reference markers, digital digits, and analog dials). When you click **Apply Alignment & Calculate ROIs**, the wizard automatically projects and configures all reference markers, digital/analog ROIs, and fine rotation for your specific camera frame!


---

### Step 4: Reference Points (Geometric Marker Alignment)
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

### Step 5: Image Adjustments & Focus Metric
- **⚡ Auto Enhance**: One-click analysis calculating optimal gamma, contrast, brightness, and sharpness parameters.
- **Environment Presets**: Fast presets (*Crisp Text*, *Basement / Dim*, *Reflective Glass*, *Reset Defaults*).
- **Gamma & Contrast**: Non-linear gamma curve slider (`0.2`–`3.0`) for recovering shadow details without washing out bright highlights.
- **Luminance Unsharp Masking**: Advanced spatial edge sharpening in CIELAB color space ($L$ channel only) with noise coring threshold.
- **Live Rec.709 Histogram**: Real-time luminance area chart with shadow and highlight clipping indicators.
- **Focus Metric**: Real-time clarity score derived from Laplacian variance.
- **Test Alignment**: Verify that the 3-point affine transformation locks onto reference markers accurately.

---

### Step 6: Digital Region of Interest (ROIs)
- Bounding boxes over mechanical odometer digits or digital LCD segments (`digit1`, `digit2`, `digit3`, ...). If a preset was selected in Step 1, placeholder boxes are already created and centered for you to align!

#### 📐 Crucial Sizing Rule: Inner Box Fits the Digit Number (20% Border)
For digit models like `dig-class11_*`, the neural network recognizes the complete digit only and requires a **background border of 20% of the image size around the digit number itself**.

In the Setup Wizard canvas, each digit ROI displays two nested rectangles:
- **Outer Thicker Rectangle**: The complete cropped ROI sub-image extracted and passed to the CNN inference engine.
- **Inner Thinner Rectangle**: Inset by exactly **20% on all four sides** (top, bottom, left, right), leaving 60% of the width and height in the center.
- **Center Line**: The horizontal line at 50% height for vertical numeral centering.

> [!IMPORTANT]
> **When drawing or resizing a digit ROI, the inner thinner box size must be adjusted to fit exactly around the digit number in the picture** (when the number is stationary / upright and has not started rotating to the next position). Do not fit the outer box tightly around the number — fitting the inner box around the number automatically provides the mandatory 20% margin on all sides.

<p align="left">
  <img src="https://raw.githubusercontent.com/paulianttila/water-meter-digitizer/main/docs/images/ROI_drawing.jpg" alt="Digit ROI Inner Box Sizing Guide (20% Border)" width="320">
</p>

```text
       ◄── 20% ──►◄──────── 60% ────────►◄── 20% ──►
     ┌────────────┬──────────────────────┬────────────┐ ▲
     │            │       Top 20%        │            │ │ 20%
     ├────────────┼──────────────────────┼────────────┤ ▼
     │            │┌────────────────────┐│            │ ▲
     │            ││                    ││            │ │
     │            ││    Digit Number    ││            │ │
     │  Left 20%  │├─── ── ── ── ── ── ─┤│  Right 20% │ │ 60% (Inner Box)
     │            ││  (Fits Inner Box)  ││            │ │
     │            ││                    ││            │ │
     │            │└────────────────────┘│            │ ▼
     ├────────────┼──────────────────────┼────────────┤ ▲
     │            │      Bottom 20%      │            │ │ 20%
     └────────────┴──────────────────────┴────────────┘ ▼
```




- **Ordering**: Order from left (Most Significant Digit) to right (Least Significant Digit).
- **Negative Sign Detection**: Enable `DetectNegativeSign` to recognize minus signs (`-`) for reverse flow meters.
- **Model Selection**: Automatically pre-selected by Step 1 (`dig-class11_*` for LCD or `dig-class100_*` for mechanical drums).
- **Canvas Alignment Tools**: Use **Align Top/Bottom/Left/Right**, **Distribute Evenly**, and **Select All** to standardize digit heights and spacing.
- **Reference Specification**: ROI drawing adheres to the [AI-on-the-edge-device ROI Configuration Guide](https://jomjol.github.io/AI-on-the-edge-device-docs/ROI-Configuration/).



---

### Step 7: Analog Region of Interest (ROIs)
- Bounding boxes centered on rotating analog needle dials (`analog1`, `analog2`, `analog3`, ...). Pre-created if an analog preset was selected!
- **Ordering**: Order dials from largest unit ($0.1$) to smallest unit ($0.0001$).
- **Model Selection**: Automatically pre-selected by Step 1 (`ana-cont_*`).

---

### Step 8: Meters Definition & Consistency Rules
- Virtual meters combining the ROIs using bracket template syntax (pre-configured from preset):
  ```ini
  [Meter.main]
  Value = {digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}
  ```
- **Consistency Engine Options**:
  - `Allow Negative Rates`: `False` (prevents backward count glitches).
  - `Max Rate Value`: Set maximum allowable volume change per readout interval (e.g., `0.2 m³`, `0` = disabled).
  - `Min Rate Value`: Set minimum required volume delta when active consumption occurs (`0` = disabled).
  - `Stale Limit (hours)`: Set maximum elapsed hours without consumption change before flagging the meter as stale (`0` = disabled).
  - `Use Previous Value`: Automatically recover ambiguous or rolling digits (`N` / `?`) from the last validated baseline reading.
  - `Use Extended Resolution`: Enable fractional sub-digit decimal calculation from analog dial needles.


---

### Step 9: Services & Integrations
- **Poller**: Enable automated background cron schedule capture (e.g., `*/15 * * * * *` for every 15 seconds, or `0 */5 * * * *` for every 5 minutes).
- **MQTT**: Configure broker host, port, topic prefix (`watermeter`), and Home Assistant Auto-Discovery.

---

### Step 10: Final Review, Save & Live Deploy
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

[🏠 Wiki Home](Home) • [◀ Previous: Getting Started & Hardware Guide](Getting-Started-&-Hardware) • [Next: Dashboard, Features & Tools Guide ▶](Dashboard-&-Features-Guide)
