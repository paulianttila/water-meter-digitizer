from dataclasses import dataclass
from typing import Callable
from pathlib import Path

from nicegui import events, ui

from data_classes import CutImage, ImagePosition
from .step_base import BaseStep
import utils.image
from processor.image import ImageProcessor


@dataclass
class Roi:
    enabled: bool = False
    name: str = ""
    color: str = "red"
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class DrawRoisBaseStep(BaseStep):
    def __init__(
        self,
        name: str,
        name_template: str,
        get_image_func: Callable[[], str],
        set_image_func: Callable[[str], None],
        draw_roi_func: Callable[[int, int, int, int, str, str], str],
        set_rois_to_svg_func: Callable[[str], None],
        show_temp_draw_in_svg_func: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            get_image_func=get_image_func,
            set_image_func=set_image_func,
            spinner=spinner,
        )
        self.name_template = name_template
        self.draw_roi_func = draw_roi_func
        self.set_rois_to_svg_func = set_rois_to_svg_func
        self.show_temp_draw_in_svg_func = show_temp_draw_in_svg_func
        self.container: ui.row
        self.test_result_container = None
        self.rois: list[Roi] = []
        self.mouse_x: int
        self.mouse_y: int
        self.draw_on = False
        self.colors = [
            "black",
            "red",
            "green",
            "blue",
            "yellow",
            "purple",
            "orange",
            "back",
            "white",
            "pink",
        ]

    def show_rois(self) -> None:
        if self.get_image_func is not None:
            self.image = self.get_image_func()
        content = "".join(
            self.draw_roi_func(roi.x, roi.y, roi.w, roi.h, roi.color, roi.name)
            for roi in self.rois
            if roi.enabled
        )
        if self.set_image_func is not None:
            self.set_image_func(self.image)
        self.set_rois_to_svg_func(content)

    def mouse_event(self, e: events.MouseEventArguments) -> None:
        if e.type == "mousedown":
            self.mouse_x = int(e.image_x)
            self.mouse_y = int(e.image_y)
            self.draw_on = True
        elif e.type == "mouseup":
            self.draw_on = False
            for roi in self.rois:
                if roi.enabled:
                    roi.x, roi.y, roi.w, roi.h = self.get_xywh(e)
            self.show_rois()
        elif e.type == "mousemove" and self.draw_on:
            x, y, w, h = self.get_xywh(e)
            rect = self.draw_roi_func(x, y, w, h, "red", "")
            self.show_temp_draw_in_svg_func(rect)

    def get_xywh(self, e: events.MouseEventArguments) -> tuple[int, int, int, int]:
        x, y = self.mouse_x, self.mouse_y
        w = int(e.image_x) - x
        h = int(e.image_y) - y
        if w < 0:
            x += w
            w = -w
        if h < 0:
            y += h
            h = -h
        return x, y, w, h

    def remove_roi(self) -> None:
        last = len(list(self.container)) - 1
        self.container.remove(last)
        self.rois.pop()

    def align_top(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = roi.y
                else:
                    roi.y = y

    def align_left(self) -> None:
        x = None
        for roi in self.rois:
            if roi.enabled:
                if x is None:
                    x = roi.x
                else:
                    roi.x = x

    def align_bottom(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = roi.y + roi.h
                else:
                    roi.y = y - roi.h

    def align_right(self) -> None:
        x = None
        for roi in self.rois:
            if roi.enabled:
                if x is None:
                    x = roi.x + roi.w
                else:
                    roi.x = x - roi.w

    def align_center(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = int(roi.y + roi.h / 2)
                else:
                    roi.y = int(y - roi.h / 2)

    def resize_all(self) -> None:
        search_first = True
        width = 0
        height = 0

        for roi in self.rois:
            if roi.enabled:
                if search_first:
                    # get width and height of the first selected roi
                    width = roi.w
                    height = roi.h
                    search_first = False
                else:
                    # set width and height of all other selected rois to the first
                    # selected roi
                    roi.w = width
                    roi.h = height

    def get_cnn_models(self, dir: str) -> dict:
        return {str(path): path.name for path in Path(dir).rglob("*.tflite")}

    def get_base64_image_by_name(
        self, name: str, digital_images: list[CutImage]
    ) -> str:
        return next(
            (
                utils.image.convert_image_base64str(img.image)
                for img in digital_images
                if name == img.name
            ),
            "",
        )

    def convert_value(self, value):
        return round(value, 2) if isinstance(value, float) else value

    def cut_images(self) -> list[CutImage]:
        imageProcessor = ImageProcessor().set_image_from_base64_str(
            self.get_image_func()
        )
        postions = [
            ImagePosition(roi.name, int(roi.x), int(roi.y), int(roi.w), int(roi.h))
            for roi in self.rois
        ]
        return (
            imageProcessor.start_image_cutting()
            .cut_images(postions)
            .stop_image_cutting()
            .save_cutted_images()
            .get_cutted_images()
        )

    def create_new_roi(self) -> Roi:
        i = len(list(self.container))
        return Roi(
            color=self.colors[i % 10],
            name=f"{self.name_template}{i}",
            enabled=True,
            x=10 * i,
            y=10 * i,
            w=50,
            h=50,
        )

    def unselect_all_rois(self) -> None:
        for roi in self.rois:
            roi.enabled = False

    def add_roi(self) -> None:
        self.unselect_all_rois()
        with self.container:
            with ui.grid(columns="1fr 2fr 2fr 2fr 2fr 2fr").classes("w-full gap-2"):
                roi = self.create_new_roi()
                ui.checkbox(on_change=self.show_rois).bind_value(roi, "enabled").props(
                    f"color={roi.color}"
                )
                ui.input().bind_value(roi, "name")
                ui.number(on_change=self.show_rois).bind_value(
                    roi, "x", forward=lambda x: int(x)
                )
                ui.number(on_change=self.show_rois).bind_value(
                    roi, "y", forward=lambda x: int(x)
                )
                ui.number(on_change=self.show_rois).bind_value(
                    roi, "w", forward=lambda x: int(x)
                )
                ui.number(on_change=self.show_rois).bind_value(
                    roi, "h", forward=lambda x: int(x)
                )
                self.rois.append(roi)
