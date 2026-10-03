"""Unit tests for image noise reduction algorithms (Bilateral, NL-Means, Median, Hybrid)."""

import numpy as np
import pytest
from PIL import Image

from utils.image_denoise import (
    apply_denoise_bilateral,
    apply_denoise_median,
    apply_denoise_median_bilateral,
    apply_denoise_nlmeans,
    denoise_image,
)


def _create_synthetic_test_image(
    mode: str = "RGB", size: tuple[int, int] = (64, 64)
) -> Image.Image:
    """Create a synthetic test image with high-frequency noise and distinct edge steps."""
    w, h = size
    arr = np.zeros((h, w, 3 if mode == "RGB" else 1), dtype=np.uint8)
    # Draw high-contrast step edge (e.g. black background, white square)
    arr[16:48, 16:48] = 220
    # Add Gaussian noise
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 15, arr.shape)
    noisy_arr = np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    if mode == "L":
        return Image.fromarray(noisy_arr[:, :, 0], mode="L")
    return Image.fromarray(noisy_arr, mode="RGB")


def test_denoise_bilateral_rgb_and_gray():
    rgb_img = _create_synthetic_test_image("RGB")
    rgb_np = np.array(rgb_img)

    out_rgb = apply_denoise_bilateral(
        rgb_np, diameter=5, sigma_color=50.0, sigma_space=50.0
    )
    assert out_rgb.shape == rgb_np.shape
    assert out_rgb.dtype == np.uint8
    # Noise variance in uniform region should be reduced
    orig_std = np.std(rgb_np[20:44, 20:44])
    denoised_std = np.std(out_rgb[20:44, 20:44])
    assert denoised_std < orig_std

    # Grayscale
    gray_img = _create_synthetic_test_image("L")
    gray_np = np.array(gray_img)
    out_gray = apply_denoise_bilateral(
        gray_np, diameter=5, sigma_color=50.0, sigma_space=50.0
    )
    assert out_gray.shape == gray_np.shape
    assert out_gray.dtype == np.uint8


def test_denoise_nlmeans_rgb_and_gray():
    rgb_img = _create_synthetic_test_image("RGB")
    rgb_np = np.array(rgb_img)

    out_rgb = apply_denoise_nlmeans(rgb_np, h=7.0, template_window=7, search_window=15)
    assert out_rgb.shape == rgb_np.shape
    assert out_rgb.dtype == np.uint8
    assert np.std(out_rgb[20:44, 20:44]) < np.std(rgb_np[20:44, 20:44])

    # RGBA handling
    rgba_np = np.dstack([rgb_np, np.full((64, 64, 1), 255, dtype=np.uint8)])
    out_rgba = apply_denoise_nlmeans(rgba_np, h=7.0)
    assert out_rgba.shape == rgba_np.shape
    assert out_rgba.shape[2] == 4

    # Single-channel 2D and 3D grayscale
    gray_img = _create_synthetic_test_image("L")
    gray_np = np.array(gray_img)
    out_gray2d = apply_denoise_nlmeans(gray_np, h=7.0)
    assert out_gray2d.shape == gray_np.shape

    gray_np3d = gray_np[:, :, np.newaxis]
    out_gray3d = apply_denoise_nlmeans(gray_np3d, h=7.0)
    assert out_gray3d.shape == gray_np3d.shape


def test_denoise_median_impulse_noise():
    img_np = np.full((40, 40, 3), 128, dtype=np.uint8)
    # Add salt and pepper noise
    img_np[10, 10] = [255, 255, 255]
    img_np[20, 20] = [0, 0, 0]

    out_np = apply_denoise_median(img_np, ksize=3)
    assert out_np.shape == img_np.shape
    # Salt and pepper spikes should be replaced by median (128)
    assert np.array_equal(out_np[10, 10], [128, 128, 128])
    assert np.array_equal(out_np[20, 20], [128, 128, 128])


def test_denoise_median_bilateral_hybrid():
    rgb_img = _create_synthetic_test_image("RGB")
    rgb_np = np.array(rgb_img)
    # Add impulse spikes
    rgb_np[5, 5] = [255, 255, 255]

    out_np = apply_denoise_median_bilateral(
        rgb_np, ksize=3, diameter=5, sigma_color=40.0, sigma_space=40.0
    )
    assert out_np.shape == rgb_np.shape
    assert not np.array_equal(out_np[5, 5], [255, 255, 255])


def test_denoise_image_wrapper_dispatch():
    img = _create_synthetic_test_image("RGB")

    # Bilateral
    res_b = denoise_image(
        img, method="bilateral", diameter=5, sigma_color=50.0, sigma_space=50.0
    )
    assert isinstance(res_b, Image.Image)
    assert res_b.size == img.size

    # NL-Means
    res_nl = denoise_image(img, method="nlmeans", strength=5.0)
    assert isinstance(res_nl, Image.Image)
    assert res_nl.size == img.size

    # Median
    res_m = denoise_image(img, method="median", median_ksize=3)
    assert isinstance(res_m, Image.Image)
    assert res_m.size == img.size

    # Hybrid
    res_h = denoise_image(img, method="median_bilateral", median_ksize=3, diameter=5)
    assert isinstance(res_h, Image.Image)
    assert res_h.size == img.size


def test_denoise_invalid_inputs():
    with pytest.raises(ValueError, match="No image to denoise"):
        denoise_image(None)

    with pytest.raises(ValueError, match="Invalid image array"):
        apply_denoise_bilateral(None)

    with pytest.raises(ValueError, match="Invalid image array"):
        apply_denoise_nlmeans(np.array([]))

    with pytest.raises(ValueError, match="Invalid image array"):
        apply_denoise_median(None)
