import time
from collections.abc import Callable

from nicegui import ui

from configuration import CNNParams
from processor.digitizer import DigitizerProcessor

from .step_base import BaseStep
from .step_draw_rois_base import DrawRoisBaseStep

HELP_TEXT = (
    "- **Digital Digits**: Add bounding boxes tightly around each "
    "drum or LCD digit (`digit1`, `digit2`, ...).\n"
    "- **Alignment**: Drag boxes on canvas, or use toolbar buttons "
    "(Align Left, Top, Center, Resize All).\n"
    "- **CNN Model**: Choose a `.tflite` model and type (`auto`, "
    "`digital`, `digital100`).\n"
    "- **Test**: Click Test to run inference on cropped ROIs."
)


class DrawDigitalRoisStep(DrawRoisBaseStep):
    def __init__(
        self,
        name: str,
        name_template: str,
        set_image_callback: Callable[[str], None],
        set_rois_to_svg_func: Callable[[str], None],
        show_temp_draw_in_svg_func: Callable[[str], None],
        digital_models_dir: str = "",
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            name_template,
            set_image_callback=set_image_callback,
            draw_roi_func=self._draw_roi_func,
            set_rois_to_svg_func=set_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            spinner=spinner,
        )
        self.digital_models_dir = digital_models_dir
        self.cnn_file: ui.select | None = None
        self.cnn_type: ui.select | None = None

    def load_from_config(self, digital_readout: CNNParams) -> None:
        if (
            hasattr(self, "cnn_type")
            and self.cnn_type is not None
            and digital_readout.model in ["auto", "digital", "digital100"]
        ):
            self.cnn_type.value = digital_readout.model
        if (
            hasattr(self, "cnn_file")
            and self.cnn_file is not None
            and isinstance(self.cnn_file.options, dict)
        ):
            for key, val in self.cnn_file.options.items():
                if (
                    val in digital_readout.model_file
                    or key in digital_readout.model_file
                    or key == digital_readout.model_file
                ):
                    self.cnn_file.value = key
                    break
        self.load_rois(digital_readout.cut_images)

    def _draw_roi_func(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: str,
        text: str,
    ) -> str:
        style = f"stroke-width:3;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style2 = f"stroke-width:1;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style3 = f"font-size:10;fill:{color};font-weight:bold;"
        return (
            f'<text x="{x}" y="{y-7}" text-anchor="left" style="{style3}">{text}</text>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" />'
            f'<rect x="{x+w*0.2}" y="{y+h*0.2}" width="{w-w*0.4}" height="{h-h*0.4}" '
            f'style="{style2}" />'
            f'<line x1="{x+w*0.2}" y1="{y+h/2}" x2="{x+w-w*0.2}" y2="{y+h/2}"'
            f' style="{style2}" />'
        )

    def _show_digits(self) -> None:
        if (
            self.cnn_file is None
            or not self.cnn_file.value
            or self.test_result_container is None
        ):
            return
        start_time = time.time()
        digital_images = self._cut_images()
        digitizerProcessor = (
            DigitizerProcessor()
            .init_digital_model(self.cnn_file.value, "auto")
            .execute_digital_cnn(digital_images)
            .evaluate_cnn_results()
        )
        results = digitizerProcessor.cnn_digital_results

        self.test_result_container.clear()
        with (
            self.test_result_container,
            ui.row().classes("w-full gap-3 flex-wrap items-center mt-2"),
        ):
            for item in results:
                base64img = self._get_base64_image_by_name(item.name, digital_images)
                c = item.confidence
                c_color = (
                    "text-emerald-400"
                    if c >= 90
                    else ("text-amber-400" if c >= 70 else "text-red-400")
                )
                with ui.element("div").classes(
                    "p-2.5 rounded-lg bg-slate-900/80 border "
                    "border-white/10 flex flex-col items-center "
                    "gap-1 min-w-[70px]"
                ):
                    ui.label(f"{item.name}").classes(
                        "text-[11px] text-gray-400 uppercase "
                        "tracking-wider font-semibold"
                    )
                    ui.image(f"data:image/jpeg;base64,{base64img}").props(
                        "fit=contain no-spinner"
                    ).classes("w-14 h-24 rounded bg-slate-950 p-0.5")
                    ui.label(f"{self._convert_value(item.value)}").classes(
                        "font-['Outfit'] font-bold text-cyan-400 text-sm"
                    )
                    ui.label(f"{c:.0f}%").classes(
                        f"text-[10px] font-semibold {c_color} font-mono"
                    ).tooltip(f"Confidence: {c:.1f}%")
        self.time.text = f"⏱ {round(time.time() - start_time, 2)}s"

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def _benchmark_models(self) -> None:
        def _apply(modelfile: str):
            if hasattr(self, "cnn_file") and self.cnn_file is not None:
                self.cnn_file.value = modelfile
            self._show_digits()

        cnn_type_val = (
            self.cnn_type.value
            if hasattr(self, "cnn_type") and self.cnn_type is not None
            else "auto"
        )
        await self.open_benchmark_dialog(
            models_dir=self.digital_models_dir,
            model_type="digital",
            cnn_type_val=cnn_type_val,
            on_apply_callback=_apply,
        )

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            # Alignment & Action Bar
            with (
                ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl p-3 my-2"
                ),
                ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"),
            ):
                with ui.row().classes("items-center gap-1"):
                    ui.label("Align:").classes(
                        "text-xs font-semibold text-slate-400 mr-1"
                    )
                    ui.button(
                        icon="format_align_left",
                        on_click=self._align_left,
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Align Left"
                    )
                    ui.button(
                        icon="vertical_align_top", on_click=self._align_top
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Align Top"
                    )
                    ui.button(
                        icon="vertical_align_bottom",
                        on_click=self._align_bottom,
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Align Bottom"
                    )
                    ui.button(
                        icon="format_align_right",
                        on_click=self._align_right,
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Align Right"
                    )
                    ui.button(
                        icon="vertical_align_center",
                        on_click=self._align_center,
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Align Center"
                    )
                    ui.button(
                        icon="horizontal_distribute",
                        on_click=self._distribute_horizontally,
                    ).props("flat dense").bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 1
                    ).tooltip(
                        "Distribute Horizontally"
                    )
                    ui.button(icon="aspect_ratio", on_click=self._resize_all).props(
                        "flat dense"
                    ).bind_enabled_from(
                        self, "rois", lambda rois: len(rois) > 0
                    ).tooltip(
                        "Resize All to First ROI Size"
                    )

                with ui.row().classes("items-center gap-2"):
                    self.select_all = ui.checkbox(
                        "Show All",
                        value=(
                            bool(self.rois and all(r.enabled for r in self.rois))
                            if self.rois
                            else True
                        ),
                        on_change=self._select_all_rois,
                    ).tooltip("Toggle visibility of all bounding boxes on canvas")
                    self._sync_select_all_checkbox()
                    ui.button(
                        "Add Digit ROI", icon="add", on_click=self._add_roi
                    ).props("dense unelevated").classes(
                        "bg-indigo-600 hover:bg-indigo-500 text-white text-xs "
                        "px-2 py-1 font-medium"
                    ).tooltip(
                        "Add new digital digit bounding box"
                    )

            # ROI List Container
            self.container = ui.column().classes("w-full gap-2 my-2")

            # Inference & Testing Card
            with ui.card().classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                "p-4 my-2 gap-3 shadow-md"
            ):
                with ui.row().classes(
                    "w-full items-center gap-2 text-slate-300 font-semibold"
                ):
                    ui.icon("psychology", size="sm").classes("text-indigo-400")
                    ui.label("Digit Neural Network Model")

                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    self.cnn_file = (
                        ui.select(
                            options=self._get_cnn_models(self.digital_models_dir),
                            label="CNN Model File",
                        )
                        .classes("flex-grow min-w-[200px]")
                        .tooltip(
                            "Select TensorFlow Lite neural network model file "
                            "for digital digits"
                        )
                    )
                    self.cnn_type = (
                        ui.select(
                            options=["auto", "digital", "digital100"],
                            value="auto",
                            label="CNN Architecture",
                        )
                        .classes("w-40")
                        .tooltip(
                            "CNN architecture: auto (detect from output shape), "
                            "digital (discrete classes 0-9), or digital100 "
                            "(continuous 0.0-9.9)"
                        )
                    )

                with (
                    ui.row().classes(
                        "w-full items-center justify-between pt-2 border-t border-white/10"
                    ),
                    ui.row().classes("items-center gap-2"),
                ):
                    ui.button(
                        "Run Inference Test",
                        icon="play_arrow",
                        on_click=self._show_digits,
                    ).props("unelevated").classes(
                        "bg-gradient-to-r from-emerald-600 to-teal-600 "
                        "hover:from-emerald-500 hover:to-teal-500 text-white "
                        "font-medium"
                    ).tooltip(
                        "Digitize test result"
                    ).bind_enabled_from(
                        self.cnn_file,
                        "value",
                        lambda x: x is not None and len(x) > 0,
                    )
                    ui.button(
                        "Benchmark Models",
                        icon="analytics",
                        on_click=self._benchmark_models,
                    ).props("outline").classes(
                        "text-indigo-300 border-indigo-500/40 "
                        "hover:bg-indigo-500/10 font-medium"
                    ).tooltip(
                        "Benchmark and compare all models side-by-side"
                    ).bind_enabled_from(
                        self,
                        "rois",
                        lambda rois: len(rois) > 0,
                    )
                    self.time = ui.label().classes("text-xs font-mono text-slate-400")

                self.test_result_container = ui.row().classes("w-full")

            super().add_navigator(stepper, first_step, last_step)
