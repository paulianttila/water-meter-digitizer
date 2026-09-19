"""Computer vision visual difference and composite ROI strip utilities."""

import io
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance

import utils.image


def _to_pil(img: Any) -> Image.Image:
    """Convert numpy ndarray or other image representation to PIL Image."""
    if isinstance(img, Image.Image):
        return img
    if isinstance(img, np.ndarray):
        if img.ndim == 2:
            return Image.fromarray(img)
        if img.shape[2] == 3:
            return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if img.shape[2] == 4:
            return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
        return Image.fromarray(img)
    raise TypeError(f"Unsupported image type: {type(img)}")


def calculate_image_ssim(img_a: Any, img_b: Any) -> float:
    """Calculate a fast structural similarity approximation (0.0 to 1.0) between two images."""
    if img_a is None or img_b is None:
        return 0.0

    pil_a = _to_pil(img_a)
    pil_b = _to_pil(img_b)

    target_size = (320, 240)
    a_gray = pil_a.convert("L").resize(target_size, Image.Resampling.BILINEAR)
    b_gray = pil_b.convert("L").resize(target_size, Image.Resampling.BILINEAR)

    arr_a = np.array(a_gray, dtype=np.float32)
    arr_b = np.array(b_gray, dtype=np.float32)

    mu_a = np.mean(arr_a)
    mu_b = np.mean(arr_b)
    sigma_a_sq = np.var(arr_a)
    sigma_b_sq = np.var(arr_b)
    sigma_ab = np.mean((arr_a - mu_a) * (arr_b - mu_b))

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    denom = (mu_a**2 + mu_b**2 + c1) * (sigma_a_sq + sigma_b_sq + c2)
    if denom == 0:
        return 1.0

    ssim = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / denom
    return round(float(np.clip(ssim, 0.0, 1.0)), 4)


def generate_difference_heatmap(
    img_a: Any,
    img_b: Any,
    threshold: int = 25,
    overlay_alpha: float = 0.65,
) -> np.ndarray:
    """Compute absolute difference heatmap between two images and return OpenCV BGR numpy array."""
    if img_a is None or img_b is None:
        fallback = (
            _to_pil(img_b)
            if img_b is not None
            else Image.new("RGB", (320, 240), (0, 0, 0))
        )
        return cv2.cvtColor(np.array(fallback), cv2.COLOR_RGB2BGR)

    pil_a = _to_pil(img_a)
    pil_b = _to_pil(img_b)

    base_b = pil_b.convert("RGB")
    matched_a = pil_a.convert("RGB").resize(base_b.size, Image.Resampling.BILINEAR)

    diff = ImageChops.difference(matched_a, base_b).convert("L")
    diff_arr = np.array(diff)
    mask = diff_arr > threshold

    heatmap = np.zeros((*diff_arr.shape, 3), dtype=np.uint8)
    scaled = np.clip(diff_arr.astype(np.float32) * 2.5, 0, 255).astype(np.uint8)

    heatmap[:, :, 0] = np.where(mask, np.clip(scaled * 1.5, 50, 255), 0)
    heatmap[:, :, 1] = np.where(mask, np.clip(255 - scaled, 0, 200), 0)
    heatmap[:, :, 2] = np.where(mask, np.clip(255 - scaled * 1.2, 0, 240), 0)

    heatmap_img = Image.fromarray(heatmap, mode="RGB")
    dimmed_base = ImageEnhance.Brightness(base_b).enhance(0.7)
    blended = Image.blend(dimmed_base, heatmap_img, overlay_alpha)

    draw = ImageDraw.Draw(blended)
    draw.rectangle(
        [(0, 0), (blended.width - 1, blended.height - 1)],
        outline=(6, 182, 212),
        width=2,
    )
    # Return as OpenCV BGR format
    return cv2.cvtColor(np.array(blended), cv2.COLOR_RGB2BGR)


def create_roi_composite_strip(
    image: Any,
    digital_rois: list[Any] | None = None,
    analog_rois: list[Any] | None = None,
    strip_height: int = 76,
) -> np.ndarray:
    """Extract, label, and stitch all configured ROI crops into a proportional composite strip (~2-4KB)."""
    if image is None:
        blank = Image.new("RGB", (100, strip_height), (15, 23, 42))
        return cv2.cvtColor(np.array(blank), cv2.COLOR_RGB2BGR)

    pil_image = _to_pil(image)

    crops: list[tuple[str, Image.Image]] = []

    if digital_rois:
        for idx, roi in enumerate(digital_rois):
            if isinstance(roi, np.ndarray):
                crops.append((f"digit_{idx+1}", _to_pil(roi)))
            elif hasattr(roi, "name"):
                crop_img = utils.image.cut_image(pil_image, roi)
                crops.append((roi.name, crop_img))

    if analog_rois:
        for idx, roi in enumerate(analog_rois):
            if isinstance(roi, np.ndarray):
                crops.append((f"analog_{idx+1}", _to_pil(roi)))
            elif hasattr(roi, "name"):
                crop_img = utils.image.cut_image(pil_image, roi)
                crops.append((roi.name, crop_img))

    if not crops:
        resized = pil_image.resize(
            (strip_height * 2, strip_height), Image.Resampling.BILINEAR
        )
        return cv2.cvtColor(np.array(resized), cv2.COLOR_RGB2BGR)

    header_height = 16
    max_crop_area_h = max(20, strip_height - header_height - 6)

    # Compute a single uniform scale factor based on the maximum source crop height
    max_source_h = max((c.height for _, c in crops), default=1)
    scale = max_crop_area_h / max(1, max_source_h)

    # Resize all crops proportionally maintaining relative sizes
    resized_crops: list[tuple[str, Image.Image]] = []
    for name, crop in crops:
        crop_w = max(16, round(crop.width * scale))
        crop_h = max(16, round(crop.height * scale))
        resized = crop.resize((crop_w, crop_h), Image.Resampling.BILINEAR)
        resized_crops.append((name, resized))

    # Measure text length for dynamic slot sizing so ROI names are never cut off
    dummy = Image.new("RGB", (1, 1))
    measure_draw = ImageDraw.Draw(dummy)

    slots: list[tuple[str, Image.Image, int, int]] = []
    total_width = 8

    for name, crop in resized_crops:
        if hasattr(measure_draw, "textlength"):
            text_w = int(measure_draw.textlength(name))
        else:
            bbox = measure_draw.textbbox((0, 0), name)
            text_w = int(bbox[2] - bbox[0])

        slot_w = max(crop.width, text_w + 8, 28)
        slots.append((name, crop, slot_w, text_w))
        total_width += slot_w + 6

    composite = Image.new("RGB", (total_width, strip_height), (15, 23, 42))
    draw = ImageDraw.Draw(composite)

    cur_x = 4
    for name, crop, slot_w, text_w in slots:
        # Horizontally center the crop within its slot
        crop_x = cur_x + (slot_w - crop.width) // 2
        # Vertically center the crop within the available crop area below header
        crop_y = header_height + (max_crop_area_h - crop.height) // 2

        composite.paste(crop, (crop_x, crop_y))

        is_digital = "dig" in name.lower()
        is_analog = "ana" in name.lower()
        border_color = (
            (59, 130, 246)
            if is_digital
            else ((245, 158, 11) if is_analog else (16, 185, 129))
        )

        draw.rectangle(
            [(crop_x, crop_y), (crop_x + crop.width - 1, crop_y + crop.height - 1)],
            outline=border_color,
            width=1,
        )

        # Horizontally center the full ROI name above the crop
        text_x = cur_x + (slot_w - text_w) // 2
        text_y = 2
        draw.text(
            (text_x, text_y),
            name,
            fill=(203, 213, 225),
        )

        cur_x += slot_w + 6

    return cv2.cvtColor(np.array(composite), cv2.COLOR_RGB2BGR)


def compress_image_to_bytes(
    img: Any,
    format_type: str = "webp",
    quality: int = 75,
) -> bytes:
    """Compress a PIL image or numpy ndarray into binary bytes (WebP or JPEG)."""
    pil_img = _to_pil(img)
    buf = io.BytesIO()
    fmt = format_type.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt == "JPEG" and pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(buf, format=fmt, quality=quality, optimize=True)
    return buf.getvalue()
