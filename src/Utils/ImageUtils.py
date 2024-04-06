import io
from typing import List
from PIL import Image
import imutils
import numpy as np
import cv2

from DataClasses import ImagePosition, RefImage


def save_image(image: Image, file_name: str) -> None:
    if isinstance(image, Image.Image):
        Image.Image.save(image, file_name, "JPEG")
    elif isinstance(image, np.ndarray):
        cv2.imwrite(file_name, image)


def bytes_to_image(data: bytes) -> Image:
    _verify(data)
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def image_shape(image: Image) -> tuple:
    return image.shape


def image_shape_from_file(file_name: str) -> tuple:
    image = cv2.imread(file_name)
    return image.shape


def _verify(data: bytes) -> bool:
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
    except Exception as e:
        raise ValueError("Invalid image") from e


def rotate(image: Image, angle: float, keep_org_size: bool = True) -> Image:
    if image is None:
        raise ValueError("No image to rotate")
    h, w, ch = image.shape
    newimg = imutils.rotate_bound(image, angle)
    return cv2.resize(newimg, (w, h)) if keep_org_size else newimg


def align(image: Image, reference_images: List[RefImage]) -> Image:
    h, w, ch = image.shape

    ref_image_cordinates = [
        _get_ref_coordinate(image, cv2.imread(reference_images[i].file_name))  # TODO
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
    return cv2.warpAffine(image, M, (w, h))


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
    colour: tuple = (255, 0, 0),
    thickness: int = 3,
) -> Image:
    return cv2.rectangle(
        img=image,
        pt1=(x, y),
        pt2=(x + w, y + h),
        color=colour,
        thickness=thickness,
    )


def draw_text(
    image: Image,
    text: str,
    x: int,
    y: int,
    colour: tuple = (255, 0, 0),
    font=cv2.FONT_HERSHEY_SIMPLEX,
    font_scale: float = 0.5,
    thickness: int = 1,
) -> Image:
    return cv2.putText(
        img=image,
        text=text,
        org=(x, y),
        fontFace=font,
        fontScale=font_scale,
        color=colour,
        thickness=thickness,
    )


def convert_bgr_to_rgb(image: Image) -> Image:
    success, buffer = cv2.imencode(".jpg", image)
    return conv_bytes_to_image(buffer.tobytes())


def conv_bytes_to_image(data: bytes) -> Image:
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def conv_rgb_image_to_bytes(image: Image) -> bytes:
    success, buffer = cv2.imencode(".jpg", image)
    return buffer.tobytes()


def cut_image(
    source: Image,
    img_position: ImagePosition,
) -> Image:
    x, y, w, h = img_position.x, img_position.y, img_position.w, img_position.h
    cropImg = source[y : y + h, x : x + w]
    cropImg = cv2.cvtColor(cropImg, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cropImg)
