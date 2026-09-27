"""Utility for projecting meter model preset template ROIs onto user camera photos.

Provides coordinate transforms to calculate camera-space ROI bounding boxes
(references, digital, analog) from interactive template alignment parameters
(pan offset, scale factor, and fine rotation).
"""

from __future__ import annotations

from typing import Any

from data_classes import ImagePosition


def transform_template_roi_to_camera(
    x_tpl: int,
    y_tpl: int,
    w_tpl: int,
    h_tpl: int,
    scale: float,
    pan_x: float,
    pan_y: float,
    cam_w: int,
    cam_h: int,
) -> tuple[int, int, int, int]:
    """Projects a single template ROI box into camera image coordinate space.

    Args:
        x_tpl: Template ROI X coordinate on canvas.
        y_tpl: Template ROI Y coordinate on canvas.
        w_tpl: Template ROI width on canvas.
        h_tpl: Template ROI height on canvas.
        scale: Scale factor (canvas pixels per camera pixel, > 0).
        pan_x: Horizontal offset of camera image on canvas.
        pan_y: Vertical offset of camera image on canvas.
        cam_w: Camera image width in pixels.
        cam_h: Camera image height in pixels.

    Returns:
        tuple (x_cam, y_cam, w_cam, h_cam) clamped within camera bounds.
    """
    if scale <= 0:
        scale = 1.0

    # Inverse mapping from canvas to camera
    x_cam = round((x_tpl - pan_x) / scale)
    y_cam = round((y_tpl - pan_y) / scale)
    w_cam = max(4, round(w_tpl / scale))
    h_cam = max(4, round(h_tpl / scale))

    # Boundary clamping
    x_cam = max(0, min(x_cam, max(0, cam_w - 4)))
    y_cam = max(0, min(y_cam, max(0, cam_h - 4)))
    w_cam = max(4, min(w_cam, cam_w - x_cam))
    h_cam = max(4, min(h_cam, cam_h - y_cam))

    return x_cam, y_cam, w_cam, h_cam


def project_template_rois_to_camera(
    template_rois: list[Any],
    scale: float,
    pan_x: float,
    pan_y: float,
    cam_w: int,
    cam_h: int,
) -> list[ImagePosition]:
    """Projects a list of template ROIs into camera image coordinate space.

    Args:
        template_rois: List of ROI objects having name, x, y, w, h attributes.
        scale: Scale factor (> 0).
        pan_x: Horizontal offset of camera image on canvas.
        pan_y: Vertical offset of camera image on canvas.
        cam_w: Camera image width in pixels.
        cam_h: Camera image height in pixels.

    Returns:
        List of ImagePosition objects with projected camera coordinates.
    """
    results: list[ImagePosition] = []
    for roi in template_rois:
        name = getattr(roi, "name", "")
        rx = int(getattr(roi, "x", 0))
        ry = int(getattr(roi, "y", 0))
        rw = int(getattr(roi, "w", 0))
        rh = int(getattr(roi, "h", 0))

        cx, cy, cw, ch = transform_template_roi_to_camera(
            x_tpl=rx,
            y_tpl=ry,
            w_tpl=rw,
            h_tpl=rh,
            scale=scale,
            pan_x=pan_x,
            pan_y=pan_y,
            cam_w=cam_w,
            cam_h=cam_h,
        )
        results.append(ImagePosition(name=name, x=cx, y=cy, w=cw, h=ch))
    return results


def calculate_initial_fit(
    cam_w: int,
    cam_h: int,
    canvas_w: int,
    canvas_h: int,
) -> tuple[float, float, float]:
    """Calculates default scale and centered pan offsets to fit a camera image on a canvas.

    Args:
        cam_w: Camera image width.
        cam_h: Camera image height.
        canvas_w: Template canvas width.
        canvas_h: Template canvas height.

    Returns:
        tuple (scale, pan_x, pan_y) that centers and fits the image within the canvas.
    """
    if cam_w <= 0 or cam_h <= 0 or canvas_w <= 0 or canvas_h <= 0:
        return 1.0, 0.0, 0.0

    scale = min(canvas_w / cam_w, canvas_h / cam_h)
    draw_w = cam_w * scale
    draw_h = cam_h * scale
    pan_x = (canvas_w - draw_w) / 2.0
    pan_y = (canvas_h - draw_h) / 2.0
    return scale, pan_x, pan_y
