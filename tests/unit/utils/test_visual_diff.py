"""Unit tests for visual diff and compression utilities."""

import numpy as np
import pytest

from utils.visual_diff import (
    calculate_image_ssim,
    compress_image_to_bytes,
    create_roi_composite_strip,
    generate_difference_heatmap,
)


def test_calculate_image_ssim_identical():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    score = calculate_image_ssim(img, img.copy())
    assert score == pytest.approx(1.0, abs=1e-3)


def test_calculate_image_ssim_different():
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
    score = calculate_image_ssim(img1, img2)
    assert score < 0.1


def test_calculate_image_ssim_different_shapes():
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((200, 150, 3), dtype=np.uint8)
    score = calculate_image_ssim(img1, img2)
    assert score == pytest.approx(1.0, abs=1e-3)


def test_generate_difference_heatmap():
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2[20:50, 20:50] = 255  # bright spot
    heatmap = generate_difference_heatmap(img1, img2)
    assert heatmap.shape == (100, 100, 3)
    assert heatmap.dtype == np.uint8
    # Modified area should have non-zero diff values
    assert np.any(heatmap[25, 25] > 0)


def test_create_roi_composite_strip():
    full_img = np.zeros((300, 300, 3), dtype=np.uint8)
    dig_crops = [np.ones((40, 30, 3), dtype=np.uint8) * 200 for _ in range(5)]
    ana_crops = [np.ones((50, 50, 3), dtype=np.uint8) * 100 for _ in range(3)]
    strip = create_roi_composite_strip(full_img, dig_crops, ana_crops)
    assert strip is not None
    assert len(strip.shape) == 3
    assert strip.shape[0] == 76  # Default strip_height
    assert strip.shape[1] > 0


def test_create_roi_composite_strip_proportional_scaling_and_labels():
    """Verify that different crop dimensions and long ROI labels are handled with dynamic column widths."""
    full_img = np.zeros((400, 400, 3), dtype=np.uint8)
    # 1 small crop and 1 large crop
    small_crop = np.ones((20, 20, 3), dtype=np.uint8) * 150
    large_crop = np.ones((100, 80, 3), dtype=np.uint8) * 250

    strip = create_roi_composite_strip(
        full_img,
        digital_rois=[large_crop],
        analog_rois=[small_crop],
        strip_height=80,
    )
    assert strip is not None
    assert strip.shape[0] == 80
    assert strip.shape[1] > 0


def test_create_roi_composite_strip_with_roi_objects():
    """Verify strip generation with structured ROI objects with custom names."""
    from data_classes import ImagePosition

    full_img = np.ones((200, 200, 3), dtype=np.uint8) * 128
    rois = [
        ImagePosition(name="digit_drum_1_main", x=10, y=10, w=30, h=50),
        ImagePosition(name="subdial_x001", x=60, y=60, w=40, h=40),
    ]
    strip = create_roi_composite_strip(full_img, digital_rois=rois, strip_height=76)
    assert strip is not None
    assert strip.shape[0] == 76
    assert strip.shape[1] > 100  # Wide enough to accommodate both full labels


def test_compress_image_to_bytes():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # WebP
    webp_bytes = compress_image_to_bytes(img, format_type="webp", quality=75)
    assert len(webp_bytes) > 0
    assert webp_bytes.startswith(b"RIFF")

    # JPEG
    jpeg_bytes = compress_image_to_bytes(img, format_type="jpeg", quality=75)
    assert len(jpeg_bytes) > 0
    assert jpeg_bytes.startswith(b"\xff\xd8")
