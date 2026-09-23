"""Analog dial needles rendering for simulated water meter."""

from __future__ import annotations

import math

import PIL.ImageDraw
from PIL.Image import Image


def draw_needle_patch(
    patch: Image,
    width: int,
    height: int,
    value: float,
    needle_color: str = "red",
) -> None:
    """Draw pointer needle on an analog dial patch."""
    draw = PIL.ImageDraw.Draw(patch)
    cx, cy = width // 2, height // 2
    radius = min(width, height) // 2 - 4

    # Angle: 0.0 = 12 o'clock (-90°), clockwise
    angle_deg = (value % 10.0) * 36.0 - 90.0
    angle_rad = math.radians(angle_deg)
    perp_rad = angle_rad + math.pi / 2

    tip_x = cx + radius * 0.88 * math.cos(angle_rad)
    tip_y = cy + radius * 0.88 * math.sin(angle_rad)
    tail_x = cx - radius * 0.24 * math.cos(angle_rad)
    tail_y = cy - radius * 0.24 * math.sin(angle_rad)

    base_half_w = max(2.0, radius * 0.09)
    b1_x = cx + base_half_w * math.cos(perp_rad)
    b1_y = cy + base_half_w * math.sin(perp_rad)
    b2_x = cx - base_half_w * math.cos(perp_rad)
    b2_y = cy - base_half_w * math.sin(perp_rad)

    body_col = (225, 25, 25) if needle_color.lower() == "red" else (25, 25, 30)
    outline_col = (140, 15, 15) if needle_color.lower() == "red" else (10, 10, 15)

    # Shadow
    draw.polygon(
        [
            (tip_x + 2, tip_y + 2),
            (b1_x + 2, b1_y + 2),
            (tail_x + 2, tail_y + 2),
            (b2_x + 2, b2_y + 2),
        ],
        fill=(30, 30, 35),
    )

    # Needle Body
    draw.polygon(
        [(tip_x, tip_y), (b1_x, b1_y), (tail_x, tail_y), (b2_x, b2_y)],
        fill=body_col,
        outline=outline_col,
    )

    # Pivot Cap
    cap_r = max(3.0, radius * 0.14)
    draw.ellipse(
        (cx - cap_r, cy - cap_r, cx + cap_r, cy + cap_r),
        fill=(35, 38, 45),
        outline=(180, 185, 195),
        width=1,
    )


def overlay_analog_needles(
    canvas: Image,
    dial_states: dict[str, float],
    needle_color: str = "red",
) -> None:
    """Render rotating needles on the 4 analog dial faces."""
    dial_centers = [
        ("analog1", 430, 300),
        ("analog2", 360, 365),
        ("analog3", 280, 365),
        ("analog4", 210, 300),
    ]
    dial_size = 76

    for name, cx, cy in dial_centers:
        val = dial_states.get(name, 0.0)
        ax, ay = cx - dial_size // 2, cy - dial_size // 2
        patch = canvas.crop((ax, ay, ax + dial_size, ay + dial_size))
        draw_needle_patch(patch, dial_size, dial_size, val, needle_color)
        canvas.paste(patch, (ax, ay))
