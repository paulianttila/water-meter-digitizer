import functools
import logging
from collections.abc import Callable, Sequence
from typing import Any

from PIL.Image import Image

import utils.download
import utils.image
from data_classes import CutImage, CutImageOptions, ImagePosition, RefImage

logger = logging.getLogger(__name__)


def _conditional_func(func) -> Callable[..., "ImageProcessor"]:
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.condition is not None and self.condition is False:
            return self

        func(self, *args, **kwargs)
        return self

    return wrapper


COLOR_ROI_REFS = (16, 185, 129)  # Emerald Green
COLOR_ROI_DIGITAL = (59, 130, 246)  # Electric Blue
COLOR_ROI_ANALOG = (245, 158, 11)  # Vivid Amber / Orange


class ImageProcessor:
    def __init__(self) -> None:
        self.condition: bool | None = None
        self.image: Image
        self.cut_images_list: list[CutImage] = []
        self.enable_img_saving = False
        self.pictures: dict[str, Image] = {}
        self.alignment_success: bool = True
        self.alignment_error: str = ""

    def if_(self, a) -> "ImageProcessor":
        self.condition = a
        return self

    def else_(self) -> "ImageProcessor":
        self.condition = self.condition is False
        return self

    def endif_(self) -> "ImageProcessor":
        self.condition = None
        return self

    @_conditional_func
    def enable_image_saving(self, state: bool = True) -> "ImageProcessor":
        self.enable_img_saving = state
        return self

    @_conditional_func
    def set_image(self, image: Image) -> "ImageProcessor":
        self.image = utils.image.convert_to_image(image)
        return self

    @_conditional_func
    def set_image_from_base64_str(self, image_as_str: str) -> "ImageProcessor":
        self.image = utils.image.convert_base64_str_to_image(image_as_str)
        return self

    def get_image(self) -> Image:
        return self.image

    def get_picture(self, name: str) -> Image:
        if name in self.pictures:
            return self.pictures[name]
        raise ValueError(f"No image with name {name} available")

    def get_pictures(self) -> dict[str, Image]:
        return self.pictures

    def get_image_as_base64_str(self) -> str:
        return utils.image.convert_image_base64str(image=self.image)

    @_conditional_func
    def save_image(self, name: str, force_save: bool = False) -> "ImageProcessor":
        if self.enable_img_saving or force_save:
            logger.debug("Store image by name %s", name)
            self.pictures[name] = self.image
        return self

    @_conditional_func
    def download_image(
        self,
        url: str,
        timeout: int,
        min_image_size: int = 0,
        allowed_directories: list[str] | tuple[str, ...] | None = None,
    ) -> "ImageProcessor":
        logger.debug("Download image from %s", url)
        data = utils.download.load_file_from_url(
            url=url,
            timeout=timeout,
            min_file_size=min_image_size,
            allowed_directories=allowed_directories,
        )
        self.image = utils.image.bytes_to_image(data)
        self.pictures.clear()
        return self

    @_conditional_func
    def rotate_image(self, angle: float) -> "ImageProcessor":
        logger.debug("Rotate image by %s degrees", angle)
        self.image = utils.image.rotate(self.image, angle, keep_org_size=False)
        return self

    @_conditional_func
    def crop_image(self, x: int, y: int, w: int, h: int) -> "ImageProcessor":
        logger.debug("Crop image to x:%s, y:%s, w:%s, h:%s", x, y, w, h)
        self.image = utils.image.crop_image(self.image, x, y, w, h)
        return self

    @_conditional_func
    def resize_image(self, width: int, height: int) -> "ImageProcessor":
        logger.debug("Resize image to width:%s, height:%s", width, height)
        self.image = utils.image.resize_image(self.image, width, height)
        return self

    @_conditional_func
    def adjust_image(
        self,
        contrast: float = 1.0,
        brightness: float = 1.0,
        sharpness: float = 1.0,
        color: float = 1.0,
        gamma: float = 1.0,
    ) -> "ImageProcessor":
        logger.debug(
            "Adjust image contrast:%s, brightness:%s, sharpness:%s, color:%s, gamma:%s",
            contrast,
            brightness,
            sharpness,
            color,
            gamma,
        )
        self.image = utils.image.adjust_image(
            self.image,
            contrast=contrast,
            brightness=brightness,
            sharpness=sharpness,
            color=color,
            gamma=gamma,
        )
        return self

    @_conditional_func
    def adjust_gamma(self, gamma: float = 1.0) -> "ImageProcessor":
        logger.debug("Adjust gamma:%s", gamma)
        self.image = utils.image.adjust_gamma(self.image, gamma=gamma)
        return self

    @_conditional_func
    def unsharp_mask(
        self,
        radius: float = 1.0,
        amount: float = 1.5,
        threshold: int = 3,
    ) -> "ImageProcessor":
        logger.debug(
            "Unsharp mask radius:%s, amount:%s, threshold:%s",
            radius,
            amount,
            threshold,
        )
        self.image = utils.image.unsharp_mask(
            self.image,
            radius=radius,
            amount=amount,
            threshold=threshold,
        )
        return self

    @_conditional_func
    def autocontrast_image(
        self,
        cutoff_low: int = 0,
        cutoff_high: int = 0,
        ignore: int | None = None,
    ) -> "ImageProcessor":
        logger.debug(
            "Auto contrast image cutoff_low:%s, cutoff_high:%s, ignore:%s",
            cutoff_low,
            cutoff_high,
            ignore,
        )
        self.image = utils.image.autocontrast_image(
            self.image,
            cutoff_low=cutoff_low,
            cutoff_high=cutoff_high,
            ignore=ignore,
        )
        return self

    @_conditional_func
    def suppress_glare(
        self,
        mode: str = "clahe",
        inpaint_threshold: int = 230,
        inpaint_radius: int = 3,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: int = 8,
    ) -> "ImageProcessor":
        logger.debug(
            "Suppress glare mode:%s, inpaint_threshold:%s, inpaint_radius:%s, clahe_clip_limit:%s, clahe_grid_size:%s",
            mode,
            inpaint_threshold,
            inpaint_radius,
            clahe_clip_limit,
            clahe_grid_size,
        )
        self.image = utils.image.suppress_glare(
            self.image,
            mode=mode,
            inpaint_threshold=inpaint_threshold,
            inpaint_radius=inpaint_radius,
            clahe_clip_limit=clahe_clip_limit,
            clahe_grid_size=clahe_grid_size,
        )
        return self

    @_conditional_func
    def to_gray_scale(self) -> "ImageProcessor":
        logger.debug("Convert image to gray scale")
        self.image = utils.image.convert_to_gray_scale(self.image)
        return self

    @_conditional_func
    def align_image(
        self,
        align_images: Sequence[RefImage],
    ) -> "ImageProcessor":
        logger.debug("Align image to %s", align_images)
        self.image, self.alignment_success, self.alignment_error = (
            utils.image.align_with_status(
                self.image,
                list(align_images),
            )
        )
        return self

    @_conditional_func
    def cut_image(
        self,
        position: ImagePosition,
        options: CutImageOptions | None = None,
        **kwargs: Any,
    ) -> "ImageProcessor":
        if options is None:
            options = CutImageOptions(**kwargs)
        image = utils.image.cut_image(self.image, position)
        if options.autocontrast:
            image = utils.image.autocontrast_image(
                image,
                options.cutoff_low,
                options.cutoff_high,
                options.ignore,
            )
        if options.glare_suppression:
            image = utils.image.suppress_glare(
                image,
                mode=options.glare_mode,
                inpaint_threshold=options.glare_inpaint_threshold,
                inpaint_radius=options.glare_inpaint_radius,
                clahe_clip_limit=options.glare_clahe_clip_limit,
                clahe_grid_size=options.glare_clahe_grid_size,
            )
        if options.unsharp:
            image = utils.image.unsharp_mask(
                image,
                radius=options.unsharp_radius,
                amount=options.unsharp_amount,
                threshold=options.unsharp_threshold,
            )
        self.cut_images_list.append(CutImage(name=position.name, image=image))
        return self

    @_conditional_func
    def cut_images(
        self,
        positions: Sequence[ImagePosition],
        options: CutImageOptions | None = None,
        **kwargs: Any,
    ) -> "ImageProcessor":
        if options is None:
            options = CutImageOptions(**kwargs)
        for pos in positions:
            self.cut_image(position=pos, options=options)
        return self

    @_conditional_func
    def start_image_cutting(self) -> "ImageProcessor":
        self.cut_images_list = []
        return self

    def get_cut_images(self) -> list[CutImage]:
        return self.cut_images_list

    @_conditional_func
    def stop_image_cutting(self) -> "ImageProcessor":
        return self

    @_conditional_func
    def save_cut_images(self) -> "ImageProcessor":
        for img in self.cut_images_list:
            self.pictures[img.name] = img.image
        return self

    @_conditional_func
    def draw_roi(
        self, images: Sequence[ImagePosition], rgb_colour: tuple = (255, 0, 0)
    ) -> "ImageProcessor":
        thickness = 2
        for img in images:
            self.image = utils.image.draw_rectangle(
                self.image,
                img.x,
                img.y,
                img.w,
                img.h,
                rgb_colour=rgb_colour,
                thickness=thickness,
            )
            label_y = max(2, img.y - 14)
            self.image = utils.image.draw_text(
                self.image,
                img.name,
                img.x,
                label_y,
                rgb_colour=rgb_colour,
                bg_colour=(10, 15, 29),
            )
        return self

    @_conditional_func
    def draw_meter_rois(
        self,
        config: Any,
        draw_refs: bool = True,
        draw_digital: bool = True,
        draw_analog: bool = True,
    ) -> "ImageProcessor":
        """Draw all configured reference, digital, and analog ROIs onto the current image."""
        if config is None:
            return self

        if draw_refs and hasattr(config, "alignment") and config.alignment.ref_images:
            for ref in config.alignment.ref_images:
                if (ref.w == 0 or ref.h == 0) and ref.file_name:
                    ref.w, ref.h = utils.image.image_size_from_file(ref.file_name)
            self.draw_roi(config.alignment.ref_images, COLOR_ROI_REFS)

        if (
            draw_digital
            and hasattr(config, "digital_readout")
            and config.digital_readout.cut_images
        ):
            self.draw_roi(config.digital_readout.cut_images, COLOR_ROI_DIGITAL)

        if (
            draw_analog
            and hasattr(config, "analog_readout")
            and config.analog_readout.cut_images
        ):
            self.draw_roi(config.analog_readout.cut_images, COLOR_ROI_ANALOG)

        return self
