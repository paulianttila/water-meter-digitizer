from typing import List
import logging

from PIL import Image

from data_classes import CutImage, ImagePosition
import utils

logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self):
        self.condition = None
        self.image = None
        self.cutted_images = [CutImage]
        self.enable_img_saving = False
        self.pictures = {}

    def _conditional_func(func):
        def wrapper(self, *args, **kwargs):
            if self.condition is not None and self.condition is False:
                return self

            func(self, *args, **kwargs)
            return self

        return wrapper

    def if_(self, a):
        self.condition = a
        return self

    def else_(self):
        self.condition = self.condition is False
        return self

    def endif_(self):
        self.condition = None
        return self

    @_conditional_func
    def enable_image_saving(self, state: bool = True) -> "ImageProcessor":
        self.enable_img_saving = state
        return self

    @_conditional_func
    def set_image(self, image: Image) -> "ImageProcessor":
        self.image = image.convert_to_image(image)
        return self

    @_conditional_func
    def set_image_from_base64_str(self, data: str) -> "ImageProcessor":
        self.image = utils.image.convert_base64_str_to_image(data)
        return self

    @_conditional_func
    def get_image(self) -> Image:
        return self.image.copy()

    def get_picture(self, name: str) -> Image:
        if self.pictures.get(name) is not None:
            return self.pictures.get(name, None)
        raise ValueError(f"No image with name {name} available")

    def get_pictures(self) -> dict:
        return self.pictures.copy()

    def get_image_as_base64_str(self) -> str:
        return utils.image.convert_image_base64str(image=self.image)

    @_conditional_func
    def save_image(self, name: str, force_save: bool = False) -> "ImageProcessor":
        if self.enable_img_saving or force_save:
            logger.debug(f"Store image by name {name}")
            self.pictures[name] = self.image
        return self

    @_conditional_func
    def download_image(
        self, url: str, timeout: int, min_image_size: int = 0
    ) -> "ImageProcessor":
        logger.debug(f"Download image from {url}")
        data = utils.download.load_file_from_url(
            url=url,
            timeout=timeout,
            min_file_size=min_image_size,
        )
        self.image = utils.image.bytes_to_image(data)
        self.pictures.clear()
        return self

    @_conditional_func
    def rotate_image(self, angle: float) -> "ImageProcessor":
        logger.debug(f"Rotate image by {angle} degrees")
        self.image = utils.image.rotate(self.image, angle, keep_org_size=False)
        return self

    @_conditional_func
    def crop_image(self, x: int, y: int, w: int, h: int) -> "ImageProcessor":
        logger.debug(f"Crop image to x:{x}, y:{y}, w:{w}, h:{h}")
        self.image = utils.image.crop_image(self.image, x, y, w, h)
        return self

    @_conditional_func
    def resize_image(self, width: int, height: int) -> "ImageProcessor":
        logger.debug(f"Resize image to width:{width}, height:{height}")
        self.image = utils.image.resize_image(self.image, width, height)
        return self

    @_conditional_func
    def adjust_image(
        self,
        contrast: float = 1.0,
        brightness: float = 1.0,
        sharpness: float = 1.0,
        color: float = 1.0,
    ) -> "ImageProcessor":
        logger.debug(
            f"Adjust image contrast:{contrast}, brightness:{brightness}, "
            f"sharpness:{sharpness}, color:{color}"
        )
        self.image = utils.image.adjust_image(
            self.image,
            contrast=contrast,
            brightness=brightness,
            sharpness=sharpness,
            color=color,
        )
        return self

    @_conditional_func
    def to_gray_scale(self) -> "ImageProcessor":
        logger.debug("Convert image to gray scale")
        self.image = utils.image.convert_to_gray_scale(self.image)
        return self

    @_conditional_func
    def align_image(self, align_images: List[ImagePosition]) -> "ImageProcessor":
        logger.debug(f"Align image to {align_images}")
        self.image = utils.image.align(self.image, align_images)
        return self

    @_conditional_func
    def cut_image(self, position: ImagePosition) -> "ImageProcessor":
        image = utils.image.cut_image(self.image, position)
        self.cutted_images.append(CutImage(name=position.name, image=image))
        return self

    @_conditional_func
    def cut_images(self, positions: List[ImagePosition]) -> "ImageProcessor":
        for img in positions:
            image = utils.image.cut_image(self.image, img)
            self.cutted_images.append(CutImage(name=img.name, image=image))
        return self

    @_conditional_func
    def start_image_cutting(self) -> "ImageProcessor":
        self.cutted_images = []
        return self

    def get_cutted_images(self) -> List[CutImage]:
        return self.cutted_images

    @_conditional_func
    def stop_image_cutting(self) -> "ImageProcessor":
        return self

    @_conditional_func
    def save_cutted_images(self) -> "ImageProcessor":
        for img in self.cutted_images:
            self.pictures[img.name] = img.image
        return self

    @_conditional_func
    def draw_roi(
        self, images: List[ImagePosition], rgb_colour: tuple = (255, 0, 0)
    ) -> "ImageProcessor":
        thickness = 1
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
            self.image = utils.image.draw_text(
                self.image,
                img.name,
                img.x,
                img.y - 15,
                rgb_colour=rgb_colour,
            )
        return self
