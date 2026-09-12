import asyncio
import logging
import os
from collections.abc import Callable

from nicegui import ui

from configuration import Config
from data_classes import RefImage
from processor.image import ImageProcessor

from .step_base import BaseStep

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "- **Live Visual Sliders**: Adjust parameters in real-time with instant "
    "debounced preview.\n"
    "- **Compare Mode**: Switch between single adjusted preview and side-by-side "
    "before/after comparison.\n"
    "- **Fine Rotation**: Correct fractional angles (e.g. `0.5°`).\n"
    "- **Crop & Resize**: Optionally crop and resize frame before alignment.\n"
    "- **Image Processing**: Master toggle to enable/disable all image processing enhancements.\n"
    "- **Image Filters**: Tune contrast, brightness, sharpness, color saturation, and grayscale.\n"
    "- **Histogram & AutoContrast**: Optimize histogram contrast stretching for full frame or ROIs.\n"
    "- **Glare Suppression**: Eliminate glass reflections using CLAHE, inpainting, "
    "or combined mode."
)

BADGE_CLASSES = "w-14 text-right text-xs font-mono font-bold text-cyan-400 shrink-0"


class AdjustStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        set_comparison_callback: Callable[[str], None] | None = None,
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.set_comparison_callback = set_comparison_callback
        self.org_image: str = ""
        self.ref_images: list[RefImage] = []
        self._debounce_task: asyncio.Task | None = None

        # Control references
        self.live_preview: ui.checkbox
        self.compare_mode: ui.radio
        self.rotate_enabled: ui.checkbox
        self.rotate_angle: ui.number
        self.rotate_slider: ui.slider

        self.crop_enabled: ui.checkbox
        self.crop_x: ui.number
        self.crop_y: ui.number
        self.crop_w: ui.number
        self.crop_h: ui.number

        self.resize_enabled: ui.checkbox
        self.resize_w: ui.number
        self.resize_h: ui.number

        self.adjust_enabled: ui.checkbox
        self.grayscale_enabled: ui.checkbox
        self.adjust_contrast: ui.slider
        self.adjust_brightness: ui.slider
        self.adjust_sharpness: ui.slider
        self.adjust_color: ui.slider

        self.autocontrast_enabled: ui.checkbox
        self.autocontrast_cutoff_low: ui.slider
        self.autocontrast_cutoff_high: ui.slider
        self.autocontrast_cut_images_enabled: ui.checkbox
        self.autocontrast_cut_images_cutoff_low: ui.slider
        self.autocontrast_cut_images_cutoff_high: ui.slider

        self.glare_enabled: ui.checkbox
        self.glare_apply_to_cut_images: ui.checkbox
        self.glare_mode: ui.select
        self.glare_inpaint_threshold: ui.slider
        self.glare_inpaint_radius: ui.slider
        self.glare_clahe_clip_limit: ui.slider
        self.glare_clahe_grid_size: ui.slider

    @property
    def image_processing_enabled(self) -> ui.checkbox:
        return self.adjust_enabled

    def update_image(self, image: str) -> None:
        self.org_image = image
        self._update_preview_canvas()

    def _reset_image(self) -> None:
        if self.org_image != "":
            self.image = self.org_image
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)
        if self.set_comparison_callback is not None:
            self.set_comparison_callback("")

    def _on_param_change(self) -> None:
        if not getattr(self, "live_preview", None) or not self.live_preview.value:
            return

        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        async def debounced_update():
            try:
                await asyncio.sleep(0.1)
                self._update_preview_canvas()
            except asyncio.CancelledError:
                pass

        self._debounce_task = asyncio.create_task(debounced_update())

    def _get_base_aligned_image(self, image: str) -> str:
        ref_images = [
            r
            for r in getattr(self, "ref_images", [])
            if getattr(r, "file_name", "") and os.path.exists(r.file_name)
        ]
        proc = ImageProcessor().set_image_from_base64_str(image)
        if len(ref_images) == 3:
            try:
                proc.align_image(ref_images)
            except Exception as e:
                logger.debug(f"Alignment skipped in base image helper: {e}")
        return proc.get_image_as_base64_str()

    def _update_preview_canvas(self) -> None:
        if not self.org_image:
            return

        try:
            adjusted_b64 = self._do_adjust(self.org_image)
        except Exception as e:
            logger.warning(f"Error adjusting image preview: {e}")
            adjusted_b64 = self.org_image

        self.image = adjusted_b64

        # Compare mode logic
        compare = self.compare_mode.value if hasattr(self, "compare_mode") else "Single"
        if compare == "Side-by-Side":
            if self.set_image_callback is not None:
                self.set_image_callback(self.org_image)
            if self.set_comparison_callback is not None:
                self.set_comparison_callback(adjusted_b64)
        else:
            if self.set_image_callback is not None:
                self.set_image_callback(self.image)
            if self.set_comparison_callback is not None:
                self.set_comparison_callback("")

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def do_adjust(self) -> None:
        self._update_preview_canvas()

    def load_from_config(self, config: Config) -> None:
        # Crop
        self.crop_enabled.value = config.crop.enabled
        self.crop_x.value = config.crop.x
        self.crop_y.value = config.crop.y
        self.crop_w.value = config.crop.w
        self.crop_h.value = config.crop.h

        # Resize
        self.resize_enabled.value = config.resize.enabled
        self.resize_w.value = config.resize.w
        self.resize_h.value = config.resize.h

        # Image adjustments
        self.adjust_enabled.value = config.image_processing.enabled
        self.adjust_contrast.value = config.image_processing.contrast
        self.adjust_brightness.value = config.image_processing.brightness
        self.adjust_sharpness.value = config.image_processing.sharpness
        self.adjust_color.value = config.image_processing.color
        self.grayscale_enabled.value = config.image_processing.grayscale

        # AutoContrast
        self.autocontrast_enabled.value = config.image_processing.autocontrast.enabled
        self.autocontrast_cutoff_low.value = (
            config.image_processing.autocontrast.cutoff_low
        )
        self.autocontrast_cutoff_high.value = (
            config.image_processing.autocontrast.cutoff_high
        )
        self.autocontrast_cut_images_enabled.value = (
            config.image_processing.autocontrast_cut_images.enabled
        )
        self.autocontrast_cut_images_cutoff_low.value = (
            config.image_processing.autocontrast_cut_images.cutoff_low
        )
        self.autocontrast_cut_images_cutoff_high.value = (
            config.image_processing.autocontrast_cut_images.cutoff_high
        )

        # Glare Suppression
        self.glare_enabled.value = config.image_processing.glare_suppression.enabled
        self.glare_mode.value = config.image_processing.glare_suppression.mode
        self.glare_inpaint_threshold.value = (
            config.image_processing.glare_suppression.inpaint_threshold
        )
        self.glare_inpaint_radius.value = (
            config.image_processing.glare_suppression.inpaint_radius
        )
        self.glare_clahe_clip_limit.value = (
            config.image_processing.glare_suppression.clahe_clip_limit
        )
        self.glare_clahe_grid_size.value = (
            config.image_processing.glare_suppression.clahe_grid_size
        )
        self.glare_apply_to_cut_images.value = (
            config.image_processing.glare_suppression.apply_to_cut_images
        )

        # Alignment
        self.ref_images = list(config.alignment.ref_images)

        # Rotation
        self.rotate_angle.value = config.alignment.post_rotate_angle
        self.rotate_enabled.value = config.alignment.post_rotate_angle != 0

    def _do_adjust(self, image: str) -> str:
        if not image:
            return ""

        ref_images = [
            r
            for r in getattr(self, "ref_images", [])
            if getattr(r, "file_name", "") and os.path.exists(r.file_name)
        ]
        proc = ImageProcessor().set_image_from_base64_str(image)

        if len(ref_images) == 3:
            try:
                proc.align_image(ref_images)
            except Exception as e:
                logger.debug(
                    f"Reference alignment skipped during adjustment preview: {e}"
                )

        try:
            if getattr(self, "rotate_enabled", None) and self.rotate_enabled.value:
                angle = float(self.rotate_angle.value or 0.0)
                if angle != 0.0:
                    proc.rotate_image(angle)
        except Exception as e:
            logger.debug(f"Rotation adjustment skipped: {e}")

        try:
            if getattr(self, "crop_enabled", None) and self.crop_enabled.value:
                cx = int(self.crop_x.value or 0)
                cy = int(self.crop_y.value or 0)
                cw = int(self.crop_w.value or 0)
                ch = int(self.crop_h.value or 0)
                if cw > 0 and ch > 0:
                    proc.crop_image(x=cx, y=cy, w=cw, h=ch)
        except Exception as e:
            logger.debug(f"Crop adjustment skipped: {e}")

        try:
            if getattr(self, "resize_enabled", None) and self.resize_enabled.value:
                rw = int(self.resize_w.value or 0)
                rh = int(self.resize_h.value or 0)
                if rw > 0 and rh > 0:
                    proc.resize_image(width=rw, height=rh)
        except Exception as e:
            logger.debug(f"Resize adjustment skipped: {e}")

        # Image processing enhancements (gated by master ImageProcessing.enabled)
        if getattr(self, "adjust_enabled", None) and self.adjust_enabled.value:
            try:
                proc.adjust_image(
                    contrast=float(self.adjust_contrast.value or 1.0),
                    brightness=float(self.adjust_brightness.value or 1.0),
                    sharpness=float(self.adjust_sharpness.value or 1.0),
                    color=float(self.adjust_color.value or 1.0),
                )
            except Exception as e:
                logger.debug(f"Filters adjustment skipped: {e}")

            try:
                if (
                    getattr(self, "grayscale_enabled", None)
                    and self.grayscale_enabled.value
                ):
                    proc.to_gray_scale()
            except Exception as e:
                logger.debug(f"Grayscale conversion skipped: {e}")

            try:
                if (
                    getattr(self, "autocontrast_enabled", None)
                    and self.autocontrast_enabled.value
                ):
                    proc.autocontrast_image(
                        cutoff_low=float(self.autocontrast_cutoff_low.value or 0.0),
                        cutoff_high=float(self.autocontrast_cutoff_high.value or 0.0),
                    )
            except Exception as e:
                logger.debug(f"AutoContrast adjustment skipped: {e}")

            try:
                if getattr(self, "glare_enabled", None) and self.glare_enabled.value:
                    proc.suppress_glare(
                        mode=str(self.glare_mode.value or "clahe"),
                        inpaint_threshold=int(
                            self.glare_inpaint_threshold.value or 230
                        ),
                        inpaint_radius=int(self.glare_inpaint_radius.value or 3),
                        clahe_clip_limit=float(
                            self.glare_clahe_clip_limit.value or 2.0
                        ),
                        clahe_grid_size=int(self.glare_clahe_grid_size.value or 8),
                    )
            except Exception as e:
                logger.debug(f"Glare suppression adjustment skipped: {e}")

        return proc.get_image_as_base64_str()

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            # Live Preview & View Mode Toolbar
            with ui.row().classes(
                "w-full items-center justify-between p-3 mb-2 rounded-xl "
                "bg-indigo-950/40 border border-indigo-500/30 backdrop-blur-md"
            ):
                with ui.row().classes("items-center gap-3"):
                    self.live_preview = ui.checkbox(
                        "Live Preview", value=True, on_change=self._on_param_change
                    ).classes("text-indigo-200 text-sm font-semibold")
                    ui.label("•").classes("text-indigo-400/50")
                    ui.label("View Mode:").classes("text-xs text-slate-400 font-medium")
                    self.compare_mode = (
                        ui.radio(
                            ["Single", "Side-by-Side"],
                            value="Single",
                            on_change=self._on_param_change,
                        )
                        .props("inline dense")
                        .classes("text-xs text-indigo-300 font-medium")
                    )

                with ui.row().classes("items-center gap-2"):
                    ui.button(
                        "Hold for Original",
                        icon="visibility",
                    ).props("outline dense").classes(
                        "text-xs border-indigo-400/40 text-indigo-300 "
                        "hover:bg-indigo-500/20 px-2 py-1"
                    ).on(
                        "mousedown",
                        lambda: (
                            self.set_image_callback(self.org_image)
                            if self.set_image_callback
                            else None
                        ),
                    ).on(
                        "mouseup", self._update_preview_canvas
                    ).on(
                        "mouseleave", self._update_preview_canvas
                    ).tooltip(
                        "Press and hold to temporarily view raw unadjusted image"
                    )

            with ui.column().classes("w-full gap-3 my-2"):
                # Image Processing Master Card
                with ui.row().classes(
                    "w-full items-center justify-between p-3 rounded-xl "
                    "bg-slate-900/80 border border-white/10 shadow-md gap-3"
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("tune", size="22px").classes("text-cyan-400 shrink-0")
                        with ui.column().classes("gap-0"):
                            ui.label("Image Processing").classes(
                                "text-sm font-bold text-white"
                            )
                            ui.label(
                                "Master toggle for filters, grayscale, autocontrast, and glare suppression"
                            ).classes("text-xs text-gray-400")
                    self.adjust_enabled = (
                        ui.checkbox(
                            "Enable Image Processing",
                            value=False,
                            on_change=self._on_param_change,
                        )
                        .props("color=cyan")
                        .tooltip(
                            "Enable or disable all image processing enhancements ([ImageProcessing] section)"
                        )
                    )

                # Geometry & Cropping Expansion
                with (
                    ui.expansion(
                        "Geometry & Cropping", icon="crop", value=True
                    ).classes(
                        "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                        "shadow-md overflow-hidden"
                    ),
                    ui.column().classes("w-full gap-3 p-3"),
                ):
                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        self.rotate_enabled = ui.checkbox(
                            "Enable Fine Rotation",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip("Enable fine rotation angle correction")
                        self.rotate_angle = (
                            ui.number(
                                "Angle (°)",
                                min=-359,
                                max=359,
                                step=0.5,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-28")
                            .tooltip("Fine rotation angle in degrees (-359° to 359°)")
                        )

                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        self.crop_enabled = ui.checkbox(
                            "Enable Crop",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip("Enable rectangular cropping before alignment")
                        self.crop_x = (
                            ui.number(
                                "X",
                                min=0,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-20")
                            .tooltip("Crop starting X position in pixels")
                        )
                        self.crop_y = (
                            ui.number(
                                "Y",
                                min=0,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-20")
                            .tooltip("Crop starting Y position in pixels")
                        )
                        self.crop_w = (
                            ui.number(
                                "Width",
                                min=640,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-24")
                            .tooltip("Crop area width in pixels")
                        )
                        self.crop_h = (
                            ui.number(
                                "Height",
                                min=480,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-24")
                            .tooltip("Crop area height in pixels")
                        )

                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        self.resize_enabled = ui.checkbox(
                            "Enable Resize",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip("Enable image resizing")
                        self.resize_w = (
                            ui.number(
                                "Width",
                                min=0,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-24")
                            .tooltip("Resized image width in pixels")
                        )
                        self.resize_h = (
                            ui.number(
                                "Height",
                                min=0,
                                max=10000,
                                step=1,
                                value=0,
                                on_change=self._on_param_change,
                            )
                            .classes("w-24")
                            .tooltip("Resized image height in pixels")
                        )

                # Tonal & Color Adjustments Expansion
                with (
                    ui.expansion(
                        "Tonal & Color Adjustments", icon="palette", value=False
                    ).classes(
                        "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                        "shadow-md overflow-hidden"
                    ),
                    ui.column().classes("w-full gap-3 p-3"),
                ):
                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        self.grayscale_enabled = ui.checkbox(
                            "Grayscale",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip("Convert the full image to grayscale")

                    # Live Visual Sliders for Tonal Settings
                    with ui.column().classes("w-full gap-4"):
                        # Contrast
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Contrast").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.adjust_contrast = (
                                ui.slider(
                                    min=0.0,
                                    max=3.0,
                                    step=0.05,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.adjust_contrast,
                                "value",
                                lambda v: f"{float(v or 1.0):.2f}x",
                            )

                        # Brightness
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Brightness").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.adjust_brightness = (
                                ui.slider(
                                    min=0.0,
                                    max=3.0,
                                    step=0.05,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.adjust_brightness,
                                "value",
                                lambda v: f"{float(v or 1.0):.2f}x",
                            )

                        # Sharpness
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Sharpness").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.adjust_sharpness = (
                                ui.slider(
                                    min=0.0,
                                    max=3.0,
                                    step=0.1,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.adjust_sharpness,
                                "value",
                                lambda v: f"{float(v or 1.0):.2f}x",
                            )

                        # Color Saturation
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Color / Sat").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.adjust_color = (
                                ui.slider(
                                    min=0.0,
                                    max=3.0,
                                    step=0.1,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.adjust_color,
                                "value",
                                lambda v: f"{float(v or 1.0):.2f}x",
                            )

                # Histogram & AutoContrast Expansion
                with (
                    ui.expansion(
                        "Histogram & AutoContrast", icon="auto_fix_high", value=False
                    ).classes(
                        "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                        "shadow-md overflow-hidden"
                    ),
                    ui.column().classes("w-full gap-3 p-3"),
                ):
                    self.autocontrast_enabled = ui.checkbox(
                        "Full Frame AutoContrast",
                        value=False,
                        on_change=self._on_param_change,
                    ).tooltip(
                        "Automatically optimize contrast histogram for " "full frame"
                    )

                    with ui.column().classes("w-full gap-4"):
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Cutoff Low").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.autocontrast_cutoff_low = (
                                ui.slider(
                                    min=0,
                                    max=50,
                                    step=1,
                                    value=2,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.autocontrast_cutoff_low,
                                "value",
                                lambda v: f"{int(float(v or 0))}%",
                            )

                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Cutoff High").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.autocontrast_cutoff_high = (
                                ui.slider(
                                    min=0,
                                    max=50,
                                    step=1,
                                    value=45,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.autocontrast_cutoff_high,
                                "value",
                                lambda v: f"{int(float(v or 0))}%",
                            )

                    ui.separator().classes("bg-white/10 my-1")

                    self.autocontrast_cut_images_enabled = ui.checkbox(
                        "Cut Images (ROIs) AutoContrast",
                        value=False,
                        on_change=self._on_param_change,
                    ).tooltip(
                        "Apply automatic contrast stretching individually on "
                        "cropped digit/pointer ROI images"
                    )

                    with ui.column().classes("w-full gap-4"):
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("ROI Cutoff Low").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.autocontrast_cut_images_cutoff_low = (
                                ui.slider(
                                    min=0,
                                    max=50,
                                    step=1,
                                    value=2,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.autocontrast_cut_images_cutoff_low,
                                "value",
                                lambda v: f"{int(float(v or 0))}%",
                            )

                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("ROI Cutoff High").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.autocontrast_cut_images_cutoff_high = (
                                ui.slider(
                                    min=0,
                                    max=50,
                                    step=1,
                                    value=45,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.autocontrast_cut_images_cutoff_high,
                                "value",
                                lambda v: f"{int(float(v or 0))}%",
                            )

                # Glare Suppression Expansion
                with (
                    ui.expansion(
                        "Glare & Specular Reflection Suppression",
                        icon="flare",
                        value=False,
                    ).classes(
                        "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                        "shadow-md overflow-hidden"
                    ),
                    ui.column().classes("w-full gap-3 p-3"),
                ):
                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        self.glare_enabled = ui.checkbox(
                            "Enable Glare Suppression",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip("Suppress specular highlights on glossy meter glass")
                        self.glare_apply_to_cut_images = ui.checkbox(
                            "Apply to Cut Images (ROIs)",
                            value=False,
                            on_change=self._on_param_change,
                        ).tooltip(
                            "Apply glare suppression to cropped digit/pointer " "images"
                        )
                        self.glare_mode = (
                            ui.select(
                                [
                                    "clahe",
                                    "inpaint",
                                    "illumination_normalize",
                                    "combined",
                                ],
                                label="Mode",
                                value="clahe",
                                on_change=self._on_param_change,
                            )
                            .classes("w-44")
                            .tooltip(
                                "Filter mode: clahe, inpaint, "
                                "illumination_normalize, or combined"
                            )
                        )

                    with ui.column().classes("w-full gap-4"):
                        # CLAHE Clip Limit
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("CLAHE Clip").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.glare_clahe_clip_limit = (
                                ui.slider(
                                    min=0.1,
                                    max=10.0,
                                    step=0.2,
                                    value=2.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.glare_clahe_clip_limit,
                                "value",
                                lambda v: f"{float(v or 2.0):.1f}",
                            )

                        # CLAHE Grid Size
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("CLAHE Grid").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.glare_clahe_grid_size = (
                                ui.slider(
                                    min=2,
                                    max=32,
                                    step=1,
                                    value=8,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.glare_clahe_grid_size,
                                "value",
                                lambda v: (
                                    f"{int(float(v or 8))}x{int(float(v or 8))}"
                                ),
                            )

                        # Inpaint Threshold
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Inpaint Thresh").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.glare_inpaint_threshold = (
                                ui.slider(
                                    min=100,
                                    max=255,
                                    step=1,
                                    value=230,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.glare_inpaint_threshold,
                                "value",
                                lambda v: f"{int(float(v or 230))}",
                            )

                        # Inpaint Radius
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Inpaint Radius").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.glare_inpaint_radius = (
                                ui.slider(
                                    min=1,
                                    max=20,
                                    step=1,
                                    value=3,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.glare_inpaint_radius,
                                "value",
                                lambda v: f"{int(float(v or 3))}px",
                            )

            # Action Toolbar
            with ui.row().classes(
                "w-full items-center justify-between mt-2 pt-2 border-t "
                "border-white/10"
            ):
                ui.button(
                    "Refresh Preview",
                    icon="tune",
                    on_click=self.do_adjust,
                ).props("unelevated").classes(
                    "bg-gradient-to-r from-blue-600 to-indigo-600 "
                    "hover:from-blue-500 hover:to-indigo-500 text-white shadow-md "
                    "transition-all font-medium"
                ).bind_enabled_from(
                    self, "image", lambda image: image != ""
                ).tooltip(
                    "Re-render adjustment parameters to the preview canvas"
                )

                ui.button(
                    "Reset to Original",
                    icon="restart_alt",
                    on_click=self._reset_image,
                ).props("outline").classes(
                    "text-slate-300 border-white/20 hover:bg-white/10 "
                    "transition-all font-medium"
                ).bind_enabled_from(
                    self, "image", lambda image: image != ""
                ).tooltip(
                    "Restore original unadjusted image"
                )

            super().add_navigator(stepper, first_step, last_step)
