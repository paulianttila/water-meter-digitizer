# Web GUI User Guide & Setup Manual

The **Water Meter System** features a built-in web interface served on port `3000` (accessible by default at `http://localhost:3000`).

---

## Table of Contents

1. [Overview & Navigation](#overview--navigation)
2. [Meter Page (Live Readouts)](#meter-page-live-readouts)
3. [Setup Wizard (Step-by-Step)](#setup-wizard-step-by-step)
   - [Step 1: Download Image](#step-1-download-image)
   - [Step 2: Initial Rotate](#step-2-initial-rotate)
   - [Step 3: Reference Points](#step-3-reference-points)
   - [Step 4: Image Adjustments & Alignment](#step-4-image-adjustments--alignment)
   - [Step 5: Digital Region of Interest (ROIs)](#step-5-digital-region-of-interest-rois)
   - [Step 6: Analog Region of Interest (ROIs)](#step-6-analog-region-of-interest-rois)
   - [Step 7: Meters Definition](#step-7-meters-definition)
   - [Step 8: Final Review & Save](#step-8-final-review--save)
4. [Interactive Canvas Controls](#interactive-canvas-controls)
5. [Config Editor Page](#config-editor-page)
6. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## Overview & Navigation

The interface is divided into a collapsible left sidebar and the main workspace:

| Tab | Icon | Purpose |
|---|---|---|
| **Meter** | `speed` | View live readings, trigger manual readouts, and inspect intermediate CNN outputs. |
| **Setup** | `settings` | Interactive 8-step wizard for camera capture, alignment, ROI bounding boxes, and meter configuration. |
| **Config** | `manufacturing` | Raw `config.ini` text editor with syntax verification, JSON schema inspection, and reload/save tools. |
| **Help** | `help_outline` | Built-in guide and keyboard/mouse shortcut reference. |
| **About** | `info` | Version information and system summary. |

---

## Meter Page (Live Readouts)

The **Meter** tab provides an operational overview of the digitizer:
- **Trigger Readout**: Click the refresh button to capture a frame and perform immediate inference.
- **Save Intermediate Images**: Checkbox to save rotated, aligned, and cropped ROI images to `/image_tmp` for diagnostics.
- **Meter Cards**: Displays current readings with units (e.g. `0300.957 m³`), timestamp, and processing duration.
- **Sub-digit Readouts**: Inspect the individual classification confidence and predictions for each digital drum digit and analog needle dial.

---

## Setup Wizard (Step-by-Step)

The **Setup** tab provides an 8-step guided configuration wizard. On the left is the **Interactive Image Canvas** (showing real-time coordinates, image dimensions, and SVG ROI overlays), and on the right is the **Step Navigator**.

### Step 1: Download Image
- **Camera URL**: Enter the HTTP snapshot endpoint (e.g. `http://192.168.1.100/capture` or `file:///config/original.jpg`).
- **Timeout**: Set the network request timeout in seconds (1–60s).
- **Download Button**: Fetches a frame from the camera. If the camera is unreachable or times out, the interactive canvas displays an offline placeholder graphic with retry instructions without crashing the page.

### Step 2: Initial Rotate
- **Coarse Rotation**: Rotate the image in 90° increments (`0°`, `90°`, `180°`, `270°`) so the meter numbers and dials are oriented right-side up.

### Step 3: Reference Points
- Aligning the camera capture is crucial to compensate for minor vibration or camera repositioning.
- The system requires **3 distinct visual landmarks** (e.g. screws, text labels like `m³`, dial centers, or logo corners).
- **Adding a Reference**: Click `+` to add a reference point, then click and drag on the interactive image to define its bounding box.
- **Color Coding**: Each reference ROI is assigned a distinct color (Red, Blue, Green) matched across the checkbox list and canvas.

### Step 4: Image Adjustments & Alignment
- **Fine Rotation**: Adjust rotation by small fractional angles (e.g. `0.5°`).
- **Alignment Test**: Click **Test Alignment** to execute OpenCV affine transformation against the 3 reference markers.
- **Image Filters**: Adjust `Contrast`, `Brightness`, `Color`, and `Sharpness` multipliers.
- **Grayscale**: Toggle grayscale conversion.
- **AutoContrast**: Enable histogram equalisation with customizable lower and upper percentile cutoffs.

### Step 5: Digital Region of Interest (ROIs)
- Define bounding boxes for mechanical drum digits or LCD numbers.
- **Add / Remove**: Use `+` and `-` buttons to manage digits (`digit1`, `digit2`, ...).
- **Positioning**: Drag a box on the interactive canvas or enter precise `X`, `Y`, `W`, `H` coordinates.
- **Alignment Tools**:
  - **Align Left / Right / Top / Bottom / Center**: Aligns selected ROIs along the specified edge or axis.
  - **Resize All**: Matches the dimensions of all selected ROIs to the first selected digit.
- **CNN Model**: Choose a pre-trained `.tflite` model from `/config/neuralnets/digital`.
- **CNN Type**:
  - `auto`: Automatically detected from model shape.
  - `digital`: Standard classification (0–9 + invalid).
  - `digital100`: High-resolution continuous rolling digit model (0–99).
- **Test Inference**: Click **Test** to crop the ROIs, run inference, and preview predicted digit numbers in real time.

### Step 6: Analog Region of Interest (ROIs)
- Define circular bounding boxes for analog dial needles (`analog1`, `analog2`, ...).
- **Alignment Tools**: Use the same left/top/center alignment and size matching tools as digital ROIs.
- **CNN Model**: Choose a pre-trained `.tflite` model from `/config/neuralnets/analog`.
- **CNN Type**:
  - `auto`: Detected from model shape.
  - `analog`: 0–10 continuous angle prediction.
  - `analog100`: High-resolution 100-class angular prediction (0–9.99).
- **Test Inference**: Click **Test** to run needle angle detection and inspect real-time outputs.

### Step 7: Meters Definition
- Define one or more named logical meters (e.g. `main`, `total`, `instant`).
- **Format Template**: Combine digit and analog variables (e.g. `{digit1}{digit2}{digit3}{digit4}.{digit5}{digit6}{analog1}`).
- **Consistency Checking**:
  - **Enabled**: Validates rate of consumption against previous reading.
  - **Max Rate Value**: Maximum allowed increment per reading interval.
  - **Allow Negative Rates**: Reject decreasing meter values.
- **Previous Value Handling**:
  - **Use Previous Value**: Automatically replace unreadable digits (`N`) with the last known valid reading.
  - **Max Age (Minutes)**: Expire cached previous values older than the threshold (`0` = no expiration).
- **Extended Resolution**: Append fractional sub-digit decimal places from the lowest analog needle.
- **Unit**: Custom unit string (e.g. `m³`, `L`, `kWh`).

### Step 8: Final Review & Save
- Review the compiled configuration and live processed image.
- **Save Config**: Writes the configuration to `/config/config.ini`.
- **Save Reference Images**: Saves cropped reference marker landmark files to `/config`.
- **Take In Use**: Applies the configuration to the active runtime engine immediately.

---

## Interactive Canvas Controls

| Action | Control / Gesture |
|---|---|
| **Draw ROI Box** | Click & Drag on the image canvas |
| **View Coordinates** | Hover mouse over any pixel (displays `X: ...`, `Y: ...` in the HUD) |
| **Select ROI Coordinate** | Click on any pixel |
| **Toggle ROI Visibility** | Check / Uncheck the colored checkbox in the ROI table |
| **Show All / Hide All** | Toggle the `Show` master checkbox in the table header |

---

## Config Editor Page

For power users, the **Config** tab allows direct editing of the INI configuration:
- **Syntax Check (`verified`)**: Validates INI syntax and parameter types before saving.
- **Save (`save`)**: Writes changes directly to `config.ini`.
- **Take in Use (`reopen_window`)**: Hot-reloads the active runtime without restarting the container.
- **Show Parsed JSON (`preview`)**: Visualizes the parsed configuration hierarchy in formatted JSON.
- **Reload (`refresh`)**: Reverts unsaved changes in the editor from disk.

---

## Troubleshooting & FAQs

### Why does the canvas show "Camera Offline / Unreachable"?
- Check that the camera URL in Step 1 is correct and reachable from the container network.
- Verify camera authentication or network firewalls.
- Increase the timeout value (e.g. from `10s` to `30s`) for slow Wi-Fi camera modules.

### Why are digit bounding boxes shifting between captures?
- Ensure reference markers in Step 3 are placed on rigid, high-contrast, non-reflective landmarks.
- Ensure the reference images do not contain moving parts (like rotating needles or rolling numbers).

### Why does a digit show `N` (unreadable)?
- Ensure the ROI bounding box is centered tightly around the digit.
- Check contrast and sharpness in Step 4 or enable `AutoContrastCutImages`.
- Verify the correct CNN model file is selected.
