import base64
import io
import logging
from collections.abc import Sequence

import cv2
import numpy as np
import PIL.Image
import PIL.ImageEnhance
from PIL import ImageDraw, ImageFont, ImageOps
from PIL.Image import Image

from data_classes import ImagePosition, RefImage

logger = logging.getLogger(__name__)


def save_image(image: Image, file_name: str) -> None:
    if image is None:
        raise ValueError("No image to save")
    if isinstance(image, Image):
        Image.save(image, file_name, "JPEG")
    elif isinstance(image, np.ndarray):
        cv2.imwrite(file_name, image)


def load_image_from_file(file_name: str) -> Image:
    return PIL.Image.open(file_name)


def bytes_to_image(data: bytes) -> Image:
    image_file = PIL.Image.open(io.BytesIO(data))
    if image_file.format not in ["JPEG", "PNG"]:
        raise ValueError("Invalid image format")
    image: Image = image_file.convert("RGB") if image_file.mode != "RGB" else image_file
    return image


def convert_image_base64str(image: Image) -> str:
    data = convert_image_to_bytes(image)
    return base64.b64encode(data).decode("utf-8")


def convert_image_to_bytes(image: Image) -> bytes:
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


def convert_to_image(image: Image) -> Image:
    if isinstance(image, Image):
        return image
    elif isinstance(image, np.ndarray):
        return Image.fromarray(image)
    else:
        raise ValueError("Invalid image")


def convert_image_to_np_array(image: Image) -> np.ndarray:
    if isinstance(image, Image):
        return np.array(image)
    elif isinstance(image, np.ndarray):
        return image
    else:
        raise ValueError("Invalid image")


def convert_np_array_to_image(data: np.ndarray) -> Image:
    if isinstance(data, np.ndarray):
        return PIL.Image.fromarray(data)
    elif isinstance(data, Image):
        return data
    else:
        raise ValueError("Invalid image")


def image_size(image: Image) -> tuple:
    if image is None:
        raise ValueError("No image for size check")
    return image.size


def image_size_from_file(file_name: str) -> tuple:
    image = PIL.Image.open(file_name)
    return image.size


def rotate(image: Image, angle: float, keep_org_size: bool = True) -> Image:
    if image is None:
        raise ValueError("No image to rotate")

    expand = not keep_org_size
    return image.rotate(angle, expand=expand)


def align(image: Image, reference_images: Sequence[RefImage]) -> Image:
    if image is None:
        raise ValueError("No image to align")
    if not reference_images:
        return image

    data = convert_image_to_np_array(image)
    w, h = image.size

    ref_image_coordinates = []
    for ref in reference_images:
        template = cv2.imread(ref.file_name)
        if template is None:
            raise FileNotFoundError(
                f"Alignment reference image file '{ref.file_name}' "
                f"for marker '{ref.name}' could not be loaded"
            )
        ref_image_coordinates.append(_get_ref_coordinate(data, template))

    alignment_ref_pos = [
        (
            reference_images[i].x,
            reference_images[i].y,
        )
        for i in range(len(reference_images))
    ]
    pts1 = np.float32(ref_image_coordinates)  # type: ignore
    pts2 = np.float32(alignment_ref_pos)  # type: ignore
    M = cv2.getAffineTransform(pts1, pts2)  # type: ignore
    img = cv2.warpAffine(data, M, (w, h))
    return convert_np_array_to_image(img)


def _get_ref_coordinate(image: np.ndarray, template: np.ndarray) -> tuple[int, int]:
    """
    Square difference (CV_TM_SQDIFF): This method calculates the squared difference
        between the pixel intensities of the source image and template.
        A lower score indicates a better match.
    Normalized square difference (CV_TM_SQDIFF_NORMED): This is similar to the Square
        Difference, but the result is normalized.
    Cross-correlation (CV_TM_CCORR): It calculates the cross-correlation between
        the source image and template. A higher score indicates a better match.
    Normalized cross-correlation (CV_TM_CCORR_NORMED): In this method, the result of
        cross-correlation is normalized.
    Coefficient correlation (CV_TM_CCOEFF): This method calculates the correlation
        coefficient between the source image and template.
        A higher score indicates a better match.
    Normalized coefficient correlation (CV_TM_CCOEFF_NORMED): In this method,
        the correlation coefficient is normalized.
    """
    if image is None or template is None:
        raise ValueError("Image and template must not be None")

    # method = cv2.TM_SQDIFF
    # method = cv2.TM_SQDIFF_NORMED
    # method = cv2.TM_CCORR_NORMED
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
    image = PIL.ImageEnhance.Contrast(image).enhance(contrast)
    image = PIL.ImageEnhance.Brightness(image).enhance(brightness)
    image = PIL.ImageEnhance.Sharpness(image).enhance(sharpness)
    image = PIL.ImageEnhance.Color(image).enhance(color)
    return image


def convert_to_gray_scale(image: Image) -> Image:
    if image is None:
        raise ValueError("No image to convert to gray scale")
    return ImageOps.grayscale(image).convert("RGB")


def autocontrast_image(
    image: Image,
    cutoff_low: int = 0,
    cutoff_high: int = 0,
    ignore: int | None = None,
) -> Image:
    if image is None:
        raise ValueError("No image to autocontrast")
    if isinstance(image, Image):
        return ImageOps.autocontrast(
            image, cutoff=(cutoff_low, cutoff_high), ignore=ignore  # type: ignore
        )
    if isinstance(image, np.ndarray):
        return image


def detect_glare_mask(
    img_np: np.ndarray,
    threshold: int = 230,
    sat_threshold: int = 40,
    dilate_kernel: int = 3,
) -> np.ndarray:
    """Detect specular glare highlights and return a binary mask (uint8, 0/255)."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for glare detection")

    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
        hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        mask = np.where((val >= threshold) & (sat <= sat_threshold), 255, 0).astype(
            np.uint8
        )
    else:
        gray = (
            cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            if len(img_np.shape) == 3
            else img_np
        )
        mask = np.where(gray >= threshold, 255, 0).astype(np.uint8)

    if dilate_kernel > 1:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (dilate_kernel, dilate_kernel)
        )
        mask = cv2.dilate(mask, kernel, iterations=1).astype(np.uint8)

    return mask


def apply_clahe(
    img_np: np.ndarray,
    clip_limit: float = 2.0,
    grid_size: int = 8,
) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization in LAB/Grayscale space."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for CLAHE")

    grid = max(1, int(grid_size))
    clahe = cv2.createCLAHE(
        clipLimit=max(0.1, float(clip_limit)),
        tileGridSize=(grid, grid),
    )

    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
        lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        enhanced_l = clahe.apply(l_chan)
        merged = cv2.merge([enhanced_l, a_chan, b_chan])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)

    return clahe.apply(img_np)


def apply_inpaint_glare(
    img_np: np.ndarray,
    threshold: int = 230,
    inpaint_radius: int = 3,
) -> np.ndarray:
    """Inpaint specular glare hotspots using Fast Marching (Telea) algorithm."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for inpainting")

    mask = detect_glare_mask(img_np, threshold=threshold)
    non_zero = np.count_nonzero(mask)
    if non_zero == 0 or non_zero == mask.size:
        return img_np.copy()

    radius = max(1, int(inpaint_radius))
    return cv2.inpaint(img_np, mask, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)


def apply_illumination_normalize(
    img_np: np.ndarray,
    sigma: float = 30.0,
) -> np.ndarray:
    """Normalize non-uniform lighting / glare gradients via illumination division."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for illumination normalization")

    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
        lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        l_float = l_chan.astype(np.float32)
        blur = cv2.GaussianBlur(l_float, (0, 0), sigmaX=sigma, sigmaY=sigma)
        mean_lum = float(np.mean(l_float))
        normalized_l = np.clip((l_float / (blur + 1e-5)) * mean_lum, 0, 255).astype(
            np.uint8
        )
        merged = cv2.merge([normalized_l, a_chan, b_chan])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)

    gray_float = img_np.astype(np.float32)
    blur = cv2.GaussianBlur(gray_float, (0, 0), sigmaX=sigma, sigmaY=sigma)
    mean_lum = float(np.mean(gray_float))
    return np.clip((gray_float / (blur + 1e-5)) * mean_lum, 0, 255).astype(np.uint8)


def suppress_glare(
    image: Image,
    mode: str = "clahe",
    inpaint_threshold: int = 230,
    inpaint_radius: int = 3,
    clahe_clip_limit: float = 2.0,
    clahe_grid_size: int = 8,
) -> Image:
    """Suppress specular reflections and glare on meter glass."""
    if image is None:
        raise ValueError("No image to suppress glare")

    img_np = convert_image_to_np_array(image)
    mode_lower = (mode or "clahe").lower()

    if mode_lower == "inpaint":
        result_np = apply_inpaint_glare(
            img_np,
            threshold=inpaint_threshold,
            inpaint_radius=inpaint_radius,
        )
    elif mode_lower in ("illumination_normalize", "retinex", "normalize"):
        result_np = apply_illumination_normalize(img_np)
    elif mode_lower in ("combined", "all"):
        inpainted = apply_inpaint_glare(
            img_np,
            threshold=inpaint_threshold,
            inpaint_radius=inpaint_radius,
        )
        result_np = apply_clahe(
            inpainted,
            clip_limit=clahe_clip_limit,
            grid_size=clahe_grid_size,
        )
    else:  # default "clahe"
        result_np = apply_clahe(
            img_np,
            clip_limit=clahe_clip_limit,
            grid_size=clahe_grid_size,
        )

    return convert_np_array_to_image(result_np)


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
