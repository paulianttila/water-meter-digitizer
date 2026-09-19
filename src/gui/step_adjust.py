import asyncio
import logging
import os
from collections.abc import Callable

from nicegui import ui

import utils.image
from configuration import Config
from data_classes import RefImage
from processor.image import ImageProcessor

from .adjust import (
    build_filter_curves_card,
    build_glare_suppression_card,
    build_histogram_card,
    build_rotation_crop_card,
    build_unsharp_mask_card,
    generate_histogram_svg,
)
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

_generate_histogram_svg = generate_histogram_svg


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
        self._preview_task: asyncio.Task | None = None
        self._auto_enhance_task: asyncio.Task | None = None

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
                await self._async_update_preview_canvas()
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

    async def _async_update_preview_canvas(self) -> None:
        if not self.org_image:
            return

        try:
            adjusted_b64 = await asyncio.to_thread(self._do_adjust, self.org_image)
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

    def _update_preview_canvas(self) -> None:
        if not self.org_image:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            self._preview_task = asyncio.create_task(
                self._async_update_preview_canvas()
            )
        else:
            try:
                adjusted_b64 = self._do_adjust(self.org_image)
            except Exception as e:
                logger.warning(f"Error adjusting image preview: {e}")
                adjusted_b64 = self.org_image

            self.image = adjusted_b64

            compare = (
                self.compare_mode.value if hasattr(self, "compare_mode") else "Single"
            )
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
        await self._async_update_preview_canvas()

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
        if (
            hasattr(self, "autocontrast_enabled")
            and self.autocontrast_enabled is not None
        ):
            self.autocontrast_enabled.value = (
                config.image_processing.autocontrast.enabled
            )
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

    async def _async_apply_auto_enhance(self) -> None:
        if not self.org_image:
            return
        try:
            raw_img = (
                ImageProcessor().set_image_from_base64_str(self.org_image).get_image()
            )
            if raw_img is None:
                return
            res = await asyncio.to_thread(utils.image.auto_tune_image, raw_img)
            self._set_auto_enhance_values(res)
        except Exception as e:
            logger.warning(f"Auto-enhance failed: {e}")

    def _set_auto_enhance_values(self, res: dict) -> None:
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

    def _apply_auto_enhance(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            self._auto_enhance_task = asyncio.create_task(
                self._async_apply_auto_enhance()
            )
        else:
            if not self.org_image:
                return
            try:
                raw_img = (
                    ImageProcessor()
                    .set_image_from_base64_str(self.org_image)
                    .get_image()
                )
                if raw_img is None:
                    return
                res = utils.image.auto_tune_image(raw_img)
                self._set_auto_enhance_values(res)
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
                    if hasattr(self, "sharpness_mode")
                    and self.sharpness_mode is not None
                    else "standard"
                )
                if smode in ("unsharp_mask", "auto"):
                    u_radius = (
                        float(self.unsharp_radius.value or 1.0)
                        if hasattr(self, "unsharp_radius")
                        and self.unsharp_radius is not None
                        else 1.0
                    )
                    u_amount = (
                        float(self.unsharp_amount.value or 1.5)
                        if hasattr(self, "unsharp_amount")
                        and self.unsharp_amount is not None
                        else 1.5
                    )
                    u_thresh = (
                        int(self.unsharp_threshold.value or 3)
                        if hasattr(self, "unsharp_threshold")
                        and self.unsharp_threshold is not None
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
                    self.histogram_container.content = _generate_histogram_svg(
                        hist_data
                    )
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
                "w-full p-2.5 mb-1.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 backdrop-blur-md gap-1.5"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between flex-wrap gap-2"
                ):
                    with ui.row().classes("items-center gap-3"):
                        self.live_preview = (
                            ui.checkbox(
                                "Live Preview",
                                value=True,
                                on_change=self._on_param_change,
                            )
                            .props("dense")
                            .classes("text-indigo-200 text-sm font-semibold")
                        )
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
                        ).tooltip(
                            "Automatically analyze image and calculate optimal gamma, contrast, brightness, and sharpness"
                        )

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

                with ui.row().classes(
                    "w-full items-center gap-2 pt-1 border-t border-indigo-500/20 flex-wrap"
                ):
                    ui.label("Presets:").classes(
                        "text-xs text-indigo-300/80 font-medium"
                    )
                    ui.button(
                        "Crisp Text",
                        icon="text_fields",
                        on_click=lambda: self._apply_preset("crisp"),
                    ).props("flat dense").classes(
                        "text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2"
                    )
                    ui.button(
                        "Basement / Dim",
                        icon="wb_twilight",
                        on_click=lambda: self._apply_preset("basement"),
                    ).props("flat dense").classes(
                        "text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2"
                    )
                    ui.button(
                        "Reflective Glass",
                        icon="flare",
                        on_click=lambda: self._apply_preset("reflective"),
                    ).props("flat dense").classes(
                        "text-xs text-slate-300 hover:text-white hover:bg-white/10 px-2"
                    )
                    ui.button(
                        "Reset Defaults",
                        icon="replay",
                        on_click=lambda: self._apply_preset("default"),
                    ).props("flat dense").classes(
                        "text-xs text-slate-400 hover:text-slate-200 hover:bg-white/10 px-2"
                    )

            with ui.column().classes("w-full gap-2.5 my-1.5"):
                # Image Processing Master Card
                with ui.row().classes(
                    "w-full items-center justify-between p-2.5 rounded-xl "
                    "bg-slate-900/80 border border-white/10 shadow-md gap-2.5"
                ):
                    with ui.row().classes("items-center gap-2.5"):
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
                        .props("dense color=cyan")
                        .tooltip(
                            "Enable or disable all image processing enhancements ([ImageProcessing] section)"
                        )
                    )

                # Sub-cards
                build_rotation_crop_card(self, ui)
                build_filter_curves_card(self, ui)
                build_unsharp_mask_card(self, ui)
                build_histogram_card(self, ui)
                build_glare_suppression_card(self, ui)

            # Action Toolbar
            with ui.row().classes(
                "w-full items-center justify-between mt-1.5 pt-1.5 border-t "
                "border-white/10"
            ):
                ui.button(
                    "Refresh Preview",
                    icon="tune",
                    on_click=self.do_adjust,
                ).props("unelevated dense").classes(
                    "bg-gradient-to-r from-blue-600 to-indigo-600 "
                    "hover:from-blue-500 hover:to-indigo-500 text-white shadow-md "
                    "transition-all font-medium px-3"
                ).bind_enabled_from(
                    self, "image", lambda image: image != ""
                ).tooltip(
                    "Re-render adjustment parameters to the preview canvas"
                )

                ui.button(
                    "Reset to Original",
                    icon="restart_alt",
                    on_click=self._reset_image,
                ).props("outline dense").classes(
                    "text-slate-300 border-white/20 hover:bg-white/10 "
                    "transition-all font-medium px-3"
                ).bind_enabled_from(
                    self, "image", lambda image: image != ""
                ).tooltip(
                    "Restore original unadjusted image"
                )

            super().add_navigator(stepper, first_step, last_step)
