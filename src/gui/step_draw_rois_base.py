from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import time

from nicegui import events, ui

from data_classes import CutImage, ImagePosition, RefImage
from .step_base import BaseStep
import utils.image
from processor.digitizer import DigitizerProcessor
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

        benchmark_results = []
        for modelfile, model_display_name in models_dict.items():
            start = time.time()
            try:
                dp = DigitizerProcessor()
                if model_type == "digital":
                    dp.init_digital_model(modelfile, cnn_type_val)
                    dp.execute_digital_cnn(cut_images)
                    dp.evaluate_cnn_results()
                    results = dp.cnn_digital_results
                else:
                    dp.init_analog_model(modelfile, cnn_type_val)
                    dp.execute_analog_cnn(cut_images)
                    dp.evaluate_cnn_results()
                    results = dp.cnn_analog_results

                latency_ms = round((time.time() - start) * 1000, 1)
                avg_conf = (
                    round(sum(r.confidence for r in results) / len(results), 1)
                    if results
                    else 0.0
                )
                composite_val = " ".join(
                    str(self._convert_value(r.value)) for r in results
                )
                benchmark_results.append(
                    {
                        "file": modelfile,
                        "name": model_display_name,
                        "latency_ms": latency_ms,
                        "avg_confidence": avg_conf,
                        "composite": composite_val,
                        "results": results,
                        "error": None,
                    }
                )
            except Exception as e:
                logger.exception(f"Error evaluating model {model_display_name}: {e}")
                benchmark_results.append(
                    {
                        "file": modelfile,
                        "name": model_display_name,
                        "latency_ms": 0.0,
                        "avg_confidence": 0.0,
                        "composite": "ERR",
                        "results": [],
                        "error": str(e),
                    }
                )

        # Sort descending by average confidence, then ascending by latency
        benchmark_results.sort(
            key=lambda x: (
                x["error"] is None,
                x["avg_confidence"],
                -x["latency_ms"],
            ),
            reverse=True,
        )

        top_model = (
            benchmark_results[0]
            if benchmark_results and benchmark_results[0]["error"] is None
            else None
        )
        fastest_model = (
            min(
                (b for b in benchmark_results if b["error"] is None),
                key=lambda x: x["latency_ms"],
                default=None,
            )
            if benchmark_results
            else None
        )

        roi_thumbnails = {
            img.name: self._get_base64_image_by_name(img.name, cut_images)
            for img in cut_images
        }

        with (
            ui.dialog() as dialog,
            ui.card().classes(
                "w-[94vw] max-w-5xl h-[88vh] bg-slate-950/95 "
                "border border-white/10 rounded-2xl shadow-2xl p-0 "
                "flex flex-col overflow-hidden backdrop-blur-xl"
            ),
        ):
            # Dialog Header
            with ui.row().classes(
                "w-full justify-between items-center px-6 py-4 border-b "
                "border-white/10 bg-slate-900/80 shrink-0"
            ):
                with ui.row().classes("items-center gap-3"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 "
                        "to-cyan-500 flex items-center justify-center shadow-md "
                        "shadow-indigo-500/20"
                    ):
                        ui.icon("analytics", color="white").classes("text-xl")
                    with ui.column().classes("gap-0"):
                        ui.label("Neural Network Model Benchmark").classes(
                            "text-lg font-bold text-white leading-tight"
                        )
                        ui.label(
                            f"Evaluated {len(benchmark_results)} candidate "
                            f"{model_type} models across {len(cut_images)} ROIs"
                        ).classes("text-xs text-slate-400")
                ui.button(icon="close", on_click=dialog.close).props(
                    "flat round dense text-color=slate-400"
                ).classes("hover:bg-white/10")

            # KPI Summary Bar
            with ui.row().classes(
                "w-full px-6 py-3 bg-slate-900/40 border-b border-white/5 "
                "gap-4 items-center justify-between text-xs shrink-0 flex-wrap"
            ):
                with ui.row().classes("items-center gap-2"):
                    if top_model:
                        ui.label("★ Top Accuracy:").classes(
                            "text-slate-400 font-medium"
                        )
                        ui.label(
                            f"{top_model['name']} ({top_model['avg_confidence']}%)"
                        ).classes("font-bold text-emerald-400 font-mono")
                with ui.row().classes("items-center gap-2"):
                    if fastest_model:
                        ui.label("⚡ Fastest:").classes("text-slate-400 font-medium")
                        ui.label(
                            f"{fastest_model['name']} ({fastest_model['latency_ms']}ms)"
                        ).classes("font-bold text-cyan-400 font-mono")
                with ui.row().classes("items-center gap-2"):
                    ui.label("ROIs:").classes("text-slate-400 font-medium")
                    ui.label(f"{len(cut_images)} regions").classes(
                        "font-semibold text-slate-300 font-mono"
                    )

            # Reference ROI Crops Bar (Visual Ground Truth)
            with ui.row().classes(
                "w-full px-6 py-2.5 bg-slate-900/60 border-b border-white/5 "
                "gap-3 items-center shrink-0 flex-nowrap overflow-x-auto "
                "custom-scrollbar"
            ):
                with ui.row().classes("items-center gap-1.5 shrink-0 mr-2"):
                    ui.icon("photo_camera", size="xs").classes("text-cyan-400")
                    ui.label("ROI Reference:").classes(
                        "text-xs font-semibold text-slate-300 whitespace-nowrap"
                    )
                for cut_img in cut_images:
                    b64 = roi_thumbnails.get(cut_img.name, "")
                    img_w_h = "w-9 h-14" if model_type == "digital" else "w-12 h-12"
                    with ui.element("div").classes(
                        "p-1.5 rounded-lg bg-slate-950/80 border border-white/10 "
                        "flex flex-col items-center gap-1 shrink-0"
                    ):
                        ui.label(cut_img.name).classes(
                            "text-[10px] text-slate-400 font-semibold "
                            "uppercase font-mono"
                        )
                        if b64:
                            ui.html(
                                f'<img src="data:image/jpeg;base64,{b64}" '
                                f'class="{img_w_h} rounded bg-slate-900 p-0.5 '
                                'border border-white/5 object-contain" />'
                            )

            # Benchmark Results Table Container
            with ui.element("div").classes(
                "w-full flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-3 "
                "custom-scrollbar"
            ):
                with ui.element("table").classes("w-full text-left border-collapse"):
                    with ui.element("thead").classes(
                        "text-xs font-semibold uppercase text-slate-400 "
                        "bg-slate-900/80 sticky top-0 z-10 border-b border-white/10"
                    ):
                        with ui.element("tr"):
                            with ui.element("th").classes("p-3"):
                                ui.label("Model File")
                            with ui.element("th").classes("p-3 text-center"):
                                ui.label("Avg Conf")
                            with ui.element("th").classes("p-3 text-center"):
                                ui.label("Speed")
                            with ui.element("th").classes("p-3"):
                                ui.label("Per-ROI Predictions")
                            with ui.element("th").classes("p-3 text-right"):
                                ui.label("Action")

                    with ui.element("tbody").classes("text-sm divide-y divide-white/5"):
                        for idx, item in enumerate(benchmark_results):
                            is_top = idx == 0 and item["error"] is None
                            row_bg = (
                                "bg-indigo-950/20 hover:bg-indigo-950/40"
                                if is_top
                                else "hover:bg-slate-900/60"
                            )
                            with ui.element("tr").classes(
                                f"{row_bg} transition-colors"
                            ):
                                # Model Name
                                with ui.element("td").classes("p-3 align-middle"):
                                    with ui.column().classes("gap-1"):
                                        with ui.row().classes(
                                            "items-center gap-1.5 flex-nowrap"
                                        ):
                                            if is_top:
                                                ui.icon("verified", size="xs").classes(
                                                    "text-emerald-400"
                                                ).tooltip("Top Ranked Model")
                                            ui.label(item["name"]).classes(
                                                "font-medium text-slate-200 "
                                                "font-mono text-xs"
                                            ).tooltip(item["file"])

                                        # Architecture & Precision Badges
                                        with ui.row().classes(
                                            "items-center gap-1 flex-wrap"
                                        ):
                                            n_low = item["name"].lower()
                                            if "class100" in n_low:
                                                ui.label("Class 100").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-indigo-900/60 "
                                                    "text-indigo-300 font-semibold "
                                                    "border border-indigo-500/30"
                                                )
                                            elif "class11" in n_low:
                                                ui.label("Class 11").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-purple-900/60 "
                                                    "text-purple-300 font-semibold "
                                                    "border border-purple-500/30"
                                                )
                                            elif "cont" in n_low:
                                                ui.label("Continuous").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-cyan-900/60 "
                                                    "text-cyan-300 font-semibold "
                                                    "border border-cyan-500/30"
                                                )
                                            elif (
                                                "legacy" in n_low or "version" in n_low
                                            ):
                                                ui.label("Legacy").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-slate-800 "
                                                    "text-slate-400 font-semibold "
                                                    "border border-white/10"
                                                )

                                            if "_q" in n_low or "-q" in n_low:
                                                ui.label("⚡ Int8").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-emerald-950/80 "
                                                    "text-emerald-300 font-semibold "
                                                    "border border-emerald-500/30 "
                                                    "font-mono"
                                                )
                                            else:
                                                ui.label("Float32").classes(
                                                    "text-[9px] px-1.5 py-0.2 "
                                                    "rounded bg-slate-900 "
                                                    "text-slate-400 font-semibold "
                                                    "border border-white/10 font-mono"
                                                )

                                # Avg Confidence
                                with ui.element("td").classes(
                                    "p-3 align-middle text-center"
                                ):
                                    if item["error"]:
                                        ui.label("—").classes("text-slate-500")
                                    else:
                                        conf = item["avg_confidence"]
                                        if conf >= 90:
                                            badge_cls = (
                                                "bg-emerald-500/15 text-emerald-400 "
                                                "border-emerald-500/30"
                                            )
                                        elif conf >= 70:
                                            badge_cls = (
                                                "bg-amber-500/15 text-amber-400 "
                                                "border-amber-500/30"
                                            )
                                        else:
                                            badge_cls = (
                                                "bg-red-500/15 text-red-400 "
                                                "border-red-500/30"
                                            )
                                        ui.label(f"{conf:.1f}%").classes(
                                            "px-2 py-0.5 rounded-full "
                                            "text-xs font-semibold border "
                                            f"{badge_cls} font-mono"
                                        )

                                # Speed
                                with ui.element("td").classes(
                                    "p-3 align-middle text-center text-xs "
                                    "font-mono text-slate-400"
                                ):
                                    ui.label(
                                        f"{item['latency_ms']}ms"
                                        if not item["error"]
                                        else "—"
                                    )

                                # Per-ROI Predictions
                                with ui.element("td").classes("p-3 align-middle"):
                                    if item["error"]:
                                        ui.label("Failed to infer").classes(
                                            "text-xs text-red-400 italic"
                                        )
                                    else:
                                        with ui.row().classes(
                                            "items-center gap-2 flex-wrap"
                                        ):
                                            for res in item["results"]:
                                                val_str = self._convert_value(res.value)
                                                c = res.confidence
                                                c_color = (
                                                    "text-emerald-400"
                                                    if c >= 90
                                                    else (
                                                        "text-amber-400"
                                                        if c >= 70
                                                        else "text-red-400"
                                                    )
                                                )
                                                b64 = roi_thumbnails.get(res.name, "")
                                                thumb_w_h = (
                                                    "w-6 h-9"
                                                    if model_type == "digital"
                                                    else "w-8 h-8"
                                                )
                                                with (
                                                    ui.element("div")
                                                    .classes(
                                                        "p-1.5 rounded-lg "
                                                        "bg-slate-900/90 border "
                                                        "border-white/10 text-xs "
                                                        "flex items-center gap-2 "
                                                        "font-mono "
                                                        "hover:border-cyan-500/40 "
                                                        "transition-colors"
                                                    )
                                                    .tooltip(
                                                        f"{res.name}: "
                                                        f"value={val_str}, "
                                                        f"confidence={c:.1f}%"
                                                    )
                                                ):
                                                    if b64:
                                                        img_src = (
                                                            "data:image/jpeg;"
                                                            f"base64,{b64}"
                                                        )
                                                        ui.html(
                                                            f'<img src="{img_src}" '
                                                            f'class="{thumb_w_h} '
                                                            "rounded bg-slate-950 "
                                                            "p-0.5 border "
                                                            "border-white/10 shrink-0 "
                                                            "object-contain "
                                                            'inline-block" />'
                                                        )
                                                    with ui.column().classes(
                                                        "gap-0 leading-tight"
                                                    ):
                                                        ui.label(f"{res.name}").classes(
                                                            "text-slate-400 "
                                                            "text-[10px] "
                                                            "uppercase font-semibold"
                                                        )
                                                        ui.label(f"{val_str}").classes(
                                                            "font-bold "
                                                            "text-slate-100 text-xs"
                                                        )
                                                        ui.label(f"{c:.0f}%").classes(
                                                            f"text-[10px] "
                                                            f"font-semibold {c_color}"
                                                        )

                                # Action Button
                                with ui.element("td").classes(
                                    "p-3 align-middle text-right"
                                ):

                                    def _make_apply(f=item["file"], n=item["name"]):
                                        def _apply():
                                            on_apply_callback(f)
                                            dialog.close()
                                            ui.notify(
                                                f"Applied model: {n}",
                                                type="positive",
                                            )

                                        return _apply

                                    ui.button(
                                        "Apply",
                                        icon="check",
                                        on_click=_make_apply(
                                            item["file"], item["name"]
                                        ),
                                    ).props("unelevated dense").classes(
                                        "bg-indigo-600 hover:bg-indigo-500 "
                                        "text-white text-xs px-2.5 py-1 "
                                        "rounded-lg font-medium"
                                        if is_top
                                        else "bg-slate-800 hover:bg-slate-700 "
                                        "text-slate-300 border border-white/10 "
                                        "text-xs px-2.5 py-1 rounded-lg"
                                    ).tooltip(
                                        f"Set {item['name']} as active model"
                                    )

            # Dialog Footer
            with ui.row().classes(
                "w-full px-6 py-3 border-t border-white/10 bg-slate-900/60 "
                "justify-between items-center shrink-0 text-xs text-slate-400"
            ):
                ui.label(
                    "Tip: Higher average confidence indicates "
                    "better prediction certainty."
                )
                ui.button("Close", on_click=dialog.close).props(
                    "outline dense"
                ).classes("text-slate-300 border-white/20 hover:bg-white/10")

        dialog.open()

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

    def _add_roi_ui(self, roi: Roi) -> None:
        with self.container:
            with ui.row().classes(
                "w-full items-center justify-between p-2 rounded-xl "
                "bg-slate-900/70 border border-white/10 shadow-sm gap-2 mb-2"
            ) as row_elem:
                with ui.row().classes("items-center gap-2 flex-grow"):
                    ui.checkbox(on_change=self._show_rois).bind_value(
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
