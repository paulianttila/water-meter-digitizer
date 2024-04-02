from dataclasses import dataclass

import io
import os
from typing import List
import numpy as np
import cv2
from PIL import Image
import logging
from lib.Config import Config, ImagePosition

logger = logging.getLogger(__name__)


@dataclass
class CutImage:
    name: str
    image: Image


@dataclass
class CutResult:
    analog_images: List[CutImage]
    digital_images: List[CutImage]

    def __init__(self, analog_images, digital_images):
        self.analog_images = analog_images
        self.digital_images = digital_images


class ImageProcessor:
    def __init__(self, config: Config, image_tmp_dir="/image_tmp/"):
        self.image_tmp_dir = image_tmp_dir
        self.config = config
        self.reference_images = []
        for item in self.config.alignment_ref_images:
            if os.path.exists(item.file_name):
                logger.debug(f"Use reference image {item.file_name}")
                self.reference_images.append(cv2.imread(item.file_name))
            else:
                logger.warning(f"Reference Image {item.file_name} not found")

    def verify_image(self, data: bytes) -> bool:
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            return True
        except Exception as e:
            logger.warning(f"Image verification failed: {str(e)}")
            return False

    def convert_bgr_to_rgb(self, image: Image) -> Image:
        success, buffer = cv2.imencode(".jpg", image)
        return self.conv_bytes_to_image(buffer.tobytes())

    def conv_bytes_to_image(self, data: bytes) -> Image:
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    def conv_rgb_image_to_bytes(self, image: Image) -> bytes:
        success, buffer = cv2.imencode(".jpg", image)
        return buffer.tobytes()

    def rotate(self, image: Image, store_intermediate_files: bool = False) -> Image:
        image = self._rotate_image(image)
        if store_intermediate_files:
            cv2.imwrite(f"{self.image_tmp_dir}/rotated.jpg", image)
        return image

    def align(self, image: Image, store_intermediate_files: bool = False) -> Image:
        image = self._align(image)
        if store_intermediate_files:
            cv2.imwrite(f"{self.image_tmp_dir}/aligned.jpg", image)
        return image

    def cut(self, image: Image, store_intermediate_files: bool = False) -> CutResult:
        digits = (
            self._cut_images(image, self.config.cut_digital_digit, store_intermediate_files)
            if self.config.digital_readout_enabled
            else []
        )
        analogs = (
            self._cut_images(image, self.config.cut_analog_counter, store_intermediate_files)
            if self.config.analog_readout_enabled
            else []
        )
        return CutResult(analogs, digits)

    def _cut_images(
        self,
        source: Image,
        imagePositions: ImagePosition,
        store_intermediate_files: bool = False,
    ) -> List[CutImage]:
        return [
            CutImage(digit.name, self._cut_image(source, digit, store_intermediate_files))
            for digit in imagePositions
        ]

    def _cut_image(
        self,
        source: Image,
        img_position: ImagePosition,
        store_intermediate_files: bool = False,
    ) -> Image:
        x, y, w, h = img_position.x1, img_position.y1, img_position.w, img_position.h
        cropImg = source[y : y + h, x : x + w]
        if store_intermediate_files:
            cv2.imwrite(f"{self.image_tmp_dir}/{img_position.name}.jpg", cropImg)
        cropImg = cv2.cvtColor(cropImg, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cropImg)

    def _align(self, source: Image) -> Image:
        h, w, ch = source.shape

        ref_image_cordinates = [
            self._get_ref_coordinate(source, self.reference_images[i])
            for i in range(len(self.reference_images))
        ]

        alignment_ref_pos = [
            (
                self.config.alignment_ref_images[i].x,
                self.config.alignment_ref_images[i].y,
            )
            for i in range(len(self.config.alignment_ref_images))
        ]
        pts1 = np.float32(ref_image_cordinates)
        pts2 = np.float32(alignment_ref_pos)
        M = cv2.getAffineTransform(pts1, pts2)
        return cv2.warpAffine(source, M, (w, h))

    def _get_ref_coordinate(self, image: Image, template):
        # method = cv2.TM_SQDIFF         #2
        method = cv2.TM_SQDIFF_NORMED  # 1
        # method = cv2.TM_CCORR_NORMED   #3
        method = cv2.TM_CCOEFF_NORMED  # 4
        res = cv2.matchTemplate(image, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc

    def _rotate_image(self, image: Image) -> Image:
        h, w, ch = image.shape
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, self.config.alignment_rotate_angle, 1.0)
        image = cv2.warpAffine(image, M, (w, h))
        return image

    def draw_roi(
        self,
        image: Image,
        store_to_file: bool = False,
        raw_refs=False,
        draw_digitals=True,
        draw_analogs=True,
    ) -> Image:

        if raw_refs:
            self._draw_refs(image)

        if draw_digitals:
            self._draw_digitals(image)

        if draw_analogs:
            self._draw_analogs(image)

        if store_to_file:
            cv2.imwrite(f"{self.image_tmp_dir}/roi.jpg", image)

        return image

    def _draw_refs(self, image: Image) -> Image:
        colour = (255, 0, 0)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.alignment_ref_images)):
            ref = self.config.alignment_ref_images[i]
            x, y = ref.x, ref.y
            h, w = self.reference_images[i].shape[:2]
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            cv2.putText(
                img=image,
                text=ref.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.4,
                color=colour,
            )
        return image

    def _draw_analogs(self, image: Image) -> Image:
        eclipse = 1
        colour = (0, 255, 0)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.cut_analog_counter)):
            img_pos = self.config.cut_analog_counter[i]
            x, y, w, h = img_pos.x1, img_pos.y1, img_pos.w, img_pos.h
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            xct = int(x + w / 2) + 1
            yct = int(y + h / 2) + 1
            cv2.line(image, (x, yct), (x + w + 5, yct), colour, 1)
            cv2.line(image, (xct, y), (xct, y + h), colour, 1)
            cv2.ellipse(
                img=image,
                center=(xct, yct),
                axes=(int(w / 2) + 2 * eclipse, int(h / 2) + 2 * eclipse),
                angle=0,
                startAngle=0,
                endAngle=360,
                color=colour,
                thickness=eclipse,
            )
            cv2.putText(
                img=image,
                text=img_pos.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.5,
                color=colour,
            )
        return image

    def _draw_digitals(self, image: Image) -> Image:
        colour = (0, 255, 255)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.cut_digital_digit)):
            img_pos = self.config.cut_digital_digit[i]
            x, y, w, h = img_pos.x1, img_pos.y1, img_pos.w, img_pos.h
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            cv2.putText(
                img=image,
                text=img_pos.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.5,
                color=colour,
            )
        return image

    def _get_optimal_font_scale(
        self, text: str, width: int, fontFace=cv2.FONT_HERSHEY_SIMPLEX, thickness=1
    ):
        for scale in reversed(range(0, 60, 1)):
            textSize = cv2.getTextSize(
                text,
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=scale / 10,
                thickness=1,
            )
            new_width = textSize[0][0]
            if new_width <= width:
                return scale / 10
        return 1
