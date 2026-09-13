import asyncio
import logging
import os
from collections.abc import Callable

from nicegui import ui

import utils.image
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
    "- **Auto Enhance & Presets**: One-click optimal parameter calculation and environment presets.\n"
    "- **Fine Rotation**: Correct fractional angles (e.g. `0.5°`).\n"
    "- **Crop & Resize**: Optionally crop and resize frame before alignment.\n"
    "- **Image Processing**: Master toggle to enable/disable all image processing enhancements.\n"
    "- **Tonal & Gamma Curves**: Non-linear gamma adjustment and contrast/brightness/saturation.\n"
    "- **Luminance Unsharp Masking**: Advanced spatial edge sharpening without chromatic noise.\n"
    "- **Histogram & AutoContrast**: Real-time luminance histogram with shadow/highlight clipping flags.\n"
    "- **Glare Suppression**: Eliminate glass reflections using CLAHE, inpainting, "
    "or combined mode."
)

BADGE_CLASSES = "w-14 text-right text-xs font-mono font-bold text-cyan-400 shrink-0"


def _generate_histogram_svg(hist_data: dict) -> str:
    """Generate lightweight inline SVG area chart for 256-bin luminance histogram."""
    luma = hist_data.get("luminance", [0] * 256)
    if not luma or len(luma) < 256:
        luma = [0] * 256
    max_val = max(1, max(luma[1:255] if len(luma) > 2 else luma))

    points = []
    for i, val in enumerate(luma):
        h = min(60, int((val / max_val) * 54))
        y = 60 - h
        points.append(f"{i},{y}")

    polyline = " ".join(points)
    polygon = f"0,60 {polyline} 255,60"

    return f"""
    <div style="width:100%; height:75px; background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:6px; position:relative; overflow:hidden;">
        <svg viewBox="0 0 256 60" preserveAspectRatio="none" style="width:100%; height:100%;">
            <defs>
                <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85"/>
                    <stop offset="100%" stop-color="#0284c7" stop-opacity="0.10"/>
                </linearGradient>
            </defs>
            <polygon points="{polygon}" fill="url(#histGrad)" />
            <polyline points="{polyline}" fill="none" stroke="#38bdf8" stroke-width="1.2" />
        </svg>
    </div>
    """


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
        self.adjust_gamma: ui.slider
        self.adjust_contrast: ui.slider
        self.adjust_brightness: ui.slider
        self.adjust_sharpness: ui.slider
        self.adjust_color: ui.slider

        # Advanced Unsharp Masking & Auto-Sharpness
        self.sharpness_mode: ui.select
        self.unsharp_amount: ui.slider
        self.unsharp_radius: ui.slider
        self.unsharp_threshold: ui.slider
        self.auto_sharpen_cut_images: ui.checkbox
        self.focus_score_badge: ui.label | None = None

        # Histogram & AutoContrast
        self.histogram_container: ui.html | None = None
        self.shadow_clip_badge: ui.label | None = None
        self.highlight_clip_badge: ui.label | None = None
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
        if hasattr(self, "adjust_enabled") and self.adjust_enabled is not None:
            self.adjust_enabled.value = config.image_processing.enabled
        if hasattr(self, "adjust_gamma") and self.adjust_gamma is not None:
            self.adjust_gamma.value = config.image_processing.gamma
        if hasattr(self, "adjust_contrast") and self.adjust_contrast is not None:
            self.adjust_contrast.value = config.image_processing.contrast
        if hasattr(self, "adjust_brightness") and self.adjust_brightness is not None:
            self.adjust_brightness.value = config.image_processing.brightness
        if hasattr(self, "adjust_sharpness") and self.adjust_sharpness is not None:
            self.adjust_sharpness.value = config.image_processing.sharpness
        if hasattr(self, "adjust_color") and self.adjust_color is not None:
            self.adjust_color.value = config.image_processing.color
        if hasattr(self, "grayscale_enabled") and self.grayscale_enabled is not None:
            self.grayscale_enabled.value = config.image_processing.grayscale

        # Advanced Unsharp Masking & Auto-Sharpness
        if hasattr(self, "sharpness_mode") and self.sharpness_mode is not None:
            self.sharpness_mode.value = config.image_processing.sharpness_mode
        if hasattr(self, "unsharp_radius") and self.unsharp_radius is not None:
            self.unsharp_radius.value = config.image_processing.unsharp_radius
        if hasattr(self, "unsharp_amount") and self.unsharp_amount is not None:
            self.unsharp_amount.value = config.image_processing.unsharp_amount
        if hasattr(self, "unsharp_threshold") and self.unsharp_threshold is not None:
            self.unsharp_threshold.value = config.image_processing.unsharp_threshold
        if (
            hasattr(self, "auto_sharpen_cut_images")
            and self.auto_sharpen_cut_images is not None
        ):
            self.auto_sharpen_cut_images.value = (
                config.image_processing.auto_sharpen_cut_images
            )

        # AutoContrast
        if hasattr(self, "autocontrast_enabled") and self.autocontrast_enabled is not None:
            self.autocontrast_enabled.value = config.image_processing.autocontrast.enabled
        if (
            hasattr(self, "autocontrast_cutoff_low")
            and self.autocontrast_cutoff_low is not None
        ):
            self.autocontrast_cutoff_low.value = (
                config.image_processing.autocontrast.cutoff_low
            )
        if (
            hasattr(self, "autocontrast_cutoff_high")
            and self.autocontrast_cutoff_high is not None
        ):
            self.autocontrast_cutoff_high.value = (
                config.image_processing.autocontrast.cutoff_high
            )
        if (
            hasattr(self, "autocontrast_cut_images_enabled")
            and self.autocontrast_cut_images_enabled is not None
        ):
            self.autocontrast_cut_images_enabled.value = (
                config.image_processing.autocontrast_cut_images.enabled
            )
        if (
            hasattr(self, "autocontrast_cut_images_cutoff_low")
            and self.autocontrast_cut_images_cutoff_low is not None
        ):
            self.autocontrast_cut_images_cutoff_low.value = (
                config.image_processing.autocontrast_cut_images.cutoff_low
            )
        if (
            hasattr(self, "autocontrast_cut_images_cutoff_high")
            and self.autocontrast_cut_images_cutoff_high is not None
        ):
            self.autocontrast_cut_images_cutoff_high.value = (
                config.image_processing.autocontrast_cut_images.cutoff_high
            )

        # Glare Suppression
        if hasattr(self, "glare_enabled") and self.glare_enabled is not None:
            self.glare_enabled.value = config.image_processing.glare_suppression.enabled
        if hasattr(self, "glare_mode") and self.glare_mode is not None:
            self.glare_mode.value = config.image_processing.glare_suppression.mode
        if (
            hasattr(self, "glare_inpaint_threshold")
            and self.glare_inpaint_threshold is not None
        ):
            self.glare_inpaint_threshold.value = (
                config.image_processing.glare_suppression.inpaint_threshold
            )
        if (
            hasattr(self, "glare_inpaint_radius")
            and self.glare_inpaint_radius is not None
        ):
            self.glare_inpaint_radius.value = (
                config.image_processing.glare_suppression.inpaint_radius
            )
        if (
            hasattr(self, "glare_clahe_clip_limit")
            and self.glare_clahe_clip_limit is not None
        ):
            self.glare_clahe_clip_limit.value = (
                config.image_processing.glare_suppression.clahe_clip_limit
            )
        if (
            hasattr(self, "glare_clahe_grid_size")
            and self.glare_clahe_grid_size is not None
        ):
            self.glare_clahe_grid_size.value = (
                config.image_processing.glare_suppression.clahe_grid_size
            )
        if (
            hasattr(self, "glare_apply_to_cut_images")
            and self.glare_apply_to_cut_images is not None
        ):
            self.glare_apply_to_cut_images.value = (
                config.image_processing.glare_suppression.apply_to_cut_images
            )

        # Alignment
        self.ref_images = list(config.alignment.ref_images)

        # Rotation
        self.rotate_angle.value = config.alignment.post_rotate_angle
        self.rotate_enabled.value = config.alignment.post_rotate_angle != 0

    def _apply_auto_enhance(self) -> None:
        if not self.org_image:
            return
        try:
            raw_img = ImageProcessor().set_image_from_base64_str(self.org_image).get_image()
            if raw_img is None:
                return
            res = utils.image.auto_tune_image(raw_img)
            self.adjust_enabled.value = True
            if hasattr(self, "adjust_gamma") and self.adjust_gamma is not None:
                self.adjust_gamma.value = float(res["gamma"])
            if hasattr(self, "adjust_contrast") and self.adjust_contrast is not None:
                self.adjust_contrast.value = float(res["contrast"])
            if hasattr(self, "adjust_brightness") and self.adjust_brightness is not None:
                self.adjust_brightness.value = float(res["brightness"])
            if hasattr(self, "sharpness_mode") and self.sharpness_mode is not None:
                self.sharpness_mode.value = "unsharp_mask"
            if hasattr(self, "unsharp_amount") and self.unsharp_amount is not None:
                self.unsharp_amount.value = float(res["unsharp_amount"])
            if hasattr(self, "unsharp_radius") and self.unsharp_radius is not None:
                self.unsharp_radius.value = float(res["unsharp_radius"])
            if hasattr(self, "unsharp_threshold") and self.unsharp_threshold is not None:
                self.unsharp_threshold.value = int(res["unsharp_threshold"])
            self._on_param_change()
            ui.notify(
                f"⚡ Auto-enhanced! Focus score: {float(res['focus_score']):.1f}",
                type="positive",
            )
        except Exception as e:
            logger.warning(f"Auto-enhance failed: {e}")

    def _apply_preset(self, preset_name: str) -> None:
        if preset_name == "default":
            self.adjust_gamma.value = 1.0
            self.adjust_contrast.value = 1.0
            self.adjust_brightness.value = 1.0
            self.adjust_sharpness.value = 1.0
            self.adjust_color.value = 1.0
            self.grayscale_enabled.value = False
            self.sharpness_mode.value = "standard"
            self.unsharp_amount.value = 1.5
            self.unsharp_radius.value = 1.0
            self.unsharp_threshold.value = 3
            self.autocontrast_enabled.value = False
            self.glare_enabled.value = False
        elif preset_name == "crisp":
            self.adjust_enabled.value = True
            self.adjust_gamma.value = 1.0
            self.adjust_contrast.value = 1.15
            self.adjust_brightness.value = 1.0
            self.sharpness_mode.value = "unsharp_mask"
            self.unsharp_amount.value = 1.6
            self.unsharp_radius.value = 1.0
            self.unsharp_threshold.value = 3
        elif preset_name == "basement":
            self.adjust_enabled.value = True
            self.adjust_gamma.value = 0.75
            self.adjust_contrast.value = 1.15
            self.adjust_brightness.value = 1.15
            self.sharpness_mode.value = "unsharp_mask"
            self.unsharp_amount.value = 1.8
            self.unsharp_radius.value = 1.2
            self.unsharp_threshold.value = 2
        elif preset_name == "reflective":
            self.adjust_enabled.value = True
            self.adjust_gamma.value = 1.1
            self.adjust_contrast.value = 1.2
            self.glare_enabled.value = True
            self.glare_mode.value = "clahe"
            self.glare_clahe_clip_limit.value = 2.5
            self.sharpness_mode.value = "unsharp_mask"
            self.unsharp_amount.value = 1.4
        self._on_param_change()
        ui.notify(f"Applied preset: {preset_name.title()}", type="info")

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
                gamma_val = (
                    float(self.adjust_gamma.value or 1.0)
                    if hasattr(self, "adjust_gamma") and self.adjust_gamma is not None
                    else 1.0
                )
                proc.adjust_image(
                    contrast=float(self.adjust_contrast.value or 1.0),
                    brightness=float(self.adjust_brightness.value or 1.0),
                    sharpness=float(self.adjust_sharpness.value or 1.0),
                    color=float(self.adjust_color.value or 1.0),
                    gamma=gamma_val,
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

            try:
                smode = (
                    str(self.sharpness_mode.value or "standard")
                    if hasattr(self, "sharpness_mode") and self.sharpness_mode is not None
                    else "standard"
                )
                if smode in ("unsharp_mask", "auto"):
                    u_radius = (
                        float(self.unsharp_radius.value or 1.0)
                        if hasattr(self, "unsharp_radius") and self.unsharp_radius is not None
                        else 1.0
                    )
                    u_amount = (
                        float(self.unsharp_amount.value or 1.5)
                        if hasattr(self, "unsharp_amount") and self.unsharp_amount is not None
                        else 1.5
                    )
                    u_thresh = (
                        int(self.unsharp_threshold.value or 3)
                        if hasattr(self, "unsharp_threshold") and self.unsharp_threshold is not None
                        else 3
                    )
                    proc.unsharp_mask(
                        radius=u_radius,
                        amount=u_amount,
                        threshold=u_thresh,
                    )
            except Exception as e:
                logger.debug(f"Unsharp mask adjustment skipped: {e}")

        # Update real-time histogram & focus score metrics
        try:
            cur_img = proc.get_image()
            if cur_img is not None:
                hist_data = utils.image.calculate_histogram(cur_img)
                f_score = utils.image.calculate_focus_score(cur_img)
                if (
                    hasattr(self, "focus_score_badge")
                    and self.focus_score_badge is not None
                ):
                    status_text = (
                        "Sharp"
                        if f_score >= 300
                        else ("Moderate" if f_score >= 100 else "Soft / Blurry")
                    )
                    self.focus_score_badge.text = f"{f_score:.1f} ({status_text})"
                if (
                    hasattr(self, "histogram_container")
                    and self.histogram_container is not None
                ):
                    self.histogram_container.content = _generate_histogram_svg(hist_data)
                if (
                    hasattr(self, "shadow_clip_badge")
                    and self.shadow_clip_badge is not None
                ):
                    self.shadow_clip_badge.text = (
                        f"Shadows: {hist_data['shadow_clip_pct']:.1f}%"
                    )
                if (
                    hasattr(self, "highlight_clip_badge")
                    and self.highlight_clip_badge is not None
                ):
                    self.highlight_clip_badge.text = (
                        f"Highlights: {hist_data['highlight_clip_pct']:.1f}%"
                    )
        except Exception as e:
            logger.debug(f"Histogram/focus calculation skipped: {e}")

        return proc.get_image_as_base64_str()

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            # Live Preview, Presets & Quick Actions Toolbar
            with ui.column().classes(
                "w-full p-3 mb-2 rounded-xl bg-indigo-950/40 border border-indigo-500/30 backdrop-blur-md gap-2"
            ):
                with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
                    with ui.row().classes("items-center gap-3"):
                        self.live_preview = ui.checkbox(
                            "Live Preview", value=True, on_change=self._on_param_change
                        ).classes("text-indigo-200 text-sm font-semibold")
                        ui.label("•").classes("text-indigo-400/50")
                        ui.label("View:").classes("text-xs text-slate-400 font-medium")
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
                            "⚡ Auto Enhance",
                            icon="auto_awesome",
                            on_click=self._apply_auto_enhance,
                        ).props("unelevated dense").classes(
                            "text-xs bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-bold px-3 py-1 rounded-lg shadow-sm"
                        ).tooltip("Automatically analyze image and calculate optimal gamma, contrast, brightness, and sharpness")

                        ui.button(
                            "Hold for Original",
                            icon="visibility",
                        ).props("outline dense").classes(
                            "text-xs border-indigo-400/40 text-indigo-300 hover:bg-indigo-500/20 px-2 py-1"
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

                with ui.row().classes("w-full items-center gap-2 pt-1 border-t border-indigo-500/20 flex-wrap"):
                    ui.label("Presets:").classes("text-xs text-indigo-300/80 font-medium")
                    ui.button(
                        "Crisp Text",
                        icon="text_fields",
                        on_click=lambda: self._apply_preset("crisp"),
                    ).props("flat dense").classes("text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2")
                    ui.button(
                        "Basement / Dim",
                        icon="wb_twilight",
                        on_click=lambda: self._apply_preset("basement"),
                    ).props("flat dense").classes("text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2")
                    ui.button(
                        "Reflective Glass",
                        icon="flare",
                        on_click=lambda: self._apply_preset("reflective"),
                    ).props("flat dense").classes("text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2")
                    ui.button(
                        "Reset Defaults",
                        icon="replay",
                        on_click=lambda: self._apply_preset("default"),
                    ).props("flat dense").classes("text-xs text-slate-400 hover:text-slate-200 hover:bg-white/10 px-2")

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
                                "Master toggle for filters, gamma, sharpness, autocontrast, and glare suppression"
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
                        # Gamma Slider
                        with ui.row().classes("w-full items-center gap-3 py-1"):
                            ui.label("Gamma").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.adjust_gamma = (
                                ui.slider(
                                    min=0.2,
                                    max=3.0,
                                    step=0.05,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.adjust_gamma,
                                "value",
                                lambda v: f"{float(v or 1.0):.2f}",
                            )

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

                # Sharpness & Edge Enhancement Expansion
                with (
                    ui.expansion(
                        "Sharpness & Edge Enhancement", icon="details", value=False
                    ).classes(
                        "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                        "shadow-md overflow-hidden"
                    ),
                    ui.column().classes("w-full gap-3 p-3"),
                ):
                    with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
                        self.sharpness_mode = (
                            ui.select(
                                {
                                    "unsharp_mask": "Luminance Unsharp Mask (Pro)",
                                    "auto": "Adaptive Auto-Sharpness",
                                    "standard": "Standard Sharpness Filter",
                                },
                                label="Sharpness Algorithm",
                                value="unsharp_mask",
                                on_change=self._on_param_change,
                            )
                            .classes("w-64")
                            .tooltip("Algorithm used for spatial digit edge enhancement")
                        )

                        with ui.row().classes("items-center gap-2"):
                            ui.label("Focus Metric:").classes("text-xs text-slate-400 font-medium")
                            self.focus_score_badge = ui.label("Calculating...").classes(
                                "text-xs font-mono font-bold px-2 py-1 rounded bg-slate-800 border border-white/10 text-emerald-400"
                            )

                    with ui.column().classes("w-full gap-4"):
                        # Standard Sharpness (visible when standard is selected)
                        with ui.row().classes("w-full items-center gap-3 py-1").bind_visibility_from(
                            self.sharpness_mode, "value", lambda v: v == "standard"
                        ):
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

                        # Unsharp Mask Amount
                        with ui.row().classes("w-full items-center gap-3 py-1").bind_visibility_from(
                            self.sharpness_mode, "value", lambda v: v in ("unsharp_mask", "auto")
                        ):
                            ui.label("Amount (Strength)").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.unsharp_amount = (
                                ui.slider(
                                    min=0.0,
                                    max=4.0,
                                    step=0.1,
                                    value=1.5,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.unsharp_amount,
                                "value",
                                lambda v: f"{float(v or 1.5):.2f}x",
                            )

                        # Unsharp Mask Radius
                        with ui.row().classes("w-full items-center gap-3 py-1").bind_visibility_from(
                            self.sharpness_mode, "value", lambda v: v in ("unsharp_mask", "auto")
                        ):
                            ui.label("Radius (px)").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.unsharp_radius = (
                                ui.slider(
                                    min=0.5,
                                    max=5.0,
                                    step=0.1,
                                    value=1.0,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.unsharp_radius,
                                "value",
                                lambda v: f"{float(v or 1.0):.1f}px",
                            )

                        # Unsharp Mask Threshold
                        with ui.row().classes("w-full items-center gap-3 py-1").bind_visibility_from(
                            self.sharpness_mode, "value", lambda v: v in ("unsharp_mask", "auto")
                        ):
                            ui.label("Noise Threshold").classes(
                                "w-24 text-xs font-semibold text-slate-300"
                            )
                            self.unsharp_threshold = (
                                ui.slider(
                                    min=0,
                                    max=20,
                                    step=1,
                                    value=3,
                                    on_change=self._on_param_change,
                                )
                                .classes("flex-1")
                                .props("label")
                            )
                            ui.label().classes(BADGE_CLASSES).bind_text_from(
                                self.unsharp_threshold,
                                "value",
                                lambda v: f"{int(float(v or 3))}",
                            )

                    self.auto_sharpen_cut_images = ui.checkbox(
                        "Sharpen Cut Images (ROIs) Individually",
                        value=False,
                        on_change=self._on_param_change,
                    ).tooltip("Apply luminance unsharp masking to cropped digit and pointer images before neural inference")

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
                    # Live Histogram Area
                    with ui.column().classes("w-full gap-1 p-2 rounded-lg bg-slate-950/60 border border-white/5"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("Luminance Distribution (Rec.709)").classes("text-xs font-semibold text-slate-400")
                            with ui.row().classes("gap-2 items-center"):
                                self.shadow_clip_badge = ui.label("Shadows: 0.0%").classes("text-[11px] font-mono text-cyan-400")
                                self.highlight_clip_badge = ui.label("Highlights: 0.0%").classes("text-[11px] font-mono text-amber-400")

                        self.histogram_container = ui.html(_generate_histogram_svg({})).classes("w-full")

                    self.autocontrast_enabled = ui.checkbox(
                        "Full Frame AutoContrast",
                        value=False,
                        on_change=self._on_param_change,
                    ).tooltip(
                        "Automatically optimize contrast histogram for full frame"
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
