"""7-Segment LCD digit rendering and themes for simulated water meter."""

from __future__ import annotations

from typing import Any

import PIL.ImageDraw
from PIL.Image import Image

# Segment mapping for 0-9 in standard 7-segment display (a, b, c, d, e, f, g)
SEGMENTS_7 = {
    -2: (False, False, False, False, False, False, False),  # Blank / off
    -1: (False, False, False, False, False, False, True),  # Minus sign '-'
    0: (True, True, True, True, True, True, False),
    1: (False, True, True, False, False, False, False),
    2: (True, True, False, True, True, False, True),
    3: (True, True, True, True, False, False, True),
    4: (False, True, True, False, False, True, True),
    5: (True, False, True, True, False, True, True),
    6: (True, False, True, True, True, True, True),
    7: (True, True, True, False, False, False, False),
    8: (True, True, True, True, True, True, True),
    9: (True, True, True, True, False, True, True),
}

COLOR_THEMES = {
    "black": {"active": (15, 20, 25), "ghost": (192, 202, 192), "bg": (205, 218, 205)},
    "dark": {"active": (50, 220, 50), "ghost": (20, 45, 20), "bg": (15, 25, 15)},
    "amber": {"active": (255, 170, 0), "ghost": (60, 40, 10), "bg": (30, 20, 10)},
    "blue": {"active": (20, 40, 90), "ghost": (195, 210, 230), "bg": (210, 225, 245)},
}


def resolve_lcd_bg_color(lcd_bg: str) -> tuple[int, int, int]:
    """Resolve LCD background color name to RGB tuple."""
    bg_map = {
        "grey": (210, 216, 210),
        "green": (195, 218, 195),
        "amber": (230, 205, 155),
        "dark": (18, 26, 20),
        "blue": (205, 220, 240),
        "white": (245, 248, 245),
        "black": (18, 26, 20),
    }
    return bg_map.get(lcd_bg.lower(), (210, 216, 210))


def resolve_lcd_theme(lcd_color: str, lcd_bg: str) -> dict[str, Any]:
    """Resolve LCD active, ghost, and background colors."""
    key = lcd_color.lower()
    theme = COLOR_THEMES.get(key, COLOR_THEMES["black"]).copy()
    if lcd_bg:
        theme["bg"] = resolve_lcd_bg_color(lcd_bg)
    bg = theme["bg"]
    act = theme["active"]
    # Ghost segments: subtle 12% blend of active color onto background
    theme["ghost"] = (
        int(bg[0] * 0.88 + act[0] * 0.12),
        int(bg[1] * 0.88 + act[1] * 0.12),
        int(bg[2] * 0.88 + act[2] * 0.12),
    )
    return theme


def draw_7segment_digit(
    draw: PIL.ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    digit: int,
    active_color: tuple[int, int, int],
    ghost_color: tuple[int, int, int],
    slant: int = 0,
) -> None:
    """Draw an authentic 7-segment LCD digit with tight, polygonal segment geometry."""
    sw = max(4, int(w * 0.22))  # Segment stroke thickness (~7px on 31px inner width)
    gap = 1  # Tight 1px separation between segments
    half_h = h // 2

    # 7 segment state flags: (a, b, c, d, e, f, g)
    seg_active = SEGMENTS_7.get(digit, SEGMENTS_7[-2])

    def color_for(seg_idx: int) -> tuple[int, int, int]:
        return active_color if seg_active[seg_idx] else ghost_color

    # Segment A (Top horizontal trapezoid)
    draw.polygon(
        [
            (x + sw * 0.6 + gap + slant, y),
            (x + w - sw * 0.6 - gap + slant, y),
            (x + w - sw - gap + slant, y + sw),
            (x + sw + gap + slant, y + sw),
        ],
        fill=color_for(0),
    )

    # Segment B (Top-Right vertical)
    draw.polygon(
        [
            (x + w + slant, y + sw * 0.6 + gap),
            (x + w + (slant // 2), y + half_h - gap),
            (x + w - sw + (slant // 2), y + half_h - sw // 2 - gap),
            (x + w - sw + slant, y + sw + gap),
        ],
        fill=color_for(1),
    )

    # Segment C (Bottom-Right vertical)
    draw.polygon(
        [
            (x + w + (slant // 2), y + half_h + gap),
            (x + w, y + h - sw * 0.6 - gap),
            (x + w - sw, y + h - sw - gap),
            (x + w - sw + (slant // 2), y + half_h + sw // 2 + gap),
        ],
        fill=color_for(2),
    )

    # Segment D (Bottom horizontal trapezoid)
    draw.polygon(
        [
            (x + sw + gap, y + h - sw),
            (x + w - sw - gap, y + h - sw),
            (x + w - sw * 0.6 - gap, y + h),
            (x + sw * 0.6 + gap, y + h),
        ],
        fill=color_for(3),
    )

    # Segment E (Bottom-Left vertical)
    draw.polygon(
        [
            (x + (slant // 2), y + half_h + gap),
            (x + sw + (slant // 2), y + half_h + sw // 2 + gap),
            (x + sw, y + h - sw - gap),
            (x, y + h - sw * 0.6 - gap),
        ],
        fill=color_for(4),
    )

    # Segment F (Top-Left vertical)
    draw.polygon(
        [
            (x + slant, y + sw * 0.6 + gap),
            (x + sw + slant, y + sw + gap),
            (x + sw + (slant // 2), y + half_h - sw // 2 - gap),
            (x + (slant // 2), y + half_h - gap),
        ],
        fill=color_for(5),
    )

    # Segment G (Middle horizontal pointed hexagon)
    draw.polygon(
        [
            (x + sw * 0.7 + gap + (slant // 2), y + half_h),
            (x + sw + gap + (slant // 2), y + half_h - sw // 2),
            (x + w - sw - gap + (slant // 2), y + half_h - sw // 2),
            (x + w - sw * 0.7 - gap + (slant // 2), y + half_h),
            (x + w - sw - gap + (slant // 2), y + half_h + sw // 2),
            (x + sw + gap + (slant // 2), y + half_h + sw // 2),
        ],
        fill=color_for(6),
    )


def overlay_lcd_digits(
    canvas: Image,
    digit_states: dict[str, float],
    lcd_color: str = "black",
    lcd_bg: str = "grey",
) -> None:
    """Render 5 authentic 7-segment LCD digits inside the LCD counter window."""
    center_x = canvas.width // 2
    center_y = canvas.height // 2
    win_w = 264
    win_x = center_x - win_w // 2
    win_y = center_y - 100

    dw, dh = 39, 66
    gap = 10
    start_dx = win_x + 14
    dy = win_y + 10

    theme = resolve_lcd_theme(lcd_color, lcd_bg)
    active_col = theme["active"]
    ghost_col = theme["ghost"]

    pad_x = 4
    pad_y = 5
    inner_w = dw - pad_x * 2
    inner_h = dh - pad_y * 2

    draw = PIL.ImageDraw.Draw(canvas)

    for i in range(5):
        digit_name = f"digit{i+1}"
        raw_val = int(digit_states.get(digit_name, 0.0))
        val = raw_val if raw_val in (-1, -2) else raw_val % 10
        x = start_dx + i * (dw + gap) + pad_x
        y = dy + pad_y
        draw_7segment_digit(
            draw,
            x=x,
            y=y,
            w=inner_w,
            h=inner_h,
            digit=val,
            active_color=active_col,
            ghost_color=ghost_col,
            slant=0,
        )
