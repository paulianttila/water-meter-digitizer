"""Glare detection and illumination normalization for camera images."""

from __future__ import annotations

import cv2
import numpy as np
from PIL.Image import Image

from utils.image_io import convert_image_to_np_array, convert_np_array_to_image


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
