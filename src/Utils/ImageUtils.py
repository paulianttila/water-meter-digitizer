import base64
import io
from typing import List
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont
import numpy as np
import cv2

from DataClasses import ImagePosition, RefImage


def save_image(image: Image, file_name: str) -> None:
    if image is None:
        raise ValueError("No image to save")
    if isinstance(image, Image.Image):
        Image.Image.save(image, file_name, "JPEG")
    elif isinstance(image, np.ndarray):
        cv2.imwrite(file_name, image)


def bytes_to_image(data: bytes) -> Image:
    image = Image.open(io.BytesIO(data))
    if image.format not in ["JPEG", "PNG"]:
        raise ValueError("Invalid image format")
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def conv_image_base64str(image: Image) -> str:
    if image is None:
        raise ValueError("No image to convert")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def conv_to_image(image: Image) -> Image:
    if isinstance(image, Image.Image):
        return image
    elif isinstance(image, np.ndarray):
        return Image.fromarray(image)
    else:
        raise ValueError("Invalid image")


def convert_image_to_np_array(image: Image) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.array(image)
    elif isinstance(image, np.ndarray):
        return image
    else:
        raise ValueError("Invalid image")


def convert_np_array_to_image(data: np.ndarray) -> np.ndarray:
    if isinstance(data, np.ndarray):
        return Image.fromarray(data)
    elif isinstance(data, Image.Image):
        return data
    else:
        raise ValueError("Invalid image")


def image_size(image: Image) -> tuple:
    if image is None:
        raise ValueError("No image for size check")
    return image.size


def image_size_from_file(file_name: str) -> tuple:
    image = Image.open(file_name)
    return image.size


def rotate(image: Image, angle: float, keep_org_size: bool = True) -> Image:
    if image is None:
        raise ValueError("No image to rotate")

    expand = not keep_org_size
    return image.rotate(angle, expand=expand)


def align(image: Image, reference_images: List[RefImage]) -> Image:
    if image is None:
        raise ValueError("No image to align")
    data = convert_image_to_np_array(image)
    w, h = image.size

    ref_image_cordinates = [
        _get_ref_coordinate(data, cv2.imread(reference_images[i].file_name))  # TODO
        for i in range(len(reference_images))
    ]
    alignment_ref_pos = [
        (
            reference_images[i].x,
            reference_images[i].y,
        )
        for i in range(len(reference_images))
    ]
    pts1 = np.float32(ref_image_cordinates)
    pts2 = np.float32(alignment_ref_pos)
    M = cv2.getAffineTransform(pts1, pts2)
    img = cv2.warpAffine(data, M, (w, h))
    return convert_np_array_to_image(img)


def _get_ref_coordinate(image: Image, template):
    # method = cv2.TM_SQDIFF         #2
    method = cv2.TM_SQDIFF_NORMED  # 1
    # method = cv2.TM_CCORR_NORMED   #3
    method = cv2.TM_CCOEFF_NORMED  # 4
    res = cv2.matchTemplate(image, template, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    return min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc


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
        [(x, y), (x + w, y + h)],
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
) -> Image:

    if image is None:
        raise ValueError("No image to draw")
    font = ImageFont.load_default(size=font_size)
    ImageDraw.Draw(image).text(
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
    x, y, w, h = img_position.x, img_position.y, img_position.w, img_position.h
    return image.crop((x, y, x + w, y + h))


def crop_image(image: Image, x: int, y: int, w: int, h: int) -> Image:
    if image is None:
        raise ValueError("No image to crop")
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
) -> Image:
    if image is None:
        raise ValueError("No image to adjust")
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Sharpness(image).enhance(sharpness)
    image = ImageEnhance.Color(image).enhance(color)
    return image


def convert_to_gray_scale(image: Image) -> Image:
    if image is None:
        raise ValueError("No image to convert to gray scale")
    return ImageOps.grayscale(image).convert("RGB")
