"""Unit tests for model alignment math utility."""

import pytest

from data_classes import ImagePosition
from utils.model_alignment import (
    calculate_initial_fit,
    project_template_rois_to_camera,
    transform_template_roi_to_camera,
)


def test_transform_template_roi_to_camera_identity():
    """Verify 1:1 scale with zero offset preserves coordinates."""
    x, y, w, h = transform_template_roi_to_camera(
        x_tpl=100,
        y_tpl=150,
        w_tpl=50,
        h_tpl=80,
        scale=1.0,
        pan_x=0.0,
        pan_y=0.0,
        cam_w=640,
        cam_h=480,
    )
    assert (x, y, w, h) == (100, 150, 50, 80)


def test_transform_template_roi_to_camera_scale_down():
    """Verify camera image displayed at half size (scale=0.5) maps to 2x larger camera box."""
    x, y, w, h = transform_template_roi_to_camera(
        x_tpl=100,
        y_tpl=150,
        w_tpl=50,
        h_tpl=80,
        scale=0.5,
        pan_x=0.0,
        pan_y=0.0,
        cam_w=640,
        cam_h=480,
    )
    assert (x, y, w, h) == (200, 300, 100, 160)


def test_transform_template_roi_to_camera_scale_up():
    """Verify camera image displayed at double size (scale=2.0) maps to half-size camera box."""
    x, y, w, h = transform_template_roi_to_camera(
        x_tpl=100,
        y_tpl=150,
        w_tpl=50,
        h_tpl=80,
        scale=2.0,
        pan_x=0.0,
        pan_y=0.0,
        cam_w=640,
        cam_h=480,
    )
    assert (x, y, w, h) == (50, 75, 25, 40)


def test_transform_template_roi_to_camera_panning():
    """Verify positive and negative pan offsets shift coordinates correctly."""
    # Pan camera photo right by 20 and down by 30
    x, y, w, h = transform_template_roi_to_camera(
        x_tpl=120,
        y_tpl=130,
        w_tpl=40,
        h_tpl=60,
        scale=1.0,
        pan_x=20.0,
        pan_y=30.0,
        cam_w=640,
        cam_h=480,
    )
    assert (x, y, w, h) == (100, 100, 40, 60)


def test_transform_template_roi_to_camera_clamping():
    """Verify boundaries are clamped within camera bounds."""
    # Offset that pushes box off left/top edge
    x, y, w, h = transform_template_roi_to_camera(
        x_tpl=10,
        y_tpl=10,
        w_tpl=50,
        h_tpl=50,
        scale=1.0,
        pan_x=100.0,
        pan_y=100.0,
        cam_w=640,
        cam_h=480,
    )
    assert x >= 0
    assert y >= 0
    assert x + w <= 640
    assert y + h <= 480


def test_project_template_rois_to_camera():
    """Verify projection of multiple ROI items preserves names and calculates correct positions."""
    template_rois = [
        ImagePosition(name="digit1", x=200, y=100, w=40, h=70),
        ImagePosition(name="digit2", x=250, y=100, w=40, h=70),
        ImagePosition(name="ref0", x=50, y=50, w=60, h=60),
    ]
    results = project_template_rois_to_camera(
        template_rois=template_rois,
        scale=1.0,
        pan_x=0.0,
        pan_y=0.0,
        cam_w=640,
        cam_h=480,
    )
    assert len(results) == 3
    assert results[0].name == "digit1"
    assert results[0].x == 200
    assert results[0].y == 100
    assert results[0].w == 40
    assert results[0].h == 70
    assert results[1].name == "digit2"
    assert results[1].x == 250
    assert results[2].name == "ref0"
    assert results[2].x == 50


def test_calculate_initial_fit():
    """Verify initial fit scales and centers image appropriately."""
    # 800x600 into 640x480 -> scale = 0.8, pan = 0, 0
    s, px, py = calculate_initial_fit(800, 600, 640, 480)
    assert s == pytest.approx(0.8)
    assert px == pytest.approx(0.0)
    assert py == pytest.approx(0.0)

    # 1280x720 (16:9) into 640x480 (4:3) -> scale = 0.5 (640 / 1280), draw_h = 360, pan_y = (480 - 360)/2 = 60
    s2, px2, py2 = calculate_initial_fit(1280, 720, 640, 480)
    assert s2 == pytest.approx(0.5)
    assert px2 == pytest.approx(0.0)
    assert py2 == pytest.approx(60.0)

    # Invalid input fallback
    s0, _, _ = calculate_initial_fit(0, 0, 640, 480)
    assert s0 == 1.0
