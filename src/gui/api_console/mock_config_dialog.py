"""Interactive Dedicated Mock Camera Configuration Editor Dialog."""

from __future__ import annotations

import base64
import configparser
import io
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import PIL.Image
from nicegui import ui

from api.routes_mock_camera import render_mock_camera_frame
from configuration import Config
from data_classes import MeterConfig
from gui.theme import (
    DIALOG_CARD,
    DIALOG_HEADER_ROW,
    ROW_ACTIONS,
    ROW_HEADER,
)
from processor.image import ImageProcessor
from services.simulator.meter_generator import MeterImageGenerator

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)

DIGITAL_MODELS: dict[str, tuple[str, str]] = {
    "Class 11 (Standard Discrete 0-9 & Blank)": (
        "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite",
        "digital",
    ),
    "Class 100 (Fine 0.0-9.9 Discrete)": (
        "config/neuralnets/digital/class100/dig-class100_20241221_091357_s2.tflite",
        "class100",
    ),
    "Continuous (Direct Angle Regression)": (
        "config/neuralnets/digital/continuous/dig-cont_1600_s2.tflite",
        "continuous",
    ),
}

ANALOG_MODELS: dict[str, tuple[str, str]] = {
    "Continuous (Standard Sub-Dial Needles)": (
        "config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite",
        "analog",
    ),
    "Class 100 (Fine 0-99 Angular Classes)": (
        "config/neuralnets/analog/class100/ana-class100_20241221_120417_s2.tflite",
        "class100",
    ),
}


class MockConfigDialog:
    """Dialog allowing users to inspect, tune, and edit dedicated mock camera engine configurations."""

    def __init__(
        self,
        current_config: Config,
        width: int,
        height: int,
        mock_url: str,
        callbacks: Callbacks | None = None,
        on_apply: Callable[[Config], None] | None = None,
        is_custom: bool = False,
    ) -> None:
        self.config: Config = current_config.model_copy(deep=True)
        self.width = width
        self.height = height
        self.mock_url = mock_url
        self.callbacks = callbacks
        self.on_apply = on_apply
        self.is_custom = is_custom

        self.dialog: ui.dialog | None = None
        self.raw_ini_editor: ui.textarea | None = None
        self.validation_banner: ui.element | None = None
        self.validation_label: ui.label | None = None
        self.status_badge: ui.badge | None = None

        # Structured Form Controls
        self.dig_model_select: ui.select | None = None
        self.ana_model_select: ui.select | None = None
        self.meter_name_input: ui.input | None = None
        self.meter_format_input: ui.input | None = None
        self.meter_unit_input: ui.input | None = None
        self.detect_neg_switch: ui.switch | None = None
        self.consistency_switch: ui.switch | None = None
        self.allow_neg_rates_switch: ui.switch | None = None
        self.proc_enabled_switch: ui.switch | None = None
        self.autocontrast_switch: ui.switch | None = None
        self.glare_switch: ui.switch | None = None
        self.glare_mode_select: ui.select | None = None
        self.sharpening_switch: ui.switch | None = None
        self.roi_preview_image: ui.image | None = None

    def _generate_roi_preview_data_uri(self) -> str:
        """Generate base64 JPEG data URI of the mock frame with ROIs overlaid."""
        try:
            jpeg_bytes, _ = render_mock_camera_frame(
                width=self.width,
                height=self.height,
            )
            pil_img = PIL.Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
            overlaid = (
                ImageProcessor()
                .set_image(pil_img)
                .draw_meter_rois(self.config)
                .get_image()
            )
            buf = io.BytesIO()
            overlaid.save(buf, format="JPEG", quality=85)
            b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64_str}"
        except Exception:
            logger.debug("Failed to generate ROI preview data URI", exc_info=True)
            return ""

    def open(self) -> None:
        """Construct and display the modal dialog."""
        with (
            ui.dialog() as self.dialog,
            ui.card()
            .classes(
                f"column no-wrap w-[94vw] max-w-5xl max-h-[90vh] {DIALOG_CARD} text-slate-100 overflow-hidden"
            )
            .style("max-width: 95vw; width: 1000px;"),
        ):
            # Dialog Header
            with ui.row().classes(f"{DIALOG_HEADER_ROW} shrink-0 gap-3"):
                with ui.row().classes("items-center gap-2.5 min-w-0 flex-1"):
                    ui.icon("tune", color="cyan", size="md").classes("shrink-0")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label("Dedicated Mock Meter Configuration").classes(
                            "text-base font-bold text-slate-100 truncate"
                        )
                        ui.label(
                            "Fine-tune neural networks, meter formulas, and image filters for mock camera testing"
                        ).classes("text-xs text-slate-400 truncate")

                with ui.row().classes(f"{ROW_ACTIONS} shrink-0"):
                    ui.badge(f"{self.width}x{self.height}", color="indigo").classes(
                        "text-xs font-mono"
                    )
                    status_text = (
                        "Custom Overrides" if self.is_custom else "Canvas Synced"
                    )
                    status_color = "amber" if self.is_custom else "emerald"
                    self.status_badge = ui.badge(
                        status_text, color=status_color
                    ).classes("text-xs")
                    ui.button(icon="close", on_click=self.dialog.close).props(
                        "flat round dense aria-label='Close dialog'"
                    )

            # Dialog Tab Bar
            with ui.tabs().classes(
                "w-full text-slate-300 border-b border-white/10"
            ) as tabs:
                tab_struct = ui.tab("Structured Settings", icon="tune")
                tab_ini = ui.tab("Raw INI Editor", icon="code")
                tab_rois = ui.tab("ROI Coordinates", icon="crop")

            # Tab Panels Container (Scrollable)
            with (
                ui.tab_panels(tabs, value=tab_struct)
                .classes("w-full bg-transparent flex-1 overflow-y-auto")
                .style("max-height: 72vh")
            ):
                # -------------------------------------------------------------
                # Panel 1: Structured Settings
                # -------------------------------------------------------------
                with ui.tab_panel(tab_struct).classes("gap-4 p-2 flex flex-col"):
                    # Section A: Neural Network Inference Models
                    with ui.card().classes(
                        "w-full p-4 bg-slate-950/70 border border-white/5 rounded-xl gap-3"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("psychology", color="cyan", size="sm")
                            ui.label("Neural Network Inference Models").classes(
                                "text-xs font-bold text-slate-200 uppercase tracking-wider"
                            )

                        with ui.grid(columns=2).classes("w-full gap-4"):
                            # Digital Model
                            current_dig = self._find_model_key(
                                DIGITAL_MODELS, self.config.digital_readout.model_file
                            )
                            self.dig_model_select = (
                                ui.select(
                                    options=list(DIGITAL_MODELS.keys()),
                                    value=current_dig,
                                    label="Digital Digits Model Architecture",
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense options-dense")
                                .classes("text-xs")
                            )

                            # Analog Model
                            current_ana = self._find_model_key(
                                ANALOG_MODELS, self.config.analog_readout.model_file
                            )
                            self.ana_model_select = (
                                ui.select(
                                    options=list(ANALOG_MODELS.keys()),
                                    value=current_ana,
                                    label="Analog Needles Model Architecture",
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense options-dense")
                                .classes("text-xs")
                            )

                        self.detect_neg_switch = (
                            ui.switch(
                                "Detect Negative Sign in Digital Readout",
                                value=self.config.digital_readout.detect_negative_sign,
                                on_change=lambda _: self._on_structured_change(),
                            )
                            .props("dense size=sm color=cyan")
                            .classes("text-xs font-semibold text-slate-300")
                        )

                    # Section B: Meter Formula & Reading Configuration
                    with ui.card().classes(
                        "w-full p-4 bg-slate-950/70 border border-white/5 rounded-xl gap-3"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("calculate", color="amber", size="sm")
                            ui.label("Meter Formula & Readout Assembly").classes(
                                "text-xs font-bold text-slate-200 uppercase tracking-wider"
                            )

                        meter_cfg = (
                            self.config.meter_configs[0]
                            if self.config.meter_configs
                            else MeterConfig(
                                name="total",
                                format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}",
                                unit="m³",
                            )
                        )

                        with ui.grid(columns=3).classes("w-full gap-3"):
                            self.meter_name_input = (
                                ui.input(
                                    label="Meter Name",
                                    value=meter_cfg.name,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense")
                                .classes("text-xs font-mono")
                            )

                            self.meter_format_input = (
                                ui.input(
                                    label="Readout Format Template",
                                    value=meter_cfg.format,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense")
                                .classes("text-xs font-mono col-span-2")
                            )

                        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                            self.meter_unit_input = (
                                ui.input(
                                    label="Unit",
                                    value=meter_cfg.unit or "m³",
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense")
                                .classes("text-xs font-mono w-28")
                            )

                            self.consistency_switch = (
                                ui.switch(
                                    "Consistency Check Enabled",
                                    value=meter_cfg.consistency_enabled,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=emerald")
                                .classes("text-xs font-semibold text-slate-300")
                            )

                            self.allow_neg_rates_switch = (
                                ui.switch(
                                    "Allow Negative Flow Rates",
                                    value=meter_cfg.allow_negative_rates,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=amber")
                                .classes("text-xs font-semibold text-slate-300")
                            )

                    # Section C: Image Preprocessing Pipeline
                    with ui.card().classes(
                        "w-full p-4 bg-slate-950/70 border border-white/5 rounded-xl gap-3"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("filter", color="purple", size="sm")
                                ui.label(
                                    "Image Preprocessing Filters & Enhancement"
                                ).classes(
                                    "text-xs font-bold text-slate-200 uppercase tracking-wider"
                                )

                            self.proc_enabled_switch = (
                                ui.switch(
                                    "Pipeline Active",
                                    value=self.config.image_processing.enabled,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=purple")
                                .classes("text-xs font-semibold text-purple-300")
                            )

                        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                            self.autocontrast_switch = (
                                ui.switch(
                                    "AutoContrast",
                                    value=self.config.image_processing.autocontrast.enabled,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=cyan")
                                .classes("text-xs text-slate-300")
                            )

                            self.glare_switch = (
                                ui.switch(
                                    "Glare Suppression",
                                    value=self.config.image_processing.glare_suppression.enabled,
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=indigo")
                                .classes("text-xs text-slate-300")
                            )

                            self.glare_mode_select = (
                                ui.select(
                                    options={
                                        "clahe": "CLAHE Contrast Limiting",
                                        "inpaint": "Fast Marching Inpainting",
                                        "illumination_normalize": "Illumination Normalization",
                                        "combined": "Combined Multi-Stage",
                                    },
                                    value=self.config.image_processing.glare_suppression.mode,
                                    label="Glare Mode",
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("outlined dense options-dense")
                                .classes("text-xs min-w-[190px]")
                            )

                            self.sharpening_switch = (
                                ui.switch(
                                    "Unsharp Mask Sharpening",
                                    value=(
                                        self.config.image_processing.sharpness_mode
                                        == "unsharp_mask"
                                    ),
                                    on_change=lambda _: self._on_structured_change(),
                                )
                                .props("dense size=sm color=emerald")
                                .classes("text-xs text-slate-300")
                            )

                # -------------------------------------------------------------
                # Panel 2: Raw INI Editor
                # -------------------------------------------------------------
                with ui.tab_panel(tab_ini).classes("gap-3 p-2 flex flex-col"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Direct INI Configuration Payload").classes(
                            "text-xs font-semibold text-slate-400"
                        )
                        ui.button(
                            "Validate Syntax",
                            icon="check_circle",
                            on_click=self._validate_ini_editor,
                        ).props("flat dense size=sm color=cyan").classes("text-xs")

                    self.validation_banner = ui.row().classes(
                        "w-full p-2.5 rounded-lg border hidden items-center gap-2 text-xs"
                    )
                    with self.validation_banner:
                        self.validation_label = ui.label("").classes("font-mono")

                    self.raw_ini_editor = (
                        ui.textarea(value=self.config.to_ini_string())
                        .props("outlined autogrow rows=14")
                        .classes(
                            "w-full font-mono text-xs bg-slate-950/80 text-emerald-300 rounded-xl border border-white/5"
                        )
                    )

                # -------------------------------------------------------------
                # Panel 3: ROI Layout Table & Visual Overlay Preview
                # -------------------------------------------------------------
                with ui.tab_panel(tab_rois).classes("gap-4 p-2 flex flex-col"):
                    # Visual ROI Overlay Card
                    with ui.card().classes(
                        "w-full p-3 bg-slate-950/80 border border-white/10 rounded-xl flex flex-col gap-2"
                    ):
                        with ui.row().classes("w-full justify-between items-center"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("visibility", color="cyan", size="xs")
                                ui.label("Visual ROI Bounding Box Overlay").classes(
                                    "text-xs font-bold text-slate-200 uppercase tracking-wide"
                                )
                            with ui.row().classes("items-center gap-2"):
                                ui.badge("🟦 Digital ROIs", color="cyan").props("dense")
                                ui.badge("🟧 Analog ROIs", color="amber").props("dense")

                        with ui.element("div").classes(
                            "w-full flex items-center justify-center bg-slate-950 rounded-lg p-2 overflow-hidden border border-white/10"
                        ):
                            self.roi_preview_image = (
                                ui.image(self._generate_roi_preview_data_uri())
                                .props('fit="contain"')
                                .classes(
                                    "w-full max-h-[460px] object-contain rounded-lg shadow"
                                )
                                .style("max-width: 100%; height: auto;")
                            )

                    with ui.row().classes("items-center justify-between"):
                        ui.label(
                            f"Region of Interest (ROI) Coordinates for {self.width}x{self.height} Canvas"
                        ).classes("text-xs font-semibold text-slate-300")

                    with ui.grid(columns=2).classes("w-full gap-4"):
                        # Digital ROIs
                        with ui.card().classes(
                            "p-3 bg-slate-950/70 border border-cyan-500/20 rounded-xl gap-2"
                        ):
                            ui.label("5 Digital Counter Drums").classes(
                                "text-xs font-bold text-cyan-300 uppercase"
                            )
                            for cut in self.config.digital_readout.cut_images:
                                with ui.row().classes(
                                    "w-full justify-between items-center py-1 border-b border-white/5 text-xs font-mono"
                                ):
                                    ui.badge(cut.name, color="cyan").props("dense")
                                    ui.label(f"x={cut.x}, y={cut.y}").classes(
                                        "text-slate-300"
                                    )
                                    ui.label(f"{cut.w}x{cut.h} px").classes(
                                        "text-slate-400"
                                    )

                        # Analog ROIs
                        with ui.card().classes(
                            "p-3 bg-slate-950/70 border border-amber-500/20 rounded-xl gap-2"
                        ):
                            ui.label("4 Analog Pointer Dials").classes(
                                "text-xs font-bold text-amber-300 uppercase"
                            )
                            for cut in self.config.analog_readout.cut_images:
                                with ui.row().classes(
                                    "w-full justify-between items-center py-1 border-b border-white/5 text-xs font-mono"
                                ):
                                    ui.badge(cut.name, color="amber").props("dense")
                                    ui.label(f"x={cut.x}, y={cut.y}").classes(
                                        "text-slate-300"
                                    )
                                    ui.label(f"{cut.w}x{cut.h} px").classes(
                                        "text-slate-400"
                                    )

            # Dialog Footer Actions
            with ui.row().classes(
                f"{ROW_HEADER} pt-3 border-t border-white/10 flex-wrap gap-2 shrink-0"
            ):
                with ui.row().classes(ROW_ACTIONS):
                    ui.button(
                        "Reset to Canvas Sync",
                        icon="restart_alt",
                        on_click=self._reset_to_canvas_sync,
                    ).props("outline dense size=sm color=purple").classes(
                        "text-xs font-semibold"
                    )

                    ui.button(
                        "Download INI",
                        icon="download",
                        on_click=self._download_ini,
                    ).props("flat dense size=sm color=grey-4").classes(
                        "text-xs font-semibold"
                    )

                with ui.row().classes(ROW_ACTIONS):
                    ui.button(
                        "Cancel",
                        icon="close",
                        on_click=self.dialog.close,
                    ).props("flat dense size=sm color=grey-4").classes(
                        "text-xs font-semibold text-slate-300"
                    )

                    ui.button(
                        "Apply to Studio",
                        icon="check",
                        on_click=self._apply_to_studio,
                    ).props("unelevated dense size=sm color=cyan-8").classes(
                        "text-xs font-semibold text-white px-3"
                    )

        self.dialog.open()

    # -------------------------------------------------------------------------
    # Internal Handlers
    # -------------------------------------------------------------------------

    def _find_model_key(
        self, model_dict: dict[str, tuple[str, str]], file_path: str | None
    ) -> str:
        if not file_path:
            return next(iter(model_dict.keys()))
        file_path_str = str(file_path).lower()
        for k, (path, _) in model_dict.items():
            if path.lower() in file_path_str or file_path_str in path.lower():
                return k
        return next(iter(model_dict.keys()))

    def _sync_structured_to_config(self) -> None:
        """Update internal Config model from structured controls."""
        if (
            self.dig_model_select
            and self.dig_model_select.value
            and self.dig_model_select.value in DIGITAL_MODELS
        ):
            path, model = DIGITAL_MODELS[self.dig_model_select.value]
            self.config.digital_readout.model_file = path
            self.config.digital_readout.model = model

        if (
            self.ana_model_select
            and self.ana_model_select.value
            and self.ana_model_select.value in ANALOG_MODELS
        ):
            path, model = ANALOG_MODELS[self.ana_model_select.value]
            self.config.analog_readout.model_file = path
            self.config.analog_readout.model = model

        if self.detect_neg_switch:
            self.config.digital_readout.detect_negative_sign = (
                self.detect_neg_switch.value
            )

        if self.meter_name_input and self.meter_format_input:
            m_name = (self.meter_name_input.value or "total").strip()
            m_fmt = (
                self.meter_format_input.value
                or "{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}"
            ).strip()
            m_unit = (
                self.meter_unit_input.value if self.meter_unit_input else "m³"
            ) or "m³"
            cons = self.consistency_switch.value if self.consistency_switch else False
            allow_neg = (
                self.allow_neg_rates_switch.value
                if self.allow_neg_rates_switch
                else True
            )

            self.config.meter_configs = [
                MeterConfig(
                    name=m_name,
                    format=m_fmt,
                    unit=m_unit,
                    consistency_enabled=cons,
                    allow_negative_rates=allow_neg,
                    use_previous_value=False,
                )
            ]

        if self.proc_enabled_switch:
            self.config.image_processing.enabled = self.proc_enabled_switch.value
        if self.autocontrast_switch:
            self.config.image_processing.autocontrast.enabled = (
                self.autocontrast_switch.value
            )
        if self.glare_switch and self.glare_mode_select:
            self.config.image_processing.glare_suppression.enabled = (
                self.glare_switch.value
            )
            self.config.image_processing.glare_suppression.mode = (
                self.glare_mode_select.value or "inpaint"
            )
        if self.sharpening_switch:
            self.config.image_processing.sharpness_mode = (
                "unsharp_mask" if self.sharpening_switch.value else "off"
            )

        # Update raw INI editor text if initialized
        if self.raw_ini_editor:
            self.raw_ini_editor.value = self.config.to_ini_string()

    def _on_structured_change(self) -> None:
        self.is_custom = True
        self._sync_structured_to_config()
        if self.status_badge:
            self.status_badge.text = "Custom Overrides"
            self.status_badge.props("color=amber")

    def _validate_ini_editor(self) -> bool:
        """Validate raw INI editor syntax and update internal config."""
        if not self.raw_ini_editor or not self.raw_ini_editor.value:
            return False

        try:
            parser = configparser.ConfigParser(interpolation=None)
            parser.read_string(self.raw_ini_editor.value)
            parsed_cfg = Config().load_config(parser)
            self.config = parsed_cfg
            self.is_custom = True

            if self.validation_banner and self.validation_label:
                self.validation_banner.classes(
                    remove="hidden bg-rose-950/80 border-rose-500/40 text-rose-300",
                    add="bg-emerald-950/80 border-emerald-500/40 text-emerald-300",
                )
                self.validation_label.text = "✓ Configuration syntax is valid!"
            if self.status_badge:
                self.status_badge.text = "Custom Overrides"
                self.status_badge.props("color=amber")
            return True
        except Exception as ex:
            if self.validation_banner and self.validation_label:
                self.validation_banner.classes(
                    remove="hidden bg-emerald-950/80 border-emerald-500/40 text-emerald-300",
                    add="bg-rose-950/80 border-rose-500/40 text-rose-300",
                )
                self.validation_label.text = f"Syntax Error: {ex}"
            return False

    def _reset_to_canvas_sync(self) -> None:
        """Regenerate clean dedicated mock configuration matching current canvas resolution."""
        base_cfg = self.callbacks.get_config() if self.callbacks else None
        self.config = MeterImageGenerator.create_mock_meter_config(
            width=self.width,
            height=self.height,
            base_config=base_cfg,
            url=self.mock_url,
        )
        self.is_custom = False

        if self.status_badge:
            self.status_badge.text = "Canvas Synced"
            self.status_badge.props("color=emerald")

        if self.raw_ini_editor:
            self.raw_ini_editor.value = self.config.to_ini_string()

        # Update structured form fields
        cur_dig = self._find_model_key(
            DIGITAL_MODELS, self.config.digital_readout.model_file
        )
        if self.dig_model_select:
            self.dig_model_select.value = cur_dig
        cur_ana = self._find_model_key(
            ANALOG_MODELS, self.config.analog_readout.model_file
        )
        if self.ana_model_select:
            self.ana_model_select.value = cur_ana
        if self.meter_format_input:
            self.meter_format_input.value = self.config.meter_configs[0].format
        if self.meter_name_input:
            self.meter_name_input.value = self.config.meter_configs[0].name
        if self.meter_unit_input:
            self.meter_unit_input.value = self.config.meter_configs[0].unit

        if self.roi_preview_image:
            self.roi_preview_image.set_source(self._generate_roi_preview_data_uri())

        ui.notify("Mock configuration reset to canvas auto-sync", type="info")

    def _download_ini(self) -> None:
        """Download mock configuration as INI file."""
        ini_content = self.config.to_ini_string()
        ui.download(ini_content.encode("utf-8"), filename="mock_config.ini")
        ui.notify("Downloading mock_config.ini", type="info")

    def _apply_to_studio(self) -> None:
        """Apply modified configuration to the active Mock Camera Studio session."""
        if self.raw_ini_editor and self.raw_ini_editor.value:
            self._validate_ini_editor()
        else:
            self._sync_structured_to_config()

        if self.on_apply:
            try:
                self.on_apply(self.config, self.is_custom)  # type: ignore[call-arg]
            except TypeError:
                self.on_apply(self.config)  # type: ignore[call-arg]

        ui.notify(
            "Dedicated mock configuration applied to studio session", type="positive"
        )
        if self.dialog:
            self.dialog.close()


__all__ = ["ANALOG_MODELS", "DIGITAL_MODELS", "MockConfigDialog"]
