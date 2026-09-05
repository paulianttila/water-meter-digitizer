from nicegui import ui


class HelpPage:
    def __init__(self) -> None:
        pass

    def show(self) -> None:
        with ui.row().classes("w-full justify-between items-center mb-3"):
            ui.label("Help & Documentation").classes("text-h4")
            ui.label("Guide & Shortcuts").classes(
                "text-xs font-semibold text-cyan-400 bg-cyan-500/10 "
                "border border-cyan-500/30 px-3 py-1 rounded-full"
            )

        with ui.column().classes("w-full max-w-4xl gap-3"):
            with ui.expansion(
                "Overview & Navigation", icon="explore", value=True
            ).classes("w-full bg-slate-900/60 border border-white/10 rounded-xl"):
                ui.markdown(
                    "- **Meter**: View live meter readings, trigger manual "
                    "readouts, and inspect individual CNN predictions.\n"
                    "- **Setup**: Interactive 8-step wizard for camera capture, "
                    "affine alignment, ROI bounding boxes, and meter formatting.\n"
                    "- **Config**: Raw `config.ini` editor with real-time "
                    "syntax checking, JSON visualization, and hot reloading.\n"
                    "- **About**: Version information, runtime details, and "
                    "system architecture summary."
                ).classes("p-2 text-sm text-gray-300 leading-relaxed")

            with ui.expansion(
                "Setup Wizard Workflow (8 Steps)", icon="checklist", value=True
            ).classes("w-full bg-slate-900/60 border border-white/10 rounded-xl"):
                ui.markdown(
                    "1. **Download Image**: Enter camera snapshot URL and "
                    "timeout. If offline, a placeholder graphic will display.\n"
                    "2. **Initial Rotate**: Rotate coarse 90° increments "
                    "(0°, 90°, 180°, 270°) to orient meter text upright.\n"
                    "3. **Reference Points**: Mark 3 distinct visual landmarks "
                    "(screws, labels, dial centers) for affine alignment.\n"
                    "4. **Image Adjustments**: Fine-tune rotation angle "
                    "(e.g. 0.5°), test alignment, and configure "
                    "contrast/sharpness filters.\n"
                    "5. **Digital ROIs**: Add bounding boxes for mechanical "
                    "drum digits, select CNN models, and test inference.\n"
                    "6. **Analog ROIs**: Add bounding boxes for circular dial "
                    "needles, select CNN models, and test angle detection.\n"
                    "7. **Meters Definition**: Define logical meter outputs, "
                    "rate limits, previous value fallbacks, and units.\n"
                    "8. **Final Review & Save**: Review compiled configuration, "
                    "save reference files, and apply settings to runtime."
                ).classes("p-2 text-sm text-gray-300 leading-relaxed")

            with ui.expansion("Interactive Canvas Controls", icon="touch_app").classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl"
            ):
                ui.markdown(
                    "- **Draw Bounding Box**: Click and drag on the interactive "
                    "image canvas on the left side of the Setup page.\n"
                    "- **Hover Coordinates**: Real-time pixel X and Y coordinates "
                    "are displayed in the status row below the image.\n"
                    "- **Toggle Visibility**: Check or uncheck colored checkboxes "
                    "in ROI table to display or hide individual boxes on canvas.\n"
                    "- **Batch Alignment**: Use toolbar buttons (Left, Top, Center, "
                    "Resize) to quickly align and standardize ROI dimensions."
                ).classes("p-2 text-sm text-gray-300 leading-relaxed")

            with ui.expansion("Troubleshooting Common Issues", icon="help").classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl"
            ):
                ui.markdown(
                    "- **Camera Offline / Timeout**: Verify camera network "
                    "connectivity, check URL in Step 1, or increase timeout.\n"
                    "- **Digit Misalignment / Shifting**: Ensure reference markers "
                    "in Step 3 are placed on rigid, high-contrast landmarks.\n"
                    "- **Unreadable Digits (`N`)**: Ensure bounding boxes fit "
                    "snugly; adjust contrast or enable `AutoContrastCutImages`.\n"
                    "- **Decreasing Readings Rejected**: Check `AllowNegativeRates` "
                    "in Step 7 if the physical meter rolled over or replaced."
                ).classes("p-2 text-sm text-gray-300 leading-relaxed")
