"""Mechanical odometer drum counter rendering engine for simulated water meters.

Simulates rotating cylindrical number wheels with continuous rollover transitions,
Geneva drive carry mechanics, 3D cylindrical lighting curvature, and dual-color
integer/decimal wheel schemes.
"""

from __future__ import annotations

import functools
import math
import os
from typing import Any

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from PIL.Image import Image

# -----------------------------------------------------------------------------
# Drum Wheel Color Themes
# -----------------------------------------------------------------------------

DRUM_THEMES: dict[str, dict[str, Any]] = {
    "standard": {
        "label": "Standard (Black with 1 Red Decimal)",
        "int_bg": (22, 24, 28),
        "int_fg": (245, 245, 245),
        "dec_bg": (185, 28, 28),
        "dec_fg": (255, 255, 255),
        "decimal_wheels": 1,  # Only digit5 is red
    },
    "classic_black": {
        "label": "All Black Drums",
        "int_bg": (22, 24, 28),
        "int_fg": (245, 245, 245),
        "dec_bg": (22, 24, 28),
        "dec_fg": (245, 245, 245),
        "decimal_wheels": 0,
    },
    "classic_white": {
        "label": "All White Drums (Vintage)",
        "int_bg": (235, 235, 230),
        "int_fg": (18, 18, 20),
        "dec_bg": (185, 28, 28),
        "dec_fg": (255, 255, 255),
        "decimal_wheels": 1,
    },
    "red_decimals_2": {
        "label": "Black with 2 Red Decimals",
        "int_bg": (22, 24, 28),
        "int_fg": (245, 245, 245),
        "dec_bg": (185, 28, 28),
        "dec_fg": (255, 255, 255),
        "decimal_wheels": 2,  # digit4 and digit5 are red
    },
    "industrial": {
        "label": "Industrial (Dark Grey / White)",
        "int_bg": (45, 48, 54),
        "int_fg": (255, 255, 255),
        "dec_bg": (195, 80, 20),
        "dec_fg": (255, 255, 255),
        "decimal_wheels": 1,
    },
}

DRUM_THEME_OPTIONS: dict[str, str] = {
    key: theme["label"] for key, theme in DRUM_THEMES.items()
}


# -----------------------------------------------------------------------------
# Font Loading & Caching
# -----------------------------------------------------------------------------


def resolve_drum_font_path(font_file: str = "Arimo.ttf") -> str:
    """Locate drum counter TrueType font in config or package directory."""
    candidates = [
        os.path.join("config", "fonts", "drum", font_file),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "..",
            "..",
            "config",
            "fonts",
            "drum",
            font_file,
        ),
        os.path.join("/config", "fonts", "drum", font_file),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError(
        f"Drum font file '{font_file}' not found in candidate paths: {candidates}"
    )


@functools.lru_cache(maxsize=16)
def get_drum_font(size: int = 48) -> PIL.ImageFont.FreeTypeFont:
    """Load and cache FreeType TTF font for simulated drum numbers."""
    font_path = resolve_drum_font_path("Arimo.ttf")
    return PIL.ImageFont.truetype(font_path, size=size)


# -----------------------------------------------------------------------------
# Geneva Carry Mechanics
# -----------------------------------------------------------------------------


def compute_drum_wheel_positions(
    digit_states: dict[str, float],
    carry_mode: str = "geneva",
) -> list[float]:
    """Calculate rolling wheel angular positions (0.0 - 9.99) across the 5 drums.

    In Geneva mode, higher-order wheels remain locked at their integer position
    until the lower-order wheel enters the rollover threshold (9.0 -> 10.0),
    at which point the higher wheel rotates in sync with the carry progression.
    """
    raw_vals = [float(digit_states.get(f"digit{i+1}", 0.0)) for i in range(5)]

    if carry_mode == "continuous":
        return raw_vals

    # Geneva mechanism calculation from rightmost (lowest order) to leftmost
    # Special states (-1 minus, -2 blank) are preserved
    positions = list(raw_vals)

    # If digit5 has a fractional part, propagate rollover backwards
    # Example: digit5 = 9.4 -> digit4 gets +0.4 rollover roll
    for i in range(4, 0, -1):
        prev_val = positions[i]
        if prev_val < 0:
            continue
        prev_mod = prev_val % 10.0
        if prev_mod >= 9.0:
            # Carry fraction from 0.0 at 9.0 to 1.0 at 10.0
            carry_frac = prev_mod - 9.0
            curr_val = positions[i - 1]
            if curr_val >= 0:
                base_digit = math.floor(curr_val) % 10
                positions[i - 1] = base_digit + carry_frac

    return positions


# -----------------------------------------------------------------------------
# Wheel & Bezel Drawing
# -----------------------------------------------------------------------------


def draw_drum_wheel(
    canvas: Image,
    x: int,
    y: int,
    w: int,
    h: int,
    roll_val: float,
    bg_color: tuple[int, int, int],
    fg_color: tuple[int, int, int],
    font: PIL.ImageFont.FreeTypeFont,
    pitch: int = 48,
) -> None:
    """Render a single cylindrical drum wheel with vertical rolling numerals and 3D shading.

    Numerals are rendered on an isolated surface bounded strictly to (w, h) so rotating
    numbers naturally clip at the aperture edges without spilling outside the bezel.
    """
    # 1. Base drum wheel surface strictly clipped to (w, h)
    wheel_img = PIL.Image.new("RGB", (w, h), bg_color)
    wheel_draw = PIL.ImageDraw.Draw(wheel_img)

    # 2. Draw rolling numerals in local coordinates
    center_y = h // 2

    if roll_val == -1.0:
        # Minus sign centered
        bbox = font.getbbox("-")
        gw = bbox[2] - bbox[0]
        gh = bbox[3] - bbox[1]
        ox = (w - gw) // 2 - bbox[0]
        oy = center_y - gh // 2 - bbox[1]
        wheel_draw.text((ox, oy), "-", fill=fg_color, font=font)
    elif roll_val == -2.0:
        # Blank drum
        pass
    else:
        norm_val = roll_val % 10.0
        d1 = math.floor(norm_val) % 10
        d2 = (d1 + 1) % 10
        frac = norm_val - math.floor(norm_val)

        # Primary digit d1 (rolls upwards as frac increases)
        bbox1 = font.getbbox(str(d1))
        gw1 = bbox1[2] - bbox1[0]
        gh1 = bbox1[3] - bbox1[1]
        ox1 = (w - gw1) // 2 - bbox1[0]
        base_oy1 = center_y - gh1 // 2 - bbox1[1]
        oy1 = base_oy1 - int(frac * pitch)
        wheel_draw.text((ox1, oy1), str(d1), fill=fg_color, font=font)

        # Secondary digit d2 entering from bottom when frac > 0.02
        if frac > 0.02:
            bbox2 = font.getbbox(str(d2))
            gw2 = bbox2[2] - bbox2[0]
            ox2 = (w - gw2) // 2 - bbox2[0]
            oy2 = oy1 + pitch
            wheel_draw.text((ox2, oy2), str(d2), fill=fg_color, font=font)

    # 3. 3D Cylindrical Curvature & Shading Overlay
    overlay = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = PIL.ImageDraw.Draw(overlay)

    shadow_depth = 16
    for sy in range(shadow_depth):
        # Top shadow: curves inward under bezel
        alpha_top = int(140 * (1.0 - sy / shadow_depth) ** 1.5)
        ov_draw.line([(0, sy), (w, sy)], fill=(0, 0, 0, alpha_top))

        # Bottom shadow: curves away from viewer
        alpha_bot = int(140 * (1.0 - sy / shadow_depth) ** 1.5)
        by = h - 1 - sy
        ov_draw.line([(0, by), (w, by)], fill=(0, 0, 0, alpha_bot))

    # Subtle specular reflection ridge across center (cylindrical highlight)
    specular_y = h // 2 - 4
    ov_draw.line([(0, specular_y), (w, specular_y)], fill=(255, 255, 255, 22))

    wheel_img.paste(overlay, (0, 0), overlay)

    # 4. Vertical border groove / separator on the wheel edges
    post_draw = PIL.ImageDraw.Draw(wheel_img)
    post_draw.line([(0, 0), (0, h)], fill=(12, 14, 16), width=1)
    post_draw.line([(w - 1, 0), (w - 1, h)], fill=(40, 44, 50), width=1)

    # 5. Composite clipped wheel into canvas
    canvas.paste(wheel_img, (x, y))


def draw_drum_bezel(
    draw: PIL.ImageDraw.ImageDraw,
    win_x: int,
    win_y: int,
    win_w: int,
    win_h: int,
) -> None:
    """Draw a recessed mechanical aperture bezel with metallic border frame."""
    # Outer dark casing
    draw.rectangle(
        (win_x - 6, win_y - 6, win_x + win_w + 6, win_y + win_h + 6),
        fill=(18, 20, 24),
        outline=(65, 70, 80),
        width=3,
    )
    # Inner recess shadow
    draw.rectangle(
        (win_x - 1, win_y - 1, win_x + win_w + 1, win_y + win_h + 1),
        outline=(10, 12, 14),
        width=2,
    )


def overlay_drum_counter(
    canvas: Image,
    digit_states: dict[str, float],
    drum_style: str = "standard",
    drum_carry: str = "geneva",
) -> None:
    """Render 5 mechanical rolling drums inside the aperture window matching exact ROI positions."""
    theme_key = (drum_style or "standard").lower().strip()
    theme = DRUM_THEMES.get(theme_key, DRUM_THEMES["standard"])
    decimal_count = theme.get("decimal_wheels", 1)

    # Fixed slot dimensions matching synthetic template: x = 202 + i*49, y = 150, w = 39, h = 66
    dw, dh = 39, 66
    slot_x_start = 202
    slot_pitch = 49
    slot_y = 150

    # Calculate outer bezel boundaries around the 5 slots
    win_x = slot_x_start - 8
    win_y = slot_y - 6
    win_w = 4 * slot_pitch + dw + 16
    win_h = dh + 12

    draw = PIL.ImageDraw.Draw(canvas)
    draw_drum_bezel(draw, win_x, win_y, win_w, win_h)

    # Compute wheel positions with Geneva rollover propagation
    wheel_positions = compute_drum_wheel_positions(digit_states, carry_mode=drum_carry)
    font = get_drum_font(size=48)

    for i in range(5):
        slot_x = slot_x_start + i * slot_pitch
        is_decimal = (5 - i) <= decimal_count

        bg = theme["dec_bg"] if is_decimal else theme["int_bg"]
        fg = theme["dec_fg"] if is_decimal else theme["int_fg"]

        roll_val = wheel_positions[i]
        draw_drum_wheel(
            canvas=canvas,
            x=slot_x,
            y=slot_y,
            w=dw,
            h=dh,
            roll_val=roll_val,
            bg_color=bg,
            fg_color=fg,
            font=font,
            pitch=48,
        )

    # Aperture dividers between adjacent wheels & frame lips
    for i in range(4):
        div_x1 = slot_x_start + i * slot_pitch + dw
        div_x2 = slot_x_start + (i + 1) * slot_pitch
        draw.rectangle(
            (div_x1, slot_y - 2, div_x2 - 1, slot_y + dh + 2), fill=(22, 24, 28)
        )
        draw.line([(div_x1, slot_y), (div_x1, slot_y + dh)], fill=(12, 14, 16), width=1)
        draw.line(
            [(div_x2 - 1, slot_y), (div_x2 - 1, slot_y + dh)],
            fill=(45, 48, 55),
            width=1,
        )

    # Recessed aperture window top and bottom lip shadows
    draw.line(
        [(win_x, slot_y - 1), (win_x + win_w, slot_y - 1)], fill=(8, 10, 12), width=1
    )
    draw.line(
        [(win_x, slot_y + dh), (win_x + win_w, slot_y + dh)],
        fill=(14, 16, 20),
        width=1,
    )

    # Decimal indicator (small red/white comma separator before decimal wheels)
    if decimal_count > 0:
        dec_slot_idx = 5 - decimal_count
        dot_x = slot_x_start + dec_slot_idx * slot_pitch - 5
        dot_y = slot_y + dh - 10
        draw.ellipse((dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2), fill=(210, 30, 30))
