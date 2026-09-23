"""Photographic enhancement filters (gamma, unsharp mask, histogram, and auto-tuning)."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import ImageOps
from PIL.Image import Image

from utils.image_io import convert_image_to_np_array, convert_np_array_to_image


def adjust_gamma(image: Image, gamma: float = 1.0) -> Image:
    """Non-linear tonal mid-tone curve adjustment using a 256-entry SIMD LUT.

    gamma < 1.0 brightens shadows/mid-tones (e.g. dark basement meter pits).
    gamma > 1.0 darkens overexposed mid-tones while protecting black/white extremes.
    """
    if image is None:
        raise ValueError("No image to adjust gamma")
    if abs(gamma - 1.0) < 1e-4:
        return image

    img_np = convert_image_to_np_array(image)
    inv_gamma = 1.0 / max(0.01, gamma)
    table = np.array(
        [np.clip(pow(i / 255.0, inv_gamma) * 255.0, 0, 255) for i in range(256)],
        dtype=np.uint8,
    )
    result_np = cv2.LUT(img_np, table)
    return convert_np_array_to_image(result_np)


def unsharp_mask(
    image: Image,
    radius: float = 1.0,
    amount: float = 1.5,
    threshold: int = 3,
) -> Image:
    """Luminance-only adaptive unsharp masking with noise coring threshold.

    Sharpens spatial edges on the Lightness (L) channel in LAB space, preventing
    chromatic fringing and noise amplification on flat background surfaces.
    """
    if image is None:
        raise ValueError("No image to sharpen")
    if amount <= 0.0 or radius <= 0.0:
        return image

    img_np = convert_image_to_np_array(image)
    is_rgb = len(img_np.shape) == 3 and img_np.shape[2] >= 3

    if is_rgb:
        # Work strictly in LAB color space: sharpen only L (Luminance) channel
        lab = cv2.cvtColor(img_np[:, :, :3], cv2.COLOR_RGB2LAB)
        l_chan = lab[:, :, 0]
        blurred = cv2.GaussianBlur(l_chan, (0, 0), radius)
        high_pass = l_chan.astype(np.int32) - blurred.astype(np.int32)
        mask = (np.abs(high_pass) >= threshold).astype(np.int32)
        sharpened_l = np.clip(
            l_chan.astype(np.float32) + (amount * high_pass * mask), 0, 255
        ).astype(np.uint8)
        lab[:, :, 0] = sharpened_l
        sharpened_np = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    else:
        gray = img_np if len(img_np.shape) == 2 else img_np[:, :, 0]
        blurred = cv2.GaussianBlur(gray, (0, 0), radius)
        high_pass = gray.astype(np.int32) - blurred.astype(np.int32)
        mask = (np.abs(high_pass) >= threshold).astype(np.int32)
        sharpened_np = np.clip(
            gray.astype(np.float32) + (amount * high_pass * mask), 0, 255
        ).astype(np.uint8)

    return convert_np_array_to_image(sharpened_np)


def calculate_focus_score(image: Image | np.ndarray) -> float:
    """Calculate the focus/blur metric of an image using Laplacian variance."""
    if image is None:
        return 0.0
    img_np = convert_image_to_np_array(image)
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np[:, :, :3], cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())
    return round(variance, 2)


def calculate_histogram(image: Image | np.ndarray) -> dict[str, list[int] | float]:
    """Compute 256-bin Luminance and RGB histograms with shadow/highlight clipping flags."""
    if image is None:
        return {
            "luminance": [0] * 256,
            "r": [0] * 256,
            "g": [0] * 256,
            "b": [0] * 256,
            "shadow_clip_pct": 0.0,
            "highlight_clip_pct": 0.0,
        }

    img_np = convert_image_to_np_array(image)
    total_pixels = float(img_np.shape[0] * img_np.shape[1])

    if len(img_np.shape) == 3 and img_np.shape[2] >= 3:
        # Rec.709 Luminance: 0.2126 R + 0.7152 G + 0.0722 B
        r_hist, _ = np.histogram(img_np[:, :, 0], bins=256, range=(0, 256))
        g_hist, _ = np.histogram(img_np[:, :, 1], bins=256, range=(0, 256))
        b_hist, _ = np.histogram(img_np[:, :, 2], bins=256, range=(0, 256))
        luma = (
            0.2126 * img_np[:, :, 0]
            + 0.7152 * img_np[:, :, 1]
            + 0.0722 * img_np[:, :, 2]
        ).astype(np.uint8)
        luma_hist, _ = np.histogram(luma, bins=256, range=(0, 256))
    else:
        gray = img_np if len(img_np.shape) == 2 else img_np[:, :, 0]
        luma_hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        r_hist, g_hist, b_hist = luma_hist, luma_hist, luma_hist

    shadow_clipped = float(luma_hist[0]) / max(1.0, total_pixels) * 100.0
    highlight_clipped = float(luma_hist[255]) / max(1.0, total_pixels) * 100.0

    return {
        "luminance": [int(x) for x in luma_hist],
        "r": [int(x) for x in r_hist],
        "g": [int(x) for x in g_hist],
        "b": [int(x) for x in b_hist],
        "shadow_clip_pct": round(shadow_clipped, 2),
        "highlight_clip_pct": round(highlight_clipped, 2),
    }


def auto_tune_image(image: Image | np.ndarray) -> dict[str, float | int]:
    """Analyze image metrics and suggest optimal photographic exposure & sharpness parameters."""
    if image is None:
        return {
            "gamma": 1.0,
            "contrast": 1.0,
            "brightness": 1.0,
            "unsharp_amount": 1.5,
            "unsharp_radius": 1.0,
            "unsharp_threshold": 3,
            "cutoff_low": 2,
            "cutoff_high": 45,
            "focus_score": 0.0,
        }

    img_np = convert_image_to_np_array(image)
    if len(img_np.shape) == 3 and img_np.shape[2] >= 3:
        gray = cv2.cvtColor(img_np[:, :, :3], cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np

    focus_score = calculate_focus_score(gray)
    mean_lum = float(np.mean(gray))
    std_lum = float(np.std(gray))

    # Tonal Curve (Gamma & Brightness) based on mid-tone luminance
    if mean_lum < 85:
        # Dark basement / underexposed image
        gamma = round(max(0.6, mean_lum / 128.0), 2)
        brightness = 1.15
        contrast = 1.10
    elif mean_lum > 175:
        # Overexposed / reflective
        gamma = round(min(1.4, mean_lum / 128.0), 2)
        brightness = 0.90
        contrast = 1.15
    else:
        # Normal lighting
        gamma = 1.0
        brightness = 1.0
        contrast = round(1.0 + max(0.0, (50.0 - std_lum) / 100.0), 2)

    # Adaptive Unsharp Mask tuning based on focus score
    if focus_score < 100:
        # Blurry / soft lens -> strong boost with tight radius
        unsharp_amount = 2.0
        unsharp_radius = 1.2
        unsharp_threshold = 2
    elif focus_score < 300:
        # Moderate sharpness -> crisp edge boost
        unsharp_amount = 1.5
        unsharp_radius = 1.0
        unsharp_threshold = 3
    else:
        # Already sharp -> subtle micro-contrast
        unsharp_amount = 1.1
        unsharp_radius = 0.8
        unsharp_threshold = 4

    return {
        "gamma": gamma,
        "contrast": contrast,
        "brightness": brightness,
        "unsharp_amount": unsharp_amount,
        "unsharp_radius": unsharp_radius,
        "unsharp_threshold": unsharp_threshold,
        "cutoff_low": 2,
        "cutoff_high": 45,
        "focus_score": focus_score,
    }


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
    return image
