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
                    "- **Meter**: View live meter readings, trigger manual readouts,\n"
                    "  and inspect individual CNN confidence and outputs.\n"
                    "- **Setup**: Interactive 8-step wizard for camera capture,\n"
                    "  affine alignment, ROI bounding boxes, and meter formatting.\n"
                    "- **Config**: Raw `config.ini` editor with real-time syntax\n"
                    "  checking, JSON visualization, and hot reloading.\n"
                    "- **About**: Version information and application summary."
                )

            with ui.expansion(
                "Setup Wizard Workflow (8 Steps)", icon="checklist", value=True
            ).classes("w-full border rounded"):
                ui.markdown(
                    "1. **Download Image**: Enter camera snapshot URL and timeout.\n"
                    "   If offline, a placeholder graphic will display.\n"
                    "2. **Initial Rotate**: Rotate coarse 90° increments\n"
                    "   (0°, 90°, 180°, 270°) to orient meter text upright.\n"
                    "3. **Reference Points**: Mark 3 distinct visual landmarks\n"
                    "   (screws, labels, dial centers) for affine alignment.\n"
                    "4. **Image Adjustments**: Fine-tune rotation angle (e.g. 0.5°),\n"
                    "   test alignment, and configure contrast/sharpness filters.\n"
                    "5. **Digital ROIs**: Add bounding boxes for mechanical drum or\n"
                    "   LCD digits, select CNN models, and test inference.\n"
                    "6. **Analog ROIs**: Add bounding boxes for circular dial\n"
                    "   needles, select CNN models, and test angle detection.\n"
                    "7. **Meters Definition**: Define logical meter outputs, rate\n"
                    "   limits, previous value fallbacks, and units.\n"
                    "8. **Final Review & Save**: Review compiled configuration,\n"
                    "   save reference files, and apply settings to runtime."
                )

            with ui.expansion("Interactive Canvas Controls", icon="touch_app").classes(
                "w-full border rounded"
            ):
                ui.markdown(
                    "- **Draw Bounding Box**: Click and drag on the interactive\n"
                    "  image canvas on the left side of the Setup page.\n"
                    "- **Hover Coordinates**: Real-time pixel X and Y coordinates\n"
                    "  are displayed in the status row below the image.\n"
                    "- **Toggle Visibility**: Check or uncheck colored checkboxes\n"
                    "  in ROI table to display or hide individual boxes on canvas.\n"
                    "- **Batch Alignment**: Use toolbar buttons (Left, Top, Center,\n"
                    "  Resize) to quickly align and standardize ROI dimensions."
                )

            with ui.expansion("Troubleshooting Common Issues", icon="help").classes(
                "w-full border rounded"
            ):
                ui.markdown(
                    "- **Camera Offline / Timeout**: Verify camera network\n"
                    "  connectivity, check URL in Step 1, or increase timeout.\n"
                    "- **Digit Misalignment / Shifting**: Ensure reference markers\n"
                    "  in Step 3 are placed on rigid, high-contrast landmarks.\n"
                    "- **Unreadable Digits (`N`)**: Ensure bounding boxes fit\n"
                    "  snugly; adjust contrast or enable `AutoContrastCutImages`.\n"
                    "- **Decreasing Readings Rejected**: Check `AllowNegativeRates`\n"
                    "  in Step 7 if the physical meter rolled over or replaced."
                )
