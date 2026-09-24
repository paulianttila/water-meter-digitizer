"""Optical perturbations, noise, blur, and glare effects for simulated meter."""

from __future__ import annotations

import numpy as np
import PIL.Image
import PIL.ImageEnhance
import PIL.ImageFilter
from PIL.Image import Image


def inject_glare(
    image: Image,
    pos: tuple[float, float] | None = None,
    intensity: float = 1.0,
) -> Image:
    """Overlay a specular glare hotspot."""
    w, h = image.size
    if pos is not None:
        gx, gy = pos
        if 0.0 <= gx <= 1.0 and 0.0 <= gy <= 1.0:
            glare_x = int(gx * w)
            glare_y = int(gy * h)
        else:
            glare_x = int(gx)
            glare_y = int(gy)
    else:
        glare_x = int(0.45 * w)
        glare_y = int(0.35 * h)

    radius = int(min(w, h) * 0.22)

    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt(((x - glare_x) ** 2) / 1.5 + ((y - glare_y) ** 2))
    glare_mask = np.clip(1.0 - dist_from_center / radius, 0.0, 1.0)
    glare_mask = np.power(glare_mask, 1.8) * min(2.0, max(0.2, intensity))

    img_np = np.array(image, dtype=np.float32)
    img_np += glare_mask[:, :, np.newaxis] * 235.0
    np.clip(img_np, 0, 255, out=img_np)

    return PIL.Image.fromarray(img_np.astype(np.uint8))


def apply_perturbations(
    image: Image,
    rotate: float = 0.0,
    glare: bool = False,
    glare_pos: tuple[float, float] | None = None,
    glare_intensity: float = 1.0,
    noise: float = 0.0,
    brightness: float = 1.0,
    contrast: float = 1.0,
    blur: float = 0.0,
    fillcolor: tuple[int, int, int] | None = None,
) -> Image:
    """Apply camera and environmental artifacts for CV robustness testing."""
    img = image.copy()

    if glare:
        img = inject_glare(img, glare_pos, glare_intensity)

    if rotate != 0.0:
        img = img.rotate(
            rotate,
            resample=PIL.Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=fillcolor,
        )

    if brightness != 1.0:
        img = PIL.ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = PIL.ImageEnhance.Contrast(img).enhance(contrast)

    if blur > 0.0:
        img = img.filter(PIL.ImageFilter.GaussianBlur(radius=blur))

    if noise > 0.0:
        img_np = np.array(img, dtype=np.float32)
        sigma = (noise / 100.0) * 255.0
        rng = np.random.default_rng()
        gauss = rng.normal(0, sigma, img_np.shape)
        noisy = np.clip(img_np + gauss, 0, 255).astype(np.uint8)
        img = PIL.Image.fromarray(noisy)

    return img
