import time
from typing import Callable

from nicegui import ui

from .step_draw_rois_base import DrawRoisBaseStep
from processor.digitizer import DigitizerProcessor


class DrawAnalogRoisStep(DrawRoisBaseStep):
    def __init__(
        self,
        name: str,
        name_template: str,
        get_image_func: Callable[[], str],
        set_image_func: Callable[[str], None],
        set_rois_to_svg_func: Callable[[str], None],
        show_temp_draw_in_svg_func: Callable[[str], None],
        analog_models_dir: str = "",
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            name_template,
            get_image_func=get_image_func,
            set_image_func=set_image_func,
            draw_roi_func=self.draw_roi_func,
            set_rois_to_svg_func=set_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            spinner=spinner,
        )
        self.analog_models_dir = analog_models_dir

    def draw_roi_func(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: str,
        text: str,
    ):
        style = f"stroke-width:3;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style2 = f"stroke-width:1;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style3 = f"font-size:10;fill:{color};"
        return (
            f'<text x="{x}" y="{y-7}" text-anchor="left" style="{style3}">{text}</text>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" />'
            f'<ellipse cx="{x+w//2}" cy="{y+h//2}" rx="{w//2}" ry="{h//2}" '
            f'style="{style2}" />'
            f'<line x1="{x+w/2}" y1="{y}" x2="{x+w/2}" y2="{y+h}" style="{style2}" />'
            f'<line x1="{x}" y1="{y+h/2}" x2="{x+w}" y2="{y+h/2}" style="{style2}" />'
        )

    def show_analogs(self):
        start_time = time.time()
        analog_images = self.cut_images()
        digitizerProcessor = (
            DigitizerProcessor()
            .init_analog_model(self.cnn_file.value, "auto")  # type: ignore
            .execute_analog_ccn(analog_images)
            .evaluate_ccn_results()
        )
        results = digitizerProcessor.cnn_analog_results

        self.test_result_container.clear()
        text_size = "text-xs"
        with self.test_result_container:
            with ui.grid(columns=len(analog_images)):
                for item in results:
                    base64img = self.get_base64_image_by_name(item.name, analog_images)
                    with ui.card():
                        ui.label(f"{item.name}").classes(text_size)
                        ui.image(f"data:image/jpeg;base64,{base64img}")
                        with ui.card_section():
                            ui.label(f"{self.convert_value(item.value)}").classes(
                                text_size
                            )
        self.time.text = f"Time: {round(time.time() - start_time, 2)}s"

    def select_all_rois(self):
        state = self.select_all.value
        for roi in self.rois:
            roi.enabled = state

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            with ui.row():
                ui.button(
                    icon="sym_s_align_horizontal_left", on_click=self.align_left
                ).tooltip("Align left")
                ui.button(
                    icon="sym_s_align_vertical_top", on_click=self.align_top
                ).tooltip("Align top")
                ui.button(
                    icon="sym_s_align_vertical_bottom", on_click=self.align_bottom
                ).tooltip("Align bottom")
                ui.button(
                    icon="sym_s_align_horizontal_right", on_click=self.align_right
                ).tooltip("Align right")
                ui.button(
                    icon="sym_s_align_vertical_center", on_click=self.align_center
                ).tooltip("Align center")
                ui.button(icon="sym_s_resize", on_click=self.resize_all).tooltip(
                    "Resize all"
                )
            with ui.grid(columns="2fr 2fr 2fr 2fr 2fr 2fr").classes("w-full gap-2"):
                self.select_all = ui.checkbox(
                    "Show", on_change=self.select_all_rois
                ).tooltip("Show all")
                ui.label("Name")
                ui.label("X-position")
                ui.label("Y-position")
                ui.label("Width")
                ui.label("Height")
            self.container = ui.row().classes("w-full")
            with ui.row():
                ui.button(icon="add", on_click=self.add_roi).tooltip(
                    "Add analog region of interest"
                )
                ui.button(icon="remove", on_click=self.remove_roi).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip("Remove last analog region of interest")
            with ui.row().classes("w-full"):
                self.cnn_file = ui.select(
                    options=self.get_cnn_models(self.analog_models_dir),
                    label="CNN model",
                ).classes("w-3/5")
                self.cnn_type = ui.select(
                    options=["auto", "analog", "analog100"],
                    value="auto",
                    label="CNN type",
                ).classes("w-1/5")
            with ui.row():
                ui.button("Test", icon="refresh", on_click=self.show_analogs).tooltip(
                    "Digitize test result"
                ).bind_enabled_from(
                    self.cnn_file, "value", lambda x: x is not None and len(x) > 0
                )
                self.time = ui.label()
            self.test_result_container = ui.row().classes("w-full")

            super().add_navigator(stepper, first_step, last_step)
