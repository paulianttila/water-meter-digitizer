"""Image I/O, format conversion, and byte/base64 utilities."""

from __future__ import annotations

import base64
import io
import logging

import cv2
import numpy as np
import PIL.Image
from PIL.Image import Image

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_FORMATS: set[str] = {
    "JPEG",
    "PNG",
    "WEBP",
    "BMP",
    "TIFF",
    "MPO",
    "GIF",
}


def save_image(image: Image | np.ndarray, file_name: str) -> None:
    if image is None:
        raise ValueError("No image to save")
    if isinstance(image, Image):
        Image.save(image, file_name, "JPEG")
    elif isinstance(image, np.ndarray):
        cv2.imwrite(file_name, image)


def load_image_from_file(file_name: str) -> Image:
    return PIL.Image.open(file_name)


def bytes_to_image(data: bytes) -> Image:
    try:
        image_file = PIL.Image.open(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"Cannot decode image data: {e}") from e

    fmt = image_file.format
    if fmt and fmt not in SUPPORTED_IMAGE_FORMATS:
        logger.warning(
            "Image format '%s' is not in standard supported formats (%s), attempting conversion to RGB.",
            fmt,
            ", ".join(sorted(SUPPORTED_IMAGE_FORMATS)),
        )

    try:
        image: Image = (
            image_file.convert("RGB") if image_file.mode != "RGB" else image_file
        )
        image.load()
        return image
    except Exception as e:
        raise ValueError(f"Failed to convert image format '{fmt}': {e}") from e


def convert_image_base64str(image: Image | np.ndarray) -> str:
    data = convert_image_to_bytes(image)
    return base64.b64encode(data).decode("utf-8")


def convert_image_to_bytes(image: Image | np.ndarray) -> bytes:
    if image is None:
        raise ValueError("No image to convert")
    if isinstance(image, Image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return buffered.getvalue()
    elif isinstance(image, np.ndarray):
        _is_success, im_buf_arr = cv2.imencode(".jpg", image)
        return im_buf_arr.tobytes()
    else:
        raise ValueError("Invalid image")


def convert_base64_str_to_image(data: str) -> Image:
    if data is None:
        raise ValueError("No image to convert")

    return bytes_to_image(base64.b64decode(data))


def convert_to_image(image: Image | np.ndarray) -> Image:
    if isinstance(image, Image):
        return image
    elif isinstance(image, np.ndarray):
        return PIL.Image.fromarray(image)
    else:
        raise ValueError("Invalid image")


def convert_image_to_np_array(image: Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image):
        return np.array(image)
    elif isinstance(image, np.ndarray):
        return image
    else:
        raise ValueError("Invalid image")


def convert_np_array_to_image(data: np.ndarray | Image) -> Image:
    if isinstance(data, np.ndarray):
        return PIL.Image.fromarray(data)
    elif isinstance(data, Image):
        return data
    else:
        raise ValueError("Invalid image")


def image_size(image: Image) -> tuple[int, int]:
    if image is None:
        raise ValueError("No image for size check")
    return image.size


def image_size_from_file(file_name: str) -> tuple[int, int]:
    image = PIL.Image.open(file_name)
    return image.size
