from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path

from nicegui import events, ui

from data_classes import CutImage, ImagePosition, RefImage
from .step_base import BaseStep
import utils.image
from processor.image import ImageProcessor

logger = logging.getLogger(__name__)


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
        set_image_callback: Callable[[str], None],
        draw_roi_func: Callable[[int, int, int, int, str, str], str],
        set_rois_to_svg_func: Callable[[str], None],
        show_temp_draw_in_svg_func: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.name_template = name_template
        self.draw_roi_func = draw_roi_func
        self.set_rois_to_svg_func = set_rois_to_svg_func
        self.show_temp_draw_in_svg_func = show_temp_draw_in_svg_func
        self.container = []
        self.test_result_container = None
        self.rois: list[Roi] = []
        self.mouse_x: int
        self.mouse_y: int
        self.draw_on = False
        self.colors = [
            "red",
            "blue",
            "green",
            "orange",
            "purple",
            "cyan",
            "teal",
            "pink",
            "indigo",
            "lime",
        ]
        self.autocontrast = False
        self.cutoff_low = 0
        self.cutoff_high = 0
        self.select_all: ui.checkbox | None = None
        self._updating_select_all: bool = False

    def _sync_select_all_checkbox(self) -> None:
        if hasattr(self, "select_all") and self.select_all is not None:
            all_enabled = bool(self.rois and all(roi.enabled for roi in self.rois))
            if self.select_all.value != all_enabled:
                self._updating_select_all = True
                try:
                    self.select_all.value = all_enabled
                finally:
                    self._updating_select_all = False

    def _select_all_rois(self) -> None:
        if getattr(self, "_updating_select_all", False):
            return
        if hasattr(self, "select_all") and self.select_all is not None:
            state = bool(self.select_all.value)
            for roi in self.rois:
                roi.enabled = state
            self._show_rois()

    def _on_roi_enabled_change(self) -> None:
        self._show_rois()
        self._sync_select_all_checkbox()

    def load_rois(self, items: list[ImagePosition | RefImage]) -> None:
        self.rois.clear()
        if hasattr(self, "container") and self.container is not None:
            self.container.clear()
        for item in items:
            roi = Roi(
                name=item.name,
                x=int(item.x),
                y=int(item.y),
                w=int(item.w),
                h=int(item.h),
                color=self.colors[len(self.rois) % len(self.colors)],
                enabled=True,
            )
            self.rois.append(roi)
            self._add_roi_ui(roi)
        self._show_rois()
        self._sync_select_all_checkbox()

    def _show_rois(self) -> None:
        content = "".join(
            self.draw_roi_func(roi.x, roi.y, roi.w, roi.h, roi.color, roi.name)
            for roi in self.rois
            if roi.enabled
        )
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)
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
                    roi.x, roi.y, roi.w, roi.h = self._get_xywh(e)
            self._show_rois()
        elif e.type == "mousemove" and self.draw_on:
            x, y, w, h = self._get_xywh(e)
            rect = self.draw_roi_func(x, y, w, h, "red", "")
            self.show_temp_draw_in_svg_func(rect)

    def _get_xywh(self, e: events.MouseEventArguments) -> tuple[int, int, int, int]:
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

    def _remove_roi(self) -> None:
        if self.rois:
            self.rois.pop()
            if (
                hasattr(self, "container")
                and self.container is not None
                and len(list(self.container)) > 0
            ):
                last = len(list(self.container)) - 1
                self.container.remove(last)
            self._show_rois()
            self._sync_select_all_checkbox()

    def _delete_roi(self, roi: Roi, row_elem) -> None:
        if roi in self.rois:
            self.rois.remove(roi)
        if (
            hasattr(self, "container")
            and self.container is not None
            and row_elem in self.container
        ):
            self.container.remove(row_elem)
        self._show_rois()
        self._sync_select_all_checkbox()

    def _align_top(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = roi.y
                else:
                    roi.y = y
        self._show_rois()

    def _align_left(self) -> None:
        x = None
        for roi in self.rois:
            if roi.enabled:
                if x is None:
                    x = roi.x
                else:
                    roi.x = x
        self._show_rois()

    def _align_bottom(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = roi.y + roi.h
                else:
                    roi.y = y - roi.h
        self._show_rois()

    def _align_right(self) -> None:
        x = None
        for roi in self.rois:
            if roi.enabled:
                if x is None:
                    x = roi.x + roi.w
                else:
                    roi.x = x - roi.w
        self._show_rois()

    def _align_center(self) -> None:
        y = None
        for roi in self.rois:
            if roi.enabled:
                if y is None:
                    y = int(roi.y + roi.h / 2)
                else:
                    roi.y = int(y - roi.h / 2)
        self._show_rois()

    def _resize_all(self) -> None:
        search_first = True
        width = 0
        height = 0

        for roi in self.rois:
            if roi.enabled:
                if search_first:
                    width = roi.w
                    height = roi.h
                    search_first = False
                else:
                    roi.w = width
                    roi.h = height
        self._show_rois()

    def _distribute_horizontally(self) -> None:
        enabled_rois = [roi for roi in self.rois if roi.enabled]
        if len(enabled_rois) < 3:
            return
        enabled_rois.sort(key=lambda r: r.x)
        min_x = enabled_rois[0].x
        max_x = enabled_rois[-1].x
        total_span = max_x - min_x
        step = total_span / (len(enabled_rois) - 1)
        for i, roi in enumerate(enabled_rois):
            roi.x = int(min_x + i * step)
        self._show_rois()

    def _get_cnn_models(self, dir: str) -> dict[str, str]:
        models = {}
        for path in sorted(Path(dir).rglob("*.tflite")):
            try:
                rel = path.relative_to(dir)
                if len(rel.parts) > 1:
                    display_name = f"{rel.parent} / {path.name}"
                else:
                    display_name = path.name
            except Exception:
                display_name = path.name
            models[str(path)] = display_name
        return models

    def _get_base64_image_by_name(
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

    def _convert_value(self, value):
        return round(value, 2) if isinstance(value, float) else value

    async def open_benchmark_dialog(
        self,
        models_dir: str,
        model_type: str,
        cnn_type_val: str,
        on_apply_callback: Callable[[str], None],
    ) -> None:
        if not self.image:
            ui.notify("Please load an image first to run benchmarks", type="warning")
            return
        if not self.rois:
            ui.notify(
                "Please define at least one ROI to run benchmarks", type="warning"
            )
            return

        models_dict = self._get_cnn_models(models_dir)
        if not models_dict:
            ui.notify(
                f"No .tflite models found in {models_dir}",
                type="warning",
            )
            return

        cut_images = self._cut_images()
        if not cut_images:
            ui.notify("Failed to crop ROI images for benchmarking", type="warning")
            return

        candidate_models = [{"file": f, "name": n} for f, n in models_dict.items()]
        roi_thumbnails = {
            img.name: self._get_base64_image_by_name(img.name, cut_images)
            for img in cut_images
        }

        from gui.dialog_benchmark import open_model_benchmark_dialog

        open_model_benchmark_dialog(
            model_type=model_type,
            candidate_models=candidate_models,
            cut_images=cut_images,
            cnn_type_val=cnn_type_val,
            convert_value_fn=self._convert_value,
            roi_thumbnails=roi_thumbnails,
            on_apply_callback=on_apply_callback,
        )

    def update_image(
        self,
        image: str,
        autocontrast: bool = False,
        cutoff_low: float = 2,
        cutoff_high: float = 45,
        glare_suppression: bool = False,
        glare_mode: str = "clahe",
        glare_inpaint_threshold: int = 230,
        glare_inpaint_radius: int = 3,
        glare_clahe_clip_limit: float = 2.0,
        glare_clahe_grid_size: int = 8,
    ) -> None:
        self.image = image
        self.autocontrast = autocontrast
        self.cutoff_low = cutoff_low
        self.cutoff_high = cutoff_high
        self.glare_suppression = glare_suppression
        self.glare_mode = glare_mode
        self.glare_inpaint_threshold = glare_inpaint_threshold
        self.glare_inpaint_radius = glare_inpaint_radius
        self.glare_clahe_clip_limit = glare_clahe_clip_limit
        self.glare_clahe_grid_size = glare_clahe_grid_size

    def _cut_images(self) -> list[CutImage]:
        positions = [
            ImagePosition(
                name=roi.name,
                x=int(roi.x),
                y=int(roi.y),
                w=int(roi.w),
                h=int(roi.h),
            )
            for roi in self.rois
        ]
        return (
            ImageProcessor()
            .set_image_from_base64_str(self.image)
            .start_image_cutting()
            .cut_images(
                positions,
                autocontrast=self.autocontrast,
                cutoff_low=self.cutoff_low,
                cutoff_high=self.cutoff_high,
                glare_suppression=getattr(self, "glare_suppression", False),
                glare_mode=getattr(self, "glare_mode", "clahe"),
                glare_inpaint_threshold=getattr(self, "glare_inpaint_threshold", 230),
                glare_inpaint_radius=getattr(self, "glare_inpaint_radius", 3),
                glare_clahe_clip_limit=getattr(self, "glare_clahe_clip_limit", 2.0),
                glare_clahe_grid_size=getattr(self, "glare_clahe_grid_size", 8),
            )
            .stop_image_cutting()
            .save_cut_images()
            .get_cut_images()
        )

    def _create_new_roi(self) -> Roi:
        i = len(self.rois)
        return Roi(
            color=self.colors[i % len(self.colors)],
            name=f"{self.name_template}{i + 1}",
            enabled=True,
            x=20 + (25 * (i % 8)),
            y=20 + (25 * (i % 8)),
            w=60,
            h=80,
        )

    def _unselect_all_rois(self) -> None:
        for roi in self.rois:
            roi.enabled = False

    def _add_roi(self) -> None:
        self._unselect_all_rois()
        roi = self._create_new_roi()
        self.rois.append(roi)
        self._add_roi_ui(roi)
        self._show_rois()
        self._sync_select_all_checkbox()

    def _add_roi_ui(self, roi: Roi) -> None:
        if not hasattr(self, "container") or not hasattr(self.container, "__enter__"):
            return
        with self.container:
            with ui.row().classes(
                "w-full items-center justify-between p-2 rounded-xl "
                "bg-slate-900/70 border border-white/10 shadow-sm gap-2 mb-2"
            ) as row_elem:
                with ui.row().classes("items-center gap-2 flex-grow"):
                    ui.checkbox(on_change=self._on_roi_enabled_change).bind_value(
                        roi, "enabled"
                    ).props(f"color={roi.color} keep-color").tooltip(
                        "Toggle ROI overlay visibility on canvas"
                    )
                    ui.input(label="Name").bind_value(roi, "name").classes(
                        "w-28 text-sm"
                    ).tooltip("Region of interest name")
                    ui.number("X", on_change=self._show_rois, step=1).bind_value(
                        roi, "x", forward=lambda x: int(x or 0)
                    ).classes("w-20 text-sm").tooltip("X coordinate in pixels")
                    ui.number("Y", on_change=self._show_rois, step=1).bind_value(
                        roi, "y", forward=lambda x: int(x or 0)
                    ).classes("w-20 text-sm").tooltip("Y coordinate in pixels")
                    ui.number("W", on_change=self._show_rois, min=1, step=1).bind_value(
                        roi, "w", forward=lambda x: int(x or 1)
                    ).classes("w-20 text-sm").tooltip("Width in pixels")
                    ui.number("H", on_change=self._show_rois, min=1, step=1).bind_value(
                        roi, "h", forward=lambda x: int(x or 1)
                    ).classes("w-20 text-sm").tooltip("Height in pixels")

                ui.button(
                    icon="delete_outline",
                    on_click=lambda r=roi, el=row_elem: self._delete_roi(r, el),
                ).props("flat color=negative dense").classes(
                    "rounded-lg hover:bg-red-500/20"
                ).tooltip(
                    "Delete this region"
                )
