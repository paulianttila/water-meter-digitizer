from nicegui import ui


class HelpPage:
    def __init__(self) -> None:
        pass

    def show(self) -> None:
        ui.label("Help & Documentation").classes("text-h4")

        with ui.column().classes("w-full gap-3 mt-2"):
            with ui.expansion(
                "Overview & Navigation", icon="explore", value=True
            ).classes("w-full border rounded"):
                ui.markdown(
                    """
- **Meter**: View live meter readings, trigger manual readouts, and inspect individual CNN confidence and outputs.
- **Setup**: Interactive 8-step wizard for camera capture, affine reference alignment, ROI bounding boxes, and meter formatting.
- **Config**: Raw `config.ini` editor with real-time syntax checking, JSON visualization, and hot reloading.
- **About**: Version information and application summary.
                    """
                )

            with ui.expansion(
                "Setup Wizard Workflow (8 Steps)", icon="checklist", value=True
            ).classes("w-full border rounded"):
                ui.markdown(
                    """
1. **Download Image**: Enter your camera snapshot URL and timeout. If offline, a placeholder graphic will display with retry instructions.
2. **Initial Rotate**: Rotate coarse 90° increments (0°, 90°, 180°, 270°) to orient meter text and dials upright.
3. **Reference Points**: Mark 3 distinct visual landmarks (e.g. screws, text labels, dial centers) to establish affine alignment against camera vibration.
4. **Image Adjustments**: Fine-tune rotation angle (e.g. 0.5°), test alignment, and configure contrast/brightness/sharpness/autocontrast.
5. **Digital ROIs**: Add bounding boxes for mechanical drum or LCD digits, select CNN models (`digital`/`digital100`), and test inference in real time.
6. **Analog ROIs**: Add bounding boxes for circular dial needles, select CNN models (`analog`/`analog100`), and test angle detection.
7. **Meters Definition**: Define logical meter outputs (e.g. `{digit1}{digit2}.{analog1}`), rate limits, previous value fallbacks, and units.
8. **Final Review & Save**: Review the compiled configuration, save reference landmark files, and apply the new configuration to the live system.
                    """
                )

            with ui.expansion(
                "Interactive Canvas Controls", icon="touch_app"
            ).classes("w-full border rounded"):
                ui.markdown(
                    """
- **Draw Bounding Box**: Click and drag on the interactive image canvas on the left side of the Setup page.
- **Hover Coordinates**: Real-time pixel X and Y coordinates are displayed in the status row below the image.
- **Toggle Visibility**: Check or uncheck colored checkboxes in the ROI table to display or hide individual boxes on the canvas.
- **Batch Alignment**: Use toolbar buttons (Left, Top, Bottom, Right, Center, Resize All) to quickly align and standardize ROI dimensions.
                    """
                )

            with ui.expansion(
                "Troubleshooting Common Issues", icon="help"
            ).classes("w-full border rounded"):
                ui.markdown(
                    """
- **Camera Offline / Download Timeout**: Verify camera network connectivity, check URL in Step 1, or increase timeout.
- **Digit Misalignment / Shifting**: Ensure reference markers in Step 3 are placed on rigid, high-contrast, non-moving landmarks.
- **Unreadable Digits (`N`)**: Ensure bounding boxes fit snugly around digits without clipping borders; adjust contrast/brightness or enable `AutoContrastCutImages`.
- **Decreasing Readings Rejected**: Check `AllowNegativeRates` in Step 7 if the physical meter rolled over or was replaced.
                    """
                )

