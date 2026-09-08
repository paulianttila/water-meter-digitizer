from typing import Callable

from nicegui import ui

from configuration import Config
from data_classes import RefImage
from processor.image import ImageProcessor
from .step_base import BaseStep

HELP_TEXT = (
    "- **Fine Rotation**: Adjust small fractional angles (e.g. `0.5°`).\n"
    "- **Crop & Resize**: Optionally crop and resize before alignment.\n"
    "- **Image Filters**: Tune contrast, brightness, sharpness, grayscale, "
    "and autocontrast.\n"
    "- Click the adjust button at the bottom to preview."
)


class AdjustStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )
        self.rotate_angle: ui.number
        self.org_image: str = ""
        self.ref_images: list[RefImage] = []

    def update_image(self, image: str) -> None:
        self.org_image = image
        self.image = self._do_adjust(image)

    def _reset_image(self) -> None:
        if self.org_image != "":
            self.image = self.org_image
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

    @BaseStep.decorator_spinner
    @BaseStep.decorator_catch_err
    async def do_adjust(self) -> None:
        self._reset_image()
        self.image = self._do_adjust(self.image)
        if self.set_image_callback is not None:
            self.set_image_callback(self.image)

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
        ref_images = [
            r for r in getattr(self, "ref_images", []) if getattr(r, "file_name", "")
        ]
        return (
            ImageProcessor()
            .set_image_from_base64_str(image)
            .if_(len(ref_images) > 0)
            .align_image(ref_images)
            .endif_()
            .if_(self.rotate_enabled.value)
            .rotate_image(self.rotate_angle.value)
            .endif_()
            .if_(self.crop_enabled.value)
            .crop_image(
                x=self.crop_x.value,
                y=self.crop_y.value,
                w=self.crop_w.value,
                h=self.crop_h.value,
            )
            .endif_()
            .if_(self.resize_enabled.value)
            .resize_image(
                width=int(self.resize_w.value),
                height=int(self.resize_h.value),
            )
            .endif_()
            .if_(self.adjust_enabled.value)
            .adjust_image(
                contrast=self.adjust_contrast.value,
                brightness=self.adjust_brightness.value,
                sharpness=self.adjust_sharpness.value,
                color=self.adjust_color.value,
            )
            .endif_()
            .if_(self.grayscale_enabled.value)
            .to_gray_scale()
            .endif_()
            .if_(self.autocontrast_enabled.value)
            .autocontrast_image(
                cutoff_low=self.autocontrast_cutoff_low.value,
                cutoff_high=self.autocontrast_cutoff_high.value,
            )
            .endif_()
            .if_(self.glare_enabled.value)
            .suppress_glare(
                mode=self.glare_mode.value,
                inpaint_threshold=int(self.glare_inpaint_threshold.value or 230),
                inpaint_radius=int(self.glare_inpaint_radius.value or 3),
                clahe_clip_limit=float(self.glare_clahe_clip_limit.value or 2.0),
                clahe_grid_size=int(self.glare_clahe_grid_size.value or 8),
            )
            .endif_()
            .get_image_as_base64_str()
        )

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            with ui.column().classes("w-full gap-3 my-2"):
                # Geometry & Cropping Expansion
                with ui.expansion(
                    "Geometry & Cropping", icon="crop", value=True
                ).classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "shadow-md overflow-hidden"
                ):
                    with ui.column().classes("w-full gap-3 p-3"):
                        with ui.row().classes("w-full items-center gap-4"):
                            self.rotate_enabled = ui.checkbox(
                                "Enable Rotation", value=False
                            ).tooltip("Enable fine rotation angle correction")
                            self.rotate_angle = (
                                ui.number(
                                    "Angle (°)", min=-359, max=359, step=1, value=0
                                )
                                .classes("w-28")
                                .tooltip(
                                    "Fine rotation angle in degrees (-359° to 359°)"
                                )
                            )

                        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                            self.crop_enabled = ui.checkbox(
                                "Enable Crop", value=False
                            ).tooltip("Enable rectangular cropping before alignment")
                            self.crop_x = (
                                ui.number("X", min=0, max=10000, step=1, value=0)
                                .classes("w-20")
                                .tooltip("Crop starting X position in pixels")
                            )
                            self.crop_y = (
                                ui.number("Y", min=0, max=10000, step=1, value=0)
                                .classes("w-20")
                                .tooltip("Crop starting Y position in pixels")
                            )
                            self.crop_w = (
                                ui.number("Width", min=640, max=10000, step=1, value=0)
                                .classes("w-24")
                                .tooltip("Crop area width in pixels")
                            )
                            self.crop_h = (
                                ui.number("Height", min=480, max=10000, step=1, value=0)
                                .classes("w-24")
                                .tooltip("Crop area height in pixels")
                            )

                        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                            self.resize_enabled = ui.checkbox(
                                "Enable Resize", value=False
                            ).tooltip("Enable image resizing")
                            self.resize_w = (
                                ui.number("Width", min=0, max=10000, step=1, value=0)
                                .classes("w-24")
                                .tooltip("Resized image width in pixels")
                            )
                            self.resize_h = (
                                ui.number("Height", min=0, max=10000, step=1, value=0)
                                .classes("w-24")
                                .tooltip("Resized image height in pixels")
                            )

                # Tonal & Color Adjustments Expansion
                with ui.expansion(
                    "Tonal & Color Adjustments", icon="palette", value=False
                ).classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "shadow-md overflow-hidden"
                ):
                    with ui.column().classes("w-full gap-3 p-3"):
                        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                            self.adjust_enabled = ui.checkbox(
                                "Enable Filters", value=False
                            ).tooltip(
                                "Enable color, brightness, contrast, and "
                                "sharpness adjustments"
                            )
                            self.grayscale_enabled = ui.checkbox(
                                "Grayscale", value=False
                            ).tooltip("Convert the full image to grayscale")

                        with ui.grid(
                            columns="repeat(auto-fit, minmax(110px, 1fr))"
                        ).classes("w-full gap-3"):
                            self.adjust_contrast = ui.number(
                                "Contrast", min=0, max=10, step=0.1, value=1.0
                            ).tooltip("Contrast adjustment factor (1.0 = normal)")
                            self.adjust_brightness = ui.number(
                                "Brightness", min=0, max=10, step=0.1, value=1.0
                            ).tooltip("Brightness adjustment factor (1.0 = normal)")
                            self.adjust_sharpness = ui.number(
                                "Sharpness", min=0, max=10, step=0.1, value=1.0
                            ).tooltip("Sharpness adjustment factor (1.0 = normal)")
                            self.adjust_color = ui.number(
                                "Color", min=0, max=10, step=0.1, value=1.0
                            ).tooltip(
                                "Color saturation factor "
                                "(1.0 = normal, 0.0 = grayscale)"
                            )

                # Histogram & AutoContrast Expansion
                with ui.expansion(
                    "Histogram & AutoContrast", icon="auto_fix_high", value=False
                ).classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "shadow-md overflow-hidden"
                ):
                    with ui.column().classes("w-full gap-3 p-3"):
                        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                            self.autocontrast_enabled = ui.checkbox(
                                "Full Frame AutoContrast", value=False
                            ).tooltip(
                                "Automatically optimize contrast histogram for "
                                "full frame"
                            )
                            self.autocontrast_cutoff_low = (
                                ui.number(
                                    "Cutoff Low (%)", min=0, max=100, step=1, value=2
                                )
                                .classes("w-28")
                                .tooltip(
                                    "Percentage of darkest pixels removed before "
                                    "mapping (0–100%)"
                                )
                            )
                            self.autocontrast_cutoff_high = (
                                ui.number(
                                    "Cutoff High (%)", min=0, max=100, step=1, value=45
                                )
                                .classes("w-28")
                                .tooltip(
                                    "Percentage of brightest pixels removed before "
                                    "mapping (0–100%)"
                                )
                            )

                        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                            self.autocontrast_cut_images_enabled = ui.checkbox(
                                "Cut Images (ROIs) AutoContrast", value=False
                            ).tooltip(
                                "Apply automatic contrast stretching individually on "
                                "cropped digit/pointer ROI images"
                            )
                            self.autocontrast_cut_images_cutoff_low = (
                                ui.number(
                                    "Cutoff Low (%)", min=0, max=100, step=1, value=2
                                )
                                .classes("w-28")
                                .tooltip(
                                    "Low cutoff percentage for cropped ROI contrast "
                                    "stretching"
                                )
                            )
                            self.autocontrast_cut_images_cutoff_high = (
                                ui.number(
                                    "Cutoff High (%)", min=0, max=100, step=1, value=45
                                )
                                .classes("w-28")
                                .tooltip(
                                    "High cutoff percentage for cropped ROI contrast "
                                    "stretching"
                                )
                            )

                # Glare Suppression Expansion
                with ui.expansion(
                    "Glare & Specular Reflection Suppression",
                    icon="flare",
                    value=False,
                ).classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "shadow-md overflow-hidden"
                ):
                    with ui.column().classes("w-full gap-3 p-3"):
                        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                            self.glare_enabled = ui.checkbox(
                                "Enable Glare Suppression", value=False
                            ).tooltip(
                                "Suppress specular highlights on glossy meter glass"
                            )
                            self.glare_apply_to_cut_images = ui.checkbox(
                                "Apply to Cut Images (ROIs)", value=False
                            ).tooltip(
                                "Apply glare suppression to cropped digit/pointer "
                                "images"
                            )

                        with ui.grid(
                            columns="repeat(auto-fit, minmax(130px, 1fr))"
                        ).classes("w-full gap-3"):
                            self.glare_mode = ui.select(
                                [
                                    "clahe",
                                    "inpaint",
                                    "illumination_normalize",
                                    "combined",
                                ],
                                label="Mode",
                                value="clahe",
                            ).tooltip(
                                "Filter mode: clahe, inpaint, illumination_normalize, "
                                "or combined"
                            )
                            self.glare_inpaint_threshold = ui.number(
                                "Inpaint Threshold", min=100, max=255, step=1, value=230
                            ).tooltip(
                                "Luminance threshold (0–255) to detect "
                                "specular hotspots"
                            )
                            self.glare_inpaint_radius = ui.number(
                                "Inpaint Radius", min=1, max=20, step=1, value=3
                            ).tooltip(
                                "Radius in pixels for Telea inpainting around "
                                "glare mask"
                            )
                            self.glare_clahe_clip_limit = ui.number(
                                "CLAHE Clip Limit",
                                min=0.1,
                                max=10.0,
                                step=0.5,
                                value=2.0,
                            ).tooltip("Threshold for contrast limiting in CLAHE")
                            self.glare_clahe_grid_size = ui.number(
                                "CLAHE Grid Size", min=2, max=32, step=1, value=8
                            ).tooltip("Tile grid size for CLAHE (e.g. 8 for 8x8)")

            # Preview & Reset Action Toolbar
            with ui.row().classes(
                "w-full items-center justify-between mt-2 pt-2 border-t "
                "border-white/10"
            ):
                ui.button(
                    "Preview Adjustments",
                    icon="tune",
                    on_click=self.do_adjust,
                ).props("unelevated").classes(
                    "bg-gradient-to-r from-blue-600 to-indigo-600 "
                    "hover:from-blue-500 hover:to-indigo-500 text-white shadow-md "
                    "transition-all font-medium"
                ).bind_enabled_from(
                    self, "image", lambda image: image != ""
                ).tooltip(
                    "Apply all current adjustment parameters to the preview canvas"
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
