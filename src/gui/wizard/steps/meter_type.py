"""Meter Type Selection Step for Setup Wizard.

Allows selecting preset meter archetypes and specific hardware models (Axioma,
Kamstrup, Diehl, Honeywell, Itron, B Meters, etc.) via a searchable dropdown
or category filters. Auto-generates placeholder ROIs, meter configurations,
and recommends optimal CNN models.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from config.meter_presets import (
    DEFAULT_BUILTIN_PRESETS,
    MeterTypePreset,
    load_meter_presets,
    reload_meter_presets,
    sort_meter_presets,
)
from gui import theme
from gui.wizard.steps.base import BaseStep

HELP_TEXT = (
    "- **Quick-Start Presets**: Search and choose a preset matching your meter hardware "
    "to automatically generate placeholder ROI boxes, virtual meter definitions, "
    "and optimal CNN models.\n"
    "- **European & Generic Models**: Includes Axioma Qalcosonic, Kamstrup flowIQ, "
    "Diehl Hydrus/Altair, Honeywell V200, Itron Aquadis+, and standard generic archetypes.\n"
    "- **Customizable Counts**: Adjust the number of integer digits, decimal digits, "
    "or analog dials before proceeding.\n"
    "- **Configuration Driven**: Add your own meter models anytime by dropping an "
    "INI file into `config/meter_types/`."
)

PRESETS: list[MeterTypePreset] = load_meter_presets()
PRESET_BY_ID: dict[str, MeterTypePreset] = {p.id: p for p in PRESETS}


def reload_presets(config_dir: str | Path | None = None) -> list[MeterTypePreset]:
    """Reloads presets from disk and updates module-level PRESETS and PRESET_BY_ID."""
    global PRESETS, PRESET_BY_ID
    loaded = reload_meter_presets(config_dir=config_dir)
    PRESETS.clear()
    PRESETS.extend(loaded)
    PRESET_BY_ID.clear()
    PRESET_BY_ID.update({p.id: p for p in PRESETS})
    return list(PRESETS)


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


class MeterTypeStep(BaseStep):
    """Wizard step 2: Guided Meter Type selection with preset configuration."""

    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None] | None = None,
        spinner=None,
        config_dir: str | Path | None = None,
        on_preset_selected: Callable[[MeterTypePreset], None] | None = None,
    ) -> None:
        super().__init__(name, set_image_callback=set_image_callback, spinner=spinner)
        self.config_dir = config_dir
        self.on_preset_selected = on_preset_selected
        self.selected_preset_id: str = "custom"
        self.active_category: str = "all"

        self.int_digits: int = 5
        self.dec_digits: int = 3
        self.analog_count: int = 0
        self.unit: str = "m³"
        self.flow_int_digits: int = 3
        self.flow_dec_digits: int = 2
        self._suppress_control_change: bool = False

        # UI References
        self._category_toggle: ui.toggle | None = None
        self._preset_select: ui.select | None = None
        self._model_info_card: ui.card | None = None
        self._model_title: ui.label | None = None
        self._model_badge: ui.badge | None = None
        self._model_desc: ui.label | None = None
        self._model_icon: ui.icon | None = None

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

        self.presets: list[MeterTypePreset] = []
        self.preset_by_id: dict[str, MeterTypePreset] = {}
        self.refresh_presets(force_reload=False)

    @property
    def selected_preset(self) -> MeterTypePreset | None:
        return self.preset_by_id.get(self.selected_preset_id)

    def refresh_presets(self, force_reload: bool = False) -> list[MeterTypePreset]:
        """Reloads presets from disk and updates UI dropdown options if rendered."""
        loaded = load_meter_presets(self.config_dir, force_reload=force_reload)
        if not loaded:
            loaded = list(DEFAULT_BUILTIN_PRESETS)
        default_presets = load_meter_presets(force_reload=force_reload)
        existing_ids = {p.id for p in loaded}
        for dp in default_presets:
            if dp.id not in existing_ids:
                loaded.append(dp)
        self.presets = sort_meter_presets(loaded)
        self.preset_by_id = {p.id: p for p in self.presets}

        if force_reload:
            reload_presets(self.config_dir)

        preset_sel = getattr(self, "_preset_select", None)
        if preset_sel is not None:
            options = self._get_filtered_preset_options()
            preset_sel.options = options
            if self.selected_preset_id not in self.preset_by_id and options:
                self._select_preset(next(iter(options)))
            else:
                preset_sel.update()
        return self.presets

    def _handle_refresh_click(self) -> None:
        self.refresh_presets(force_reload=True)
        ui.notify("Meter templates reloaded from disk", type="positive")

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

    def _get_filtered_preset_options(self) -> dict[str, str]:
        """Returns mapping of preset_id -> display label filtered by active category."""
        result: dict[str, str] = {}
        for p in self.presets:
            if self.active_category != "all" and p.category != self.active_category:
                continue
            result[p.id] = p.label
        return result

    def _select_preset(self, preset_id: str) -> None:
        self.selected_preset_id = preset_id
        preset = self.preset_by_id.get(preset_id)
        if preset and preset.id != "custom":
            self.int_digits = preset.default_int_digits
            self.dec_digits = preset.default_dec_digits
            self.analog_count = preset.default_analog_count
            self.unit = preset.default_unit
            self.flow_int_digits = preset.default_flow_int_digits
            self.flow_dec_digits = preset.default_flow_dec_digits

            self._suppress_control_change = True
            try:
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
            finally:
                self._suppress_control_change = False

        if self._preset_select and self._preset_select.value != preset_id:
            self._preset_select.value = preset_id

        self._update_ui_state()
        if self.on_preset_selected and preset and preset.id != "custom":
            self.on_preset_selected(preset)

    def _on_category_changed(self, category: str) -> None:
        self.active_category = category
        if self._preset_select:
            options = self._get_filtered_preset_options()
            self._preset_select.options = options
            # If current selection is not in filtered options, select first available
            if self.selected_preset_id not in options and options:
                first_key = next(iter(options))
                self._select_preset(first_key)
            else:
                self._preset_select.update()

    def _on_control_change(self) -> None:
        if getattr(self, "_suppress_control_change", False):
            return
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
        if (
            self.on_preset_selected
            and self.selected_preset
            and self.selected_preset.id != "custom"
        ):
            self.on_preset_selected(self.selected_preset)

    def _update_ui_state(self) -> None:
        preset = self.selected_preset
        is_custom = preset is None or preset.id == "custom"

        # Update Inspector Card
        if preset:
            if self._model_title:
                self._model_title.set_text(preset.label)
            if self._model_desc:
                self._model_desc.set_text(preset.description)
            if self._model_icon:
                self._model_icon.name = preset.icon
            if self._model_badge:
                tech_text = preset.meter_technology.replace("_", " ").title()
                self._model_badge.set_text(tech_text)

        # Show/hide customization controls
        if self._controls_container:
            self._controls_container.set_visibility(not is_custom)

        # Dynamic sub-section visibility based on preset capabilities
        if preset and not is_custom:
            if self._dec_row:
                has_dec = (
                    preset.cnn.analog_category is None
                    and preset.id != "generic_mechanical_drums"
                )
                self._dec_row.set_visibility(has_dec)
            if self._analog_row:
                self._analog_row.set_visibility(preset.cnn.analog_category is not None)
            if self._flow_container:
                self._flow_container.set_visibility(preset.has_secondary_group)

        # Update CNN recommendations
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
                ui.label("Select Your Meter Type & Hardware Model").classes(
                    theme.HEADING_SECTION
                )

            # Category Filter Chips
            category_options = {
                "all": "All Models",
                "smart": "Smart",
                "mechanical": "Mechanical",
                "generic": "Generic & Custom",
            }
            with ui.row().classes("w-full items-center gap-2 mb-2 flex-wrap"):
                ui.label("Filter:").classes(theme.TEXT_MONO_MUTED)
                self._category_toggle = (
                    ui.toggle(
                        category_options,
                        value=self.active_category,
                        on_change=lambda e: self._on_category_changed(e.value),
                    )
                    .props("dense no-caps toggle-color=indigo-600")
                    .classes("text-xs")
                )

            # Searchable Dropdown Selection
            with (
                ui.card().classes(f"{theme.CARD_DEFAULT} mb-3"),
                ui.row().classes("w-full items-center gap-3"),
            ):
                ui.icon("search", size="sm").classes("text-cyan-400")
                self._preset_select = (
                    ui.select(
                        options=self._get_filtered_preset_options(),
                        value=self.selected_preset_id,
                        label="Meter Model / Brand Preset",
                        with_input=True,
                        on_change=lambda e: self._select_preset(e.value),
                    )
                    .props("outlined dense options-dense")
                    .classes("w-full flex-grow text-sm")
                )
                ui.button(
                    icon="refresh",
                    on_click=self._handle_refresh_click,
                ).props(
                    "flat dense round color=grey-4"
                ).tooltip("Reload meter templates from disk")

            # Selected Model Overview Inspector Card
            self._model_info_card = ui.card().classes(f"{theme.CARD_DEFAULT} mb-3")
            with self._model_info_card:
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.row().classes("items-center gap-2"):
                        self._model_icon = ui.icon("water_drop", size="md").classes(
                            "text-indigo-400"
                        )
                        self._model_title = ui.label("").classes(
                            "font-bold text-base text-gray-100"
                        )
                    self._model_badge = ui.badge("Preset", color="indigo").classes(
                        "text-xs px-2.5 py-0.5"
                    )

                self._model_desc = ui.label("").classes(
                    "text-xs text-gray-300 leading-relaxed mt-1"
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

            # Initialize initial preset state (preserves 'custom' default unless selected)
            self._select_preset(self.selected_preset_id)

            super().add_navigator(stepper, first_step, last_step)


__all__ = [
    "DEFAULT_BUILTIN_PRESETS",
    "HELP_TEXT",
    "PRESETS",
    "PRESET_BY_ID",
    "MeterTypePreset",
    "MeterTypeStep",
    "load_meter_presets",
    "reload_presets",
    "select_best_model",
]
