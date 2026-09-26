# Meter Models Directory (`config/meter_types/`)

This directory contains modular configuration template files (`*.ini`) and optional faceplate reference images (`*.jpg`, `*.png`) for meter models and archetypes used in Step 1 (**Meter type**) and Step 2 (**Download image**) of the Setup Wizard.

## Contributing a New Meter Model

To add support for a new water, gas, or electricity meter model:

1. Copy `_template.ini` to a new file named after your meter (e.g. `zenner_etkd.ini` or `badger_meter_e_series.ini`).
   - Files starting with `_` or `.` are ignored by the loader.
2. If available, place a 640×480 faceplate reference photo in the same directory (e.g. `zenner_etkd.jpg`) and reference it in the `[Template]` section via `Image = zenner_etkd.jpg`. This makes the image selectable in the Setup Wizard via `model://zenner_etkd`.
3. Edit the fields in your INI file:
   - `[Template]` section:
     - `Id`: Unique identifier (e.g. `zenner_etkd`).
     - `Category`: `"smart"`, `"mechanical"`, or `"generic"`.
     - `Brand`: Manufacturer name (e.g. `Zenner`).
     - `Model`: Model name (e.g. `ETKD / MNK`).
     - `Label`: Display name in the dropdown (e.g. `Zenner ETKD (Mechanical 5+4)`).
     - `Description`: Brief description of display and registers.
     - `Icon`: Material/Quasar icon (e.g. `tune`, `speed`, `water_drop`, `counter_5`).
     - `MeterTechnology`: `ultrasonic_lcd`, `mechanical_dial`, `mechanical_drum`, etc.
     - `DefaultIntDigits`, `DefaultDecDigits`, `DefaultAnalogCount`: Standard register counts.
     - `ReferenceWidth`, `ReferenceHeight`: Calibrated canvas dimensions (e.g. 640×480). All coordinates auto-scale to active camera resolution.
     - `DigitalCategoryPreference`: `"class11"` for LCD digits, `"class100"` for rolling counter drums.
     - `AnalogCategoryPreference`: `"continuous"` for rotating needle pointer dials.
   - Standard sections:
     - `[Alignment]`: Initial coarse rotation (`RotationAngle`) and 3 stationary reference marker anchor ROIs (`Refs = ref0, ref1, ref2`).
     - `[Digits]`: Pre-placed digital boxes (`Names = digit1, ...`, `[Digits.digit1] x=... y=... w=... h=...`).
     - `[Analog]`: Pre-placed analog dial boxes (`Names = analog1, ...`, `[Analog.analog1] x=... y=... w=... h=...`).
     - `[ImageProcessing]`: Recommended camera preprocessing (contrast, gamma, unsharp masking, CLAHE glare suppression).
     - `[Meters]`: Declarative virtual meter definitions using `{digits}`, `{decimals}`, `{analogs}`, `{flow_digits}`, `{flow_decimals}` tags.
4. Verify your configuration with unit tests:
   ```bash
   uv run pytest tests/unit/config/test_meter_presets.py
   ```
5. Submit a Pull Request! Because each meter model is in its own isolated `.ini` file, your contribution will never produce git merge conflicts.
