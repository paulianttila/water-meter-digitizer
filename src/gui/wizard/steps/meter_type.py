"""Meter Type Selection Step for Setup Wizard.

Allows selecting preset meter archetypes (LCD cumulative, LCD flow,
mechanical drums+dials, drums only, or custom). Auto-generates placeholder
ROIs, meter configurations, and recommends optimal CNN models.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nicegui import ui

from data_classes import ImagePosition, MeterConfig
from gui import theme
from gui.wizard.steps.base import BaseStep

HELP_TEXT = (
    "- **Quick-Start Presets**: Choose a preset matching your meter hardware to "
    "automatically generate placeholder ROI boxes, virtual meter definitions, "
    "and optimal CNN models.\n"
    "- **Customizable Counts**: Adjust the number of integer digits, decimal digits, "
    "or analog dials before proceeding.\n"
    "- **Fine-Tuning**: Pre-created ROI boxes will be placed on your image for easy "
    "repositioning and alignment in subsequent steps."
)


def select_best_model(
    options: dict[str, str],
    category_preference: str,
    preferred_filename: str | None = None,
) -> str | None:
    """Finds the best matching model path from available options dictionary.

    Args:
        options: Dict mapping file_path -> display_name (from _get_cnn_models)
        category_preference: e.g. 'class11', 'class100', 'continuous'
        preferred_filename: Optional target filename (e.g. 'dig-class11_1600_s2_q.tflite')

    Returns:
        The matched model key (file path) or None if options is empty.
    """
    if not options:
        return None

    keys = list(options.keys())

    # 1. Exact filename match if specified
    if preferred_filename:
        for k in keys:
            if Path(k).name == preferred_filename:
                return k

    # 2. Preference match with quantized model (_q.tflite preferred for edge efficiency)
    matches_q = [
        k
        for k in keys
        if category_preference.lower() in k.lower() and "_q.tflite" in k.lower()
    ]
    if matches_q:
        return sorted(matches_q, reverse=True)[0]

    # 3. Any match in the preferred category directory/name
    matches_cat = [k for k in keys if category_preference.lower() in k.lower()]
    if matches_cat:
        return sorted(matches_cat, reverse=True)[0]

    # 4. Fallback to first available option
    return keys[0]


def _make_positions_row(
    names: list[str],
    img_w: int,
    img_h: int,
    y_frac: float = 0.5,
    box_w_hint: int = 60,
    box_h_hint: int = 80,
) -> list[ImagePosition]:
    """Arranges a list of ROI names in a centered horizontal row."""
    n = len(names)
    if n == 0:
        return []

    gap = 6
    available_w = max(50, img_w - 40)
    box_w = max(24, min(box_w_hint, (available_w // n) - gap))
    box_h = max(30, min(box_h_hint, img_h // 4))
    total_w = n * box_w + (n - 1) * gap
    x0 = max(0, (img_w - total_w) // 2)
    y = max(0, int(img_h * y_frac) - (box_h // 2))

    return [
        ImagePosition(name=nm, x=x0 + i * (box_w + gap), y=y, w=box_w, h=box_h)
        for i, nm in enumerate(names)
    ]


@dataclass
class MeterTypePreset:
    id: str
    label: str
    description: str
    icon: str
    default_int_digits: int = 5
    default_dec_digits: int = 0
    default_analog_count: int = 0
    default_unit: str = "㎥"
    has_secondary_group: bool = False
    default_flow_int_digits: int = 3
    default_flow_dec_digits: int = 2
    digital_category_preference: str = "class100"
    digital_preferred_filename: str | None = None
    digital_cnn_type: str = "auto"
    analog_category_preference: str | None = None
    analog_preferred_filename: str | None = None
    analog_cnn_type: str = "auto"
    recommendation_reason: str = ""

    def get_digital_roi_names(
        self,
        int_digits: int,
        dec_digits: int,
        flow_int_digits: int = 0,
        flow_dec_digits: int = 0,
    ) -> list[str]:
        if self.id == "custom":
            return []
        names = [f"digit{i + 1}" for i in range(int_digits)]
        if dec_digits > 0:
            names.extend([f"decimal{i + 1}" for i in range(dec_digits)])
        if self.has_secondary_group:
            names.extend([f"flow{i + 1}" for i in range(flow_int_digits)])
            if flow_dec_digits > 0:
                names.extend([f"flow_dec{i + 1}" for i in range(flow_dec_digits)])
        return names

    def get_analog_roi_names(self, analog_count: int) -> list[str]:
        if (
            self.id == "custom"
            or self.analog_category_preference is None
            or analog_count <= 0
        ):
            return []
        return [f"analog{i + 1}" for i in range(analog_count)]

    def get_digital_roi_positions(
        self,
        names: list[str],
        img_w: int = 640,
        img_h: int = 480,
        flow_split: int = 0,
    ) -> list[ImagePosition]:
        if not names:
            return []
        if self.has_secondary_group and flow_split > 0 and flow_split < len(names):
            main_names = names[:-flow_split]
            flow_names = names[-flow_split:]
            return _make_positions_row(
                main_names, img_w, img_h, y_frac=0.35
            ) + _make_positions_row(flow_names, img_w, img_h, y_frac=0.65)
        return _make_positions_row(names, img_w, img_h, y_frac=0.45)

    def get_analog_roi_positions(
        self, names: list[str], img_w: int = 640, img_h: int = 480
    ) -> list[ImagePosition]:
        if not names:
            return []
        return _make_positions_row(
            names, img_w, img_h, y_frac=0.70, box_w_hint=70, box_h_hint=70
        )

    def build_meter_configs(
        self,
        digital_names: list[str],
        analog_names: list[str],
        unit: str = "㎥",
    ) -> list[MeterConfig]:
        if self.id == "custom":
            return []

        if self.id == "lcd_cumulative":
            int_names = [n for n in digital_names if not n.startswith("decimal")]
            dec_names = [n for n in digital_names if n.startswith("decimal")]
            fmt = "".join(f"{{{n}}}" for n in int_names)
            if dec_names:
                fmt += "." + "".join(f"{{{n}}}" for n in dec_names)
            return [
                MeterConfig(
                    name="total",
                    format=fmt,
                    unit=unit,
                    consistency_enabled=True,
                    use_previous_value=True,
                    max_rate_value=0.2,
                )
            ]

        if self.id == "lcd_cumulative_flow":
            main_names = [n for n in digital_names if not n.startswith("flow")]
            main_int = [n for n in main_names if not n.startswith("decimal")]
            main_dec = [n for n in main_names if n.startswith("decimal")]
            fmt_main = "".join(f"{{{n}}}" for n in main_int)
            if main_dec:
                fmt_main += "." + "".join(f"{{{n}}}" for n in main_dec)

            flow_names = [n for n in digital_names if n.startswith("flow")]
            flow_int = [n for n in flow_names if not n.startswith("flow_dec")]
            flow_dec = [n for n in flow_names if n.startswith("flow_dec")]
            fmt_flow = "".join(f"{{{n}}}" for n in flow_int)
            if flow_dec:
                fmt_flow += "." + "".join(f"{{{n}}}" for n in flow_dec)

            return [
                MeterConfig(
                    name="total",
                    format=fmt_main,
                    unit=unit,
                    consistency_enabled=True,
                    use_previous_value=True,
                    max_rate_value=0.2,
                ),
                MeterConfig(
                    name="flow",
                    format=fmt_flow,
                    unit=f"{unit}/h" if unit else "㎥/h",
                    consistency_enabled=False,
                    use_previous_value=False,
                    detect_negative_sign=True,
                ),
            ]

        if self.id == "analog_classic":
            fmt = "".join(f"{{{n}}}" for n in digital_names)
            if analog_names:
                fmt += "." + "".join(f"{{{n}}}" for n in analog_names)
            return [
                MeterConfig(
                    name="total",
                    format=fmt,
                    unit=unit,
                    use_extended_resolution=bool(analog_names),
                    consistency_enabled=True,
                    use_previous_value=True,
                    max_rate_value=0.2,
                )
            ]

        if self.id == "analog_drums_only":
            fmt = "".join(f"{{{n}}}" for n in digital_names)
            return [
                MeterConfig(
                    name="total",
                    format=fmt,
                    unit=unit,
                    consistency_enabled=True,
                    use_previous_value=True,
                    max_rate_value=0.2,
                )
            ]

        return []


PRESETS: list[MeterTypePreset] = [
    MeterTypePreset(
        id="lcd_cumulative",
        label="LCD - Cumulative",
        description="Digital 7-segment LCD showing single cumulative total reading.",
        icon="pin",
        default_int_digits=5,
        default_dec_digits=3,
        default_analog_count=0,
        default_unit="㎥",
        digital_category_preference="class11",
        digital_preferred_filename="dig-class11_1600_s2_q.tflite",
        digital_cnn_type="auto",
        recommendation_reason="class11 discrete models are optimized for 7-segment LCD digits (0-9).",
    ),
    MeterTypePreset(
        id="lcd_cumulative_flow",
        label="LCD - Total + Flow",
        description="Digital LCD showing cumulative total and instantaneous flow rate.",
        icon="speed",
        default_int_digits=5,
        default_dec_digits=3,
        default_analog_count=0,
        has_secondary_group=True,
        default_flow_int_digits=3,
        default_flow_dec_digits=2,
        default_unit="㎥",
        digital_category_preference="class11",
        digital_preferred_filename="dig-class11_1600_s2_q.tflite",
        digital_cnn_type="auto",
        recommendation_reason="class11 discrete models with negative sign detection for reverse flow.",
    ),
    MeterTypePreset(
        id="analog_classic",
        label="Mechanical - 5+4",
        description="5 rolling odometer drums with 4 rotating needle dials for decimals.",
        icon="tune",
        default_int_digits=5,
        default_dec_digits=0,
        default_analog_count=4,
        default_unit="㎥",
        digital_category_preference="class100",
        digital_preferred_filename="dig-class100_0168_s2_q.tflite",
        digital_cnn_type="auto",
        analog_category_preference="continuous",
        analog_preferred_filename="ana-cont_1209_s2.tflite",
        analog_cnn_type="auto",
        recommendation_reason="class100 reads continuously rolling counter drums; continuous pointer network reads needle dials.",
    ),
    MeterTypePreset(
        id="analog_drums_only",
        label="Mechanical - Drums",
        description="Mechanical meter with roller drums only (no analog dials).",
        icon="counter_5",
        default_int_digits=5,
        default_dec_digits=0,
        default_analog_count=0,
        default_unit="㎥",
        digital_category_preference="class100",
        digital_preferred_filename="dig-class100_0168_s2_q.tflite",
        digital_cnn_type="auto",
        recommendation_reason="class100 accurately classifies intermediate states of rolling counter drums.",
    ),
    MeterTypePreset(
        id="custom",
        label="Custom (Manual)",
        description="Blank canvas for completely custom ROI placement and manual configuration.",
        icon="edit_note",
        default_unit="㎥",
        recommendation_reason="Leaves current CNN model selections and ROIs untouched for manual setup.",
    ),
]

PRESET_BY_ID: dict[str, MeterTypePreset] = {p.id: p for p in PRESETS}


class MeterTypeStep(BaseStep):
    """Wizard step 2: Guided Meter Type selection with preset configuration."""

    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None] | None = None,
        spinner=None,
    ) -> None:
        super().__init__(name, set_image_callback=set_image_callback, spinner=spinner)
        self.selected_preset_id: str = "custom"
        self.int_digits: int = 5
        self.dec_digits: int = 3
        self.analog_count: int = 0
        self.unit: str = "㎥"
        self.flow_int_digits: int = 3
        self.flow_dec_digits: int = 2

        # UI Element References
        self._card_elements: dict[str, ui.card] = {}
        self._controls_container: ui.column | None = None
        self._dec_row: ui.row | None = None
        self._analog_row: ui.row | None = None
        self._flow_container: ui.column | None = None
        self._preview_label: ui.label | None = None
        self._cnn_rec_card: ui.card | None = None
        self._cnn_dig_label: ui.label | None = None
        self._cnn_ana_label: ui.label | None = None
        self._cnn_reason_label: ui.label | None = None

        # Input controls
        self._int_input: ui.number | None = None
        self._dec_input: ui.number | None = None
        self._analog_input: ui.number | None = None
        self._unit_input: ui.input | None = None
        self._flow_int_input: ui.number | None = None
        self._flow_dec_input: ui.number | None = None

    @property
    def selected_preset(self) -> MeterTypePreset | None:
        return PRESET_BY_ID.get(self.selected_preset_id)

    @property
    def effective_digital_roi_names(self) -> list[str]:
        preset = self.selected_preset
        if not preset:
            return []
        return preset.get_digital_roi_names(
            int_digits=self.int_digits,
            dec_digits=self.dec_digits,
            flow_int_digits=self.flow_int_digits,
            flow_dec_digits=self.flow_dec_digits,
        )

    @property
    def effective_analog_roi_names(self) -> list[str]:
        preset = self.selected_preset
        if not preset:
            return []
        return preset.get_analog_roi_names(analog_count=self.analog_count)

    def _select_preset(self, preset_id: str) -> None:
        self.selected_preset_id = preset_id
        preset = PRESET_BY_ID.get(preset_id)
        if preset and preset.id != "custom":
            self.int_digits = preset.default_int_digits
            self.dec_digits = preset.default_dec_digits
            self.analog_count = preset.default_analog_count
            self.unit = preset.default_unit
            self.flow_int_digits = preset.default_flow_int_digits
            self.flow_dec_digits = preset.default_flow_dec_digits

            if self._int_input:
                self._int_input.value = self.int_digits
            if self._dec_input:
                self._dec_input.value = self.dec_digits
            if self._analog_input:
                self._analog_input.value = self.analog_count
            if self._unit_input:
                self._unit_input.value = self.unit
            if self._flow_int_input:
                self._flow_int_input.value = self.flow_int_digits
            if self._flow_dec_input:
                self._flow_dec_input.value = self.flow_dec_digits

        self._update_ui_state()

    def _on_control_change(self) -> None:
        if self._int_input and self._int_input.value is not None:
            self.int_digits = int(self._int_input.value)
        if self._dec_input and self._dec_input.value is not None:
            self.dec_digits = int(self._dec_input.value)
        if self._analog_input and self._analog_input.value is not None:
            self.analog_count = int(self._analog_input.value)
        if self._unit_input and self._unit_input.value is not None:
            self.unit = str(self._unit_input.value)
        if self._flow_int_input and self._flow_int_input.value is not None:
            self.flow_int_digits = int(self._flow_int_input.value)
        if self._flow_dec_input and self._flow_dec_input.value is not None:
            self.flow_dec_digits = int(self._flow_dec_input.value)

        self._update_preview()

    def _update_ui_state(self) -> None:
        # Update card active/inactive styles
        for pid, card in self._card_elements.items():
            if pid == self.selected_preset_id:
                card.classes(replace=theme.CARD_SELECTABLE_ACTIVE)
            else:
                card.classes(replace=theme.CARD_SELECTABLE_INACTIVE)

        preset = self.selected_preset
        is_custom = preset is None or preset.id == "custom"

        # Show/hide configuration container
        if self._controls_container:
            self._controls_container.set_visibility(not is_custom)

        # Show/hide sub-sections
        if preset and not is_custom:
            if self._dec_row:
                self._dec_row.set_visibility(
                    preset.id in ("lcd_cumulative", "lcd_cumulative_flow")
                )
            if self._analog_row:
                self._analog_row.set_visibility(preset.id == "analog_classic")
            if self._flow_container:
                self._flow_container.set_visibility(preset.has_secondary_group)

        # Update CNN recommendation panel
        if self._cnn_rec_card:
            self._cnn_rec_card.set_visibility(not is_custom)
        if preset and not is_custom:
            if self._cnn_dig_label:
                dig_rec = (
                    f"{preset.digital_category_preference} ("
                    f"{preset.digital_preferred_filename or 'quantized'})"
                )
                self._cnn_dig_label.set_text(dig_rec)
            if self._cnn_ana_label:
                ana_rec = (
                    f"{preset.analog_category_preference} ("
                    f"{preset.analog_preferred_filename or 'quantized'})"
                    if preset.analog_category_preference
                    else "None (Not needed for this meter type)"
                )
                self._cnn_ana_label.set_text(ana_rec)
            if self._cnn_reason_label:
                self._cnn_reason_label.set_text(preset.recommendation_reason)

        self._update_preview()

    def _update_preview(self) -> None:
        if not self._preview_label:
            return
        preset = self.selected_preset
        if not preset or preset.id == "custom":
            self._preview_label.set_text(
                "Custom mode: No automatic ROIs or meters will be created."
            )
            return

        dig_names = self.effective_digital_roi_names
        ana_names = self.effective_analog_roi_names
        configs = preset.build_meter_configs(dig_names, ana_names, unit=self.unit)

        preview_lines = []
        for cfg in configs:
            preview_lines.append(f"Meter '{cfg.name}': {cfg.format} [{cfg.unit}]")
        self._preview_label.set_text("\n".join(preview_lines))

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            # Header row
            with ui.row().classes("w-full items-center gap-2 mb-2"):
                ui.icon("speed", size="sm").classes("text-indigo-400")
                ui.label("Select Your Meter Type").classes(theme.HEADING_SECTION)

            # Presets Grid
            with ui.grid(columns=3).classes(
                "w-full gap-3 mb-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3"
            ):
                for p in PRESETS:
                    init_cls = (
                        theme.CARD_SELECTABLE_ACTIVE
                        if p.id == self.selected_preset_id
                        else theme.CARD_SELECTABLE_INACTIVE
                    )
                    card = ui.card().classes(init_cls)
                    self._card_elements[p.id] = card

                    with card:
                        card.on("click", lambda _, pid=p.id: self._select_preset(pid))
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.icon(p.icon, size="md").classes("text-indigo-400")
                            if p.id == "custom":
                                ui.badge("Blank", color="slate").classes("text-[10px]")
                            else:
                                ui.badge("Preset", color="indigo").classes(
                                    "text-[10px]"
                                )
                        ui.label(p.label).classes(
                            "font-semibold text-sm text-gray-100 mt-2"
                        )
                        ui.label(p.description).classes(
                            "text-xs text-gray-400 leading-relaxed mt-1"
                        )

            # Customizable Controls Container
            self._controls_container = ui.column().classes("w-full gap-3 mb-3")
            with self._controls_container, ui.card().classes(theme.CARD_DEFAULT):
                with ui.row().classes("w-full items-center gap-2 mb-2"):
                    ui.icon("tune", size="xs").classes("text-cyan-400")
                    ui.label("Customize Digits & Dials").classes(
                        theme.HEADING_SUBSECTION
                    )

                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    self._int_input = (
                        ui.number(
                            label="Integer Digits",
                            value=self.int_digits,
                            min=1,
                            max=10,
                            step=1,
                            on_change=lambda _: self._on_control_change(),
                        )
                        .props("dense outlined")
                        .classes("w-32")
                    )

                    with ui.row().classes("items-center") as self._dec_row:
                        self._dec_input = (
                            ui.number(
                                label="Decimal Digits",
                                value=self.dec_digits,
                                min=0,
                                max=6,
                                step=1,
                                on_change=lambda _: self._on_control_change(),
                            )
                            .props("dense outlined")
                            .classes("w-32")
                        )

                    with ui.row().classes("items-center") as self._analog_row:
                        self._analog_input = (
                            ui.number(
                                label="Analog Dials",
                                value=self.analog_count,
                                min=1,
                                max=8,
                                step=1,
                                on_change=lambda _: self._on_control_change(),
                            )
                            .props("dense outlined")
                            .classes("w-32")
                        )

                    self._unit_input = (
                        ui.input(
                            label="Unit",
                            value=self.unit,
                            on_change=lambda _: self._on_control_change(),
                        )
                        .props("dense outlined")
                        .classes("w-28")
                    )

                # Secondary Flow Group Sub-Panel
                self._flow_container = ui.column().classes("w-full pt-2")
                with self._flow_container:
                    ui.separator().classes("my-1 opacity-20")
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.icon("waves", size="xs").classes("text-cyan-400")
                        ui.label("Flow Rate Reading Digits").classes(
                            theme.TEXT_MONO_MUTED
                        )
                    with ui.row().classes("w-full items-center gap-4 mt-1"):
                        self._flow_int_input = (
                            ui.number(
                                label="Flow Int Digits",
                                value=self.flow_int_digits,
                                min=1,
                                max=6,
                                step=1,
                                on_change=lambda _: self._on_control_change(),
                            )
                            .props("dense outlined")
                            .classes("w-36")
                        )
                        self._flow_dec_input = (
                            ui.number(
                                label="Flow Dec Digits",
                                value=self.flow_dec_digits,
                                min=0,
                                max=4,
                                step=1,
                                on_change=lambda _: self._on_control_change(),
                            )
                            .props("dense outlined")
                            .classes("w-36")
                        )

            # Neural Network Model Recommendations Panel
            self._cnn_rec_card = ui.card().classes(f"{theme.CARD_DEFAULT} mb-3")
            with self._cnn_rec_card:
                with ui.row().classes("w-full items-center gap-2 mb-2"):
                    ui.icon("psychology", size="xs").classes("text-indigo-400")
                    ui.label("Neural Network Model Recommendations").classes(
                        theme.HEADING_SUBSECTION
                    )

                with ui.row().classes(
                    "w-full items-center justify-between gap-4 flex-wrap"
                ):
                    with ui.column().classes("gap-1"):
                        ui.label("Digit Neural Network:").classes(theme.TEXT_MONO_MUTED)
                        self._cnn_dig_label = ui.label("").classes(
                            "text-sm font-semibold text-cyan-300 font-mono"
                        )
                    with ui.column().classes("gap-1"):
                        ui.label("Pointer Neural Network:").classes(
                            theme.TEXT_MONO_MUTED
                        )
                        self._cnn_ana_label = ui.label("").classes(
                            "text-sm font-semibold text-amber-300 font-mono"
                        )

                self._cnn_reason_label = ui.label("").classes(
                    "text-xs text-slate-400 italic mt-1"
                )

            # Live Preview Card
            with ui.card().classes(f"{theme.CARD_DEFAULT} mb-3"):
                with ui.row().classes("w-full items-center gap-2 mb-1"):
                    ui.icon("preview", size="xs").classes("text-emerald-400")
                    ui.label("Virtual Meter Format Preview").classes(
                        theme.HEADING_SUBSECTION
                    )

                self._preview_label = ui.label("").classes(
                    "w-full p-2.5 rounded-lg bg-slate-950 font-mono text-xs "
                    "text-emerald-300 whitespace-pre border border-white/5"
                )

            self._update_ui_state()
            super().add_navigator(stepper, first_step, last_step)
