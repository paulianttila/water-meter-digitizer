"""Professional edge-preserving image noise reduction filters.

Supports:
- Bilateral Filtering: Ultra-fast edge-preserving smoothing across spatial and range domains.
- Fast Non-Local Means (NL-Means): Patch-based textural noise reduction for severe sensor grain.
- Median Filtering: Impulse / salt-and-pepper noise removal protecting axis-aligned edges.
- Hybrid Median + Bilateral: Pre-cleans impulse spikes then smooths Gaussian sensor noise.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL.Image import Image

from utils.image_io import convert_image_to_np_array, convert_np_array_to_image


def apply_denoise_bilateral(
    img_np: np.ndarray,
    diameter: int = 5,
    sigma_color: float = 50.0,
    sigma_space: float = 50.0,
) -> np.ndarray:
    """Apply edge-preserving bilateral filter to RGB or grayscale numpy array."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for bilateral filtering")

    d = max(1, int(diameter))
    s_color = max(0.1, float(sigma_color))
    s_space = max(0.1, float(sigma_space))

    # Bilateral filter handles uint8 and float32 natively in OpenCV
    return cv2.bilateralFilter(img_np, d=d, sigmaColor=s_color, sigmaSpace=s_space)


def apply_denoise_nlmeans(
    img_np: np.ndarray,
    h: float = 7.0,
    template_window: int = 7,
    search_window: int = 15,
) -> np.ndarray:
    """Apply Fast Non-Local Means denoising for texture-preserving grain suppression."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for NL-Means denoising")

    # Ensure windows are odd and within bounds
    t_win = max(3, int(template_window))
    if t_win % 2 == 0:
        t_win += 1

    s_win = max(t_win + 2, int(search_window))
    if s_win % 2 == 0:
        s_win += 1

    h_param = max(0.5, float(h))

    # Fast NL-Means requires 8-bit input in OpenCV
    work_img = img_np
    if work_img.dtype != np.uint8:
        work_img = np.clip(work_img, 0, 255).astype(np.uint8)

    is_rgb = len(work_img.shape) == 3 and work_img.shape[2] >= 3
    if is_rgb:
        # Separate luminance and chrominance filtering in LAB color space
        res = cv2.fastNlMeansDenoisingColored(
            work_img[:, :, :3],
            None,
            h=h_param,
            hColor=h_param,
            templateWindowSize=t_win,
            searchWindowSize=s_win,
        )
        if work_img.shape[2] == 4:
            # Preserve alpha channel if present
            return np.dstack([res, work_img[:, :, 3]])
        return res

    # Single-channel grayscale
    if len(work_img.shape) == 3 and work_img.shape[2] == 1:
        squeezed = work_img[:, :, 0]
        denoised = cv2.fastNlMeansDenoising(
            squeezed,
            None,
            h=h_param,
            templateWindowSize=t_win,
            searchWindowSize=s_win,
        )
        return denoised[:, :, np.newaxis]

    return cv2.fastNlMeansDenoising(
        work_img,
        None,
        h=h_param,
        templateWindowSize=t_win,
        searchWindowSize=s_win,
    )


def apply_denoise_median(
    img_np: np.ndarray,
    ksize: int = 3,
) -> np.ndarray:
    """Apply median blur filter for salt-and-pepper and dead-pixel impulse noise."""
    if img_np is None or img_np.size == 0:
        raise ValueError("Invalid image array for median filtering")

    k = max(3, int(ksize))
    if k % 2 == 0:
        k += 1

    return cv2.medianBlur(img_np, k)


def apply_denoise_median_bilateral(
    img_np: np.ndarray,
    ksize: int = 3,
    diameter: int = 5,
    sigma_color: float = 50.0,
    sigma_space: float = 50.0,
) -> np.ndarray:
    """Hybrid two-stage denoiser: median impulse pre-filter followed by bilateral smoothing."""
    median_filtered = apply_denoise_median(img_np, ksize=ksize)
    return apply_denoise_bilateral(
        median_filtered,
        diameter=diameter,
        sigma_color=sigma_color,
        sigma_space=sigma_space,
    )


def denoise_image(
    image: Image,
    method: str = "bilateral",
    diameter: int = 5,
    sigma_color: float = 50.0,
    sigma_space: float = 50.0,
    strength: float = 7.0,
    template_window: int = 7,
    search_window: int = 15,
    median_ksize: int = 3,
) -> Image:
    """Denoise PIL Image using configured edge-preserving algorithm.

    Supported methods:
    - 'bilateral': Fast spatial + range smoothing preserving digit/pointer boundaries.
    - 'nlmeans': Non-Local Means patch filtering for high-ISO sensor grain.
    - 'median': Median filtering targeting salt-and-pepper / dead pixel noise.
    - 'median_bilateral': Combined impulse pre-cleaning and bilateral edge-preserving smoothing.
    """
    if image is None:
        raise ValueError("No image to denoise")

    img_np = convert_image_to_np_array(image)
    method_lower = (method or "bilateral").strip().lower()

    if method_lower == "nlmeans":
        out_np = apply_denoise_nlmeans(
            img_np,
            h=strength,
            template_window=template_window,
            search_window=search_window,
        )
    elif method_lower == "median":
        out_np = apply_denoise_median(img_np, ksize=median_ksize)
    elif method_lower in ("median_bilateral", "hybrid"):
        out_np = apply_denoise_median_bilateral(
            img_np,
            ksize=median_ksize,
            diameter=diameter,
            sigma_color=sigma_color,
            sigma_space=sigma_space,
        )
    else:  # default 'bilateral'
        out_np = apply_denoise_bilateral(
            img_np,
            diameter=diameter,
            sigma_color=sigma_color,
            sigma_space=sigma_space,
        )

    return convert_np_array_to_image(out_np)
