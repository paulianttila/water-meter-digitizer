import time
from typing import Callable

from nicegui import ui

from configuration import CNNParams
from .step_draw_rois_base import DrawRoisBaseStep
from processor.digitizer import DigitizerProcessor

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
        self.cnn_file: ui.select
        self.cnn_type: ui.select

    def load_from_config(self, digital_readout: CNNParams) -> None:
        if hasattr(self, "cnn_type") and self.cnn_type is not None:
            if digital_readout.model in ["auto", "digital", "digital100"]:
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
        start_time = time.time()
        digital_images = self._cut_images()
        digitizerProcessor = (
            DigitizerProcessor()
            .init_digital_model(self.cnn_file.value, "auto")  # type: ignore
            .execute_digital_cnn(digital_images)
            .evaluate_cnn_results()
        )
        results = digitizerProcessor.cnn_digital_results

        self.test_result_container.clear()
        text_size = "text-xs"
        with self.test_result_container:
            with ui.grid(columns=len(digital_images)):
                for item in results:
                    base64img = self._get_base64_image_by_name(
                        item.name, digital_images
                    )
                    with ui.card():
                        ui.label(f"{item.name}").classes(text_size)
                        ui.image(f"data:image/jpeg;base64,{base64img}")
                        with ui.card_section():
                            ui.label(f"{self._convert_value(item.value)}").classes(
                                text_size
                            )
        self.time.text = f"Time: {round(time.time() - start_time, 2)}s"

    def _select_all_rois(self) -> None:
        state = self.select_all.value
        for roi in self.rois:
            roi.enabled = state

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)
            with ui.row():
                ui.button(
                    icon="sym_s_align_horizontal_left", on_click=self._align_left
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Align left"
                )
                ui.button(
                    icon="sym_s_align_vertical_top", on_click=self._align_top
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Align top"
                )
                ui.button(
                    icon="sym_s_align_vertical_bottom", on_click=self._align_bottom
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Align bottom"
                )
                ui.button(
                    icon="sym_s_align_horizontal_right", on_click=self._align_right
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Align right"
                )
                ui.button(
                    icon="sym_s_align_vertical_center", on_click=self._align_center
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Align center"
                )
                ui.button(
                    icon="sym_s_resize", on_click=self._resize_all
                ).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip(
                    "Resize all"
                )
            with ui.grid(columns="2fr 2fr 2fr 2fr 2fr 2fr").classes("w-full gap-2"):
                self.select_all = ui.checkbox(
                    "Show", on_change=self._select_all_rois
                ).tooltip("Show all")
                ui.label("Name")
                ui.label("X-position")
                ui.label("Y-position")
                ui.label("Width")
                ui.label("Height")
            self.container = ui.row().classes("w-full")
            with ui.row():
                ui.button(icon="add", on_click=self._add_roi).tooltip(
                    "Add digital region of interest"
                )
                ui.button(icon="remove", on_click=self._remove_roi).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip("Remove last digital region of interest")
            with ui.row().classes("w-full"):
                self.cnn_file = ui.select(
                    options=self._get_cnn_models(self.digital_models_dir),
                    label="CNN model",
                ).classes("w-3/5")
                self.cnn_type = ui.select(
                    options=["auto", "digital", "digital100"],
                    value="auto",
                    label="CNN type",
                ).classes("w-1/5")
            with ui.row():
                ui.button("Test", icon="refresh", on_click=self._show_digits).tooltip(
                    "Digitize test result"
                ).bind_enabled_from(
                    self.cnn_file, "value", lambda x: x is not None and len(x) > 0
                )
                self.time = ui.label()
            self.test_result_container = ui.row().classes("w-full")

            super().add_navigator(stepper, first_step, last_step)
