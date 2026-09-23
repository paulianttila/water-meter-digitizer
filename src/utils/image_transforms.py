"""Geometric transformations, affine alignment, cropping, and annotation drawing."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import cv2
import numpy as np
import PIL.Image
import PIL.ImageEnhance
from PIL import ImageDraw, ImageFont
from PIL.Image import Image

from data_classes import ImagePosition, RefImage
from utils.image_filters import adjust_gamma
from utils.image_io import convert_image_to_np_array, convert_np_array_to_image

logger = logging.getLogger(__name__)


def rotate(image: Image, angle: float, keep_org_size: bool = True) -> Image:
    if image is None:
        raise ValueError("No image to rotate")

    expand = not keep_org_size
    return image.rotate(angle, expand=expand)


def align_with_status(
    image: Image, reference_images: Sequence[RefImage]
) -> tuple[Image, bool, str]:
    if image is None:
        raise ValueError("No image to align")
    if not reference_images:
        return image, True, ""

    if len(reference_images) != 3:
        msg = (
            f"Image alignment requires exactly 3 reference markers, found "
            f"{len(reference_images)}. Skipping alignment."
        )
        logger.warning(msg)
        return image, False, msg

    data = convert_image_to_np_array(image)
    w, h = image.size

    ref_image_coordinates = []
    for ref in reference_images:
        template = cv2.imread(ref.file_name)
        if template is None:
            msg = (
                f"Alignment reference image file '{ref.file_name}' for marker "
                f"'{ref.name}' could not be loaded. Skipping alignment."
            )
            logger.warning(msg)
            return image, False, msg
        ref_image_coordinates.append(_get_ref_coordinate(data, template))

    alignment_ref_pos = [
        (
            reference_images[i].x,
            reference_images[i].y,
        )
        for i in range(len(reference_images))
    ]
    try:
        pts1 = np.float32(ref_image_coordinates)  # type: ignore
        pts2 = np.float32(alignment_ref_pos)  # type: ignore
        M = cv2.getAffineTransform(pts1, pts2)  # type: ignore
        img = cv2.warpAffine(data, M, (w, h))
        return convert_np_array_to_image(img), True, ""
    except Exception as e:
        msg = f"Failed to perform affine alignment: {e}"
        logger.error(msg)
        return image, False, msg


def align(image: Image, reference_images: Sequence[RefImage]) -> Image:
    aligned_img, _, _ = align_with_status(image, reference_images)
    return aligned_img


def _get_ref_coordinate(image: np.ndarray, template: np.ndarray) -> tuple[int, int]:
    if image is None or template is None:
        raise ValueError("Image and template must not be None")

    method = cv2.TM_CCOEFF_NORMED
    res = cv2.matchTemplate(image, template, method)
    _min_val, _max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    point = min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc
    return (point[0], point[1])


def draw_rectangle(
    image: Image,
    x: int,
    y: int,
    w: int,
    h: int,
    rgb_colour: tuple = (255, 0, 0),
    thickness: int = 3,
) -> Image:
    if image is None:
        raise ValueError("No image to draw")
    ImageDraw.Draw(image).rectangle(
        xy=((x, y), (x + w, y + h)),
        outline=rgb_colour,
        width=thickness,
    )
    return image


def draw_text(
    image: Image,
    text: str,
    x: int,
    y: int,
    rgb_colour: tuple = (255, 0, 0),
    thickness: int = 1,
    font_size: int = 12,
    bg_colour: tuple | None = None,
) -> Image:
    if image is None:
        raise ValueError("No image to draw")
    font = ImageFont.load_default(size=font_size)
    draw = ImageDraw.Draw(image)
    if bg_colour is not None and text:
        bbox = draw.textbbox((x, y), text, font=font)
        padded_bbox = (bbox[0] - 3, bbox[1] - 1, bbox[2] + 3, bbox[3] + 1)
        draw.rectangle(padded_bbox, fill=bg_colour)
    draw.text(
        (x, y),
        text,
        fill=rgb_colour,
        font=font,
        width=thickness,
    )
    return image


def cut_image(
    image: Image,
    img_position: ImagePosition,
) -> Image:
    if image is None:
        raise ValueError("No image to cut")
    img_w, img_h = image.size
    x, y, w, h = img_position.x, img_position.y, img_position.w, img_position.h
    if x < 0 or y < 0 or (x + w) > img_w or (y + h) > img_h:
        logger.warning(
            "ROI '%s' coordinates [%d, %d, %d, %d] exceed image bounds [%d, %d]",
            getattr(img_position, "name", "unknown"),
            x,
            y,
            w,
            h,
            img_w,
            img_h,
        )
    return image.crop((x, y, x + w, y + h))


def crop_image(image: Image, x: int, y: int, w: int, h: int) -> Image:
    if image is None:
        raise ValueError("No image to crop")
    img_w, img_h = image.size
    if x < 0 or y < 0 or (x + w) > img_w or (y + h) > img_h:
        logger.warning(
            "Crop coordinates [%d, %d, %d, %d] exceed image bounds [%d, %d]",
            x,
            y,
            w,
            h,
            img_w,
            img_h,
        )
    return image.crop((x, y, x + w, y + h))


def resize_image(image: Image, width: int, height: int) -> Image:
    if image is None:
        raise ValueError("No image to resize")
    return image.resize((width, height))


def adjust_image(
    image: Image,
    contrast: float = 1.0,
    brightness: float = 1.0,
    sharpness: float = 1.0,
    color: float = 1.0,
    gamma: float = 1.0,
) -> Image:
    if image is None:
        raise ValueError("No image to adjust")
    if gamma != 1.0:
        image = adjust_gamma(image, gamma=gamma)
    if contrast != 1.0:
        image = PIL.ImageEnhance.Contrast(image).enhance(contrast)
    if brightness != 1.0:
        image = PIL.ImageEnhance.Brightness(image).enhance(brightness)
    if sharpness != 1.0:
        image = PIL.ImageEnhance.Sharpness(image).enhance(sharpness)
    if color != 1.0:
        image = PIL.ImageEnhance.Color(image).enhance(color)
    return image


def create_side_by_side_comparison(
    left_image: Image,
    right_image: Image,
    label_left: str = "ORIGINAL",
    label_right: str = "ADJUSTED",
) -> Image:
    """Combine two images horizontally with labeled badges and a separator."""
    if left_image is None or right_image is None:
        raise ValueError("Both images must be provided for comparison")

    w1, h1 = left_image.size
    w2, h2 = right_image.size
    target_h = max(h1, h2)

    if h1 != target_h:
        w1 = max(1, int(w1 * (target_h / h1)))
        left_img = left_image.resize((w1, target_h))
    else:
        left_img = left_image.copy()

    if h2 != target_h:
        w2 = max(1, int(w2 * (target_h / h2)))
        right_img = right_image.resize((w2, target_h))
    else:
        right_img = right_image.copy()

    total_w = w1 + w2 + 4
    combined = PIL.Image.new("RGB", (total_w, target_h), color=(15, 23, 42))
    combined.paste(left_img.convert("RGB"), (0, 0))
    combined.paste(right_img.convert("RGB"), (w1 + 4, 0))

    draw = ImageDraw.Draw(combined)
    # Vertical cyan separator
    draw.line([(w1 + 1, 0), (w1 + 1, target_h)], fill=(6, 182, 212), width=2)

    font = ImageFont.load_default(size=12)
    if label_left:
        pad_w = len(label_left) * 7 + 12
        draw.rectangle(
            [(10, 10), (10 + pad_w, 30)],
            fill=(15, 23, 42),
            outline=(59, 130, 246),
            width=1,
        )
        draw.text((16, 14), label_left, fill=(147, 197, 253), font=font)

    if label_right:
        pad_w = len(label_right) * 7 + 12
        draw.rectangle(
            [(w1 + 14, 10), (w1 + 14 + pad_w, 30)],
            fill=(15, 23, 42),
            outline=(16, 185, 129),
            width=1,
        )
        draw.text((w1 + 20, 14), label_right, fill=(110, 231, 183), font=font)

    return combined
