"""7-Segment LCD digit rendering and themes for simulated water meter."""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass
from typing import Any

import PIL.ImageDraw
import PIL.ImageFont
from PIL.Image import Image

LCD_FONTS: dict[str, dict[str, str]] = {
    "builtin": {
        "label": "Builtin Procedural (Vector)",
        "family": "vector",
        "category": "vector",
    },
    # 7-Segment (DSEG7)
    "dseg7_classic": {
        "label": "DSEG7 Classic Regular (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Classic-Regular.ttf",
        "ghost_char": "8",
    },
    "dseg7_classic_bold": {
        "label": "DSEG7 Classic Bold (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Classic-Bold.ttf",
        "ghost_char": "8",
    },
    "dseg7_classic_italic": {
        "label": "DSEG7 Classic Italic (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Classic-Italic.ttf",
        "ghost_char": "8",
    },
    "dseg7_modern": {
        "label": "DSEG7 Modern Regular (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Modern-Regular.ttf",
        "ghost_char": "8",
    },
    "dseg7_modern_bold": {
        "label": "DSEG7 Modern Bold (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Modern-Bold.ttf",
        "ghost_char": "8",
    },
    "dseg7_modern_italic": {
        "label": "DSEG7 Modern Italic (7-Seg)",
        "family": "dseg7",
        "category": "7seg",
        "file": "DSEG7Modern-Italic.ttf",
        "ghost_char": "8",
    },
    # 14-Segment (DSEG14)
    "dseg14_classic": {
        "label": "DSEG14 Classic Regular (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Classic-Regular.ttf",
        "ghost_char": "~",
    },
    "dseg14_classic_bold": {
        "label": "DSEG14 Classic Bold (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Classic-Bold.ttf",
        "ghost_char": "~",
    },
    "dseg14_classic_italic": {
        "label": "DSEG14 Classic Italic (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Classic-Italic.ttf",
        "ghost_char": "~",
    },
    "dseg14_modern": {
        "label": "DSEG14 Modern Regular (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Modern-Regular.ttf",
        "ghost_char": "~",
    },
    "dseg14_modern_bold": {
        "label": "DSEG14 Modern Bold (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Modern-Bold.ttf",
        "ghost_char": "~",
    },
    "dseg14_modern_italic": {
        "label": "DSEG14 Modern Italic (14-Seg)",
        "family": "dseg14",
        "category": "14seg",
        "file": "DSEG14Modern-Italic.ttf",
        "ghost_char": "~",
    },
}

LCD_FONT_OPTIONS: dict[str, str] = {k: v["label"] for k, v in LCD_FONTS.items()}


def resolve_font_path(font_file: str) -> str:
    """Resolve font file path from configuration or package directories."""
    candidates = [
        os.path.join("config", "fonts", "dseg", font_file),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "..",
            "..",
            "config",
            "fonts",
            "dseg",
            font_file,
        ),
        os.path.join("/config", "fonts", "dseg", font_file),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError(
        f"Font file '{font_file}' not found in candidate paths: {candidates}"
    )


@functools.lru_cache(maxsize=32)
def get_lcd_font(font_file: str, size: int) -> PIL.ImageFont.FreeTypeFont:
    """Load and cache FreeType TTF font for simulated LCD rendering."""
    full_path = resolve_font_path(font_file)
    return PIL.ImageFont.truetype(full_path, size=size)


def draw_7segment_font_digit(
    draw: PIL.ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    char_str: str,
    font_cfg: dict[str, str],
    active_color: tuple[int, int, int],
    ghost_color: tuple[int, int, int],
) -> None:
    """Render authentic dual-layer ghost and active LCD segments with optical slot centering."""
    font_file = font_cfg["file"]
    # Scale font size dynamically based on slot height h
    font_size = max(14, int(h * 0.68))
    font = get_lcd_font(font_file, size=font_size)
    ghost_char = font_cfg.get("ghost_char", "8")

    bbox = font.getbbox(ghost_char)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]

    # Exactly center the character bounding box inside slot (x, y, w, h)
    ox = x + (w - gw) // 2 - bbox[0]
    oy = y + (h - gh) // 2 - bbox[1]

    # Layer 1: Ghost unlit segments
    draw.text((ox, oy), ghost_char, fill=ghost_color, font=font)

    # Layer 2: Active lit glyph (if not blank)
    if char_str and char_str != " ":
        draw.text((ox, oy), char_str, fill=active_color, font=font)


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
    sw = max(2, int(w * 0.20))  # Adaptive segment stroke thickness
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


@dataclass(frozen=True)
class BoxDigitLayout:
    """Specification for a group of regularly spaced digit display boxes."""

    x0: int
    y0: int
    w: int
    h: int
    step: int
    count: int
    prefix: str

    def get_box(self, index: int) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) for digit box at given 0-based index."""
        return (self.x0 + index * self.step, self.y0, self.w, self.h)

    def digit_name(self, index: int) -> str:
        """Return canonical digit slot name (e.g. 'digit1', 'flow_dec2')."""
        return f"{self.prefix}{index + 1}"


class DigitalFlowScreenLayout:
    """Canonical screen layout coordinates on the 640x480 simulation canvas."""

    DIVIDER_LINE: tuple[tuple[int, int], tuple[int, int]] = ((188, 216), (452, 216))
    BATTERY_OUTLINE: tuple[int, int, int, int] = (192, 142, 205, 148)
    BATTERY_TIP: tuple[int, int, int, int] = (205, 144, 207, 146)
    BATTERY_FILL: tuple[int, int, int, int] = (194, 144, 201, 146)
    ARROW_POINTS: tuple[tuple[int, int], ...] = ((438, 143), (446, 146), (438, 149))

    # Cumulative volume (m³) line
    VOLUME_INTEGER = BoxDigitLayout(
        x0=190, y0=156, w=24, h=44, step=28, count=6, prefix="digit"
    )
    VOLUME_DOT: tuple[int, int] = (358, 197)
    VOLUME_DECIMAL = BoxDigitLayout(
        x0=364, y0=168, w=18, h=32, step=21, count=3, prefix="decimal"
    )
    VOLUME_UNIT_POS: tuple[int, int] = (430, 172)

    # Instantaneous flow rate (m³/h) line
    FLOW_LABEL_POS: tuple[int, int] = (194, 246)
    FLOW_INTEGER = BoxDigitLayout(
        x0=242, y0=236, w=18, h=32, step=21, count=2, prefix="flow"
    )
    FLOW_DOT: tuple[int, int] = (284, 265)
    FLOW_DECIMAL = BoxDigitLayout(
        x0=290, y0=236, w=18, h=32, step=21, count=3, prefix="flow_dec"
    )
    FLOW_UNIT_POS: tuple[int, int] = (356, 244)


def overlay_lcd_digits(
    canvas: Image,
    digit_states: dict[str, float],
    lcd_color: str = "black",
    lcd_bg: str = "grey",
    lcd_font: str = "builtin",
    has_flow_display: bool = False,
    has_decimal_dot: bool = False,
) -> None:
    """Render authentic 7-segment or 14-segment LCD digits inside the LCD counter window(s)."""
    # Note: Coordinates assume canonical 640x480 simulation canvas; resizing occurs in stage 5
    if canvas.size != (640, 480):
        pass

    theme = resolve_lcd_theme(lcd_color, lcd_bg)
    active_col = theme["active"]
    ghost_col = theme["ghost"]

    draw = PIL.ImageDraw.Draw(canvas)
    font_key = (lcd_font or "builtin").lower().strip()
    font_cfg = LCD_FONTS.get(font_key)
    use_font = font_cfg is not None and font_cfg.get("category") in (
        "7seg",
        "14seg",
    )

    def _render_box_digit(x: int, y: int, w: int, h: int, raw_val: int | float) -> None:
        int_val = int(raw_val)
        val = int_val if int_val in (-1, -2) else int_val % 10
        if use_font and font_cfg is not None:
            char_str = "-" if val == -1 else (" " if val == -2 else str(val))
            draw_7segment_font_digit(
                draw=draw,
                x=x,
                y=y,
                w=w,
                h=h,
                char_str=char_str,
                font_cfg=font_cfg,
                active_color=active_col,
                ghost_color=ghost_col,
            )
        else:
            px = max(2, round(w * 0.09))
            py = max(3, round(h * 0.085))
            draw_7segment_digit(
                draw,
                x=x + px,
                y=y + py,
                w=w - px * 2,
                h=h - py * 2,
                digit=val,
                active_color=active_col,
                ghost_color=ghost_col,
                slant=0,
            )

    if has_flow_display:
        # Dual-line ultrasonic smart meter (Axioma W1 style unified screen)
        # Note: has_decimal_dot is implicit in dual-line LCD layout (VOLUME_DOT & FLOW_DOT)
        layout = DigitalFlowScreenLayout

        # 1. Subtle horizontal divider across the LCD screen
        draw.line(layout.DIVIDER_LINE, fill=ghost_col, width=1)

        # 2. Battery status icon
        draw.rectangle(layout.BATTERY_OUTLINE, outline=ghost_col, width=1)
        draw.rectangle(layout.BATTERY_TIP, fill=ghost_col)
        draw.rectangle(layout.BATTERY_FILL, fill=ghost_col)

        # 3. Flow direction indicator arrow
        flow_v = 0.0
        if "flow1" in digit_states:
            flow_v = (
                digit_states.get("flow1", 0.0) * 10.0
                + digit_states.get("flow2", 0.0)
                + digit_states.get("flow_dec1", 0.0) * 0.1
            )
        arrow_col = active_col if flow_v > 0.001 else ghost_col
        draw.polygon(layout.ARROW_POINTS, fill=arrow_col)

        # 4. Main cumulative volume line (6 large integer digits)
        for i in range(layout.VOLUME_INTEGER.count):
            bx, by, bw, bh = layout.VOLUME_INTEGER.get_box(i)
            _render_box_digit(
                bx,
                by,
                bw,
                bh,
                digit_states.get(layout.VOLUME_INTEGER.digit_name(i), 0.0),
            )

        # Main volume decimal dot
        dot_x, dot_y = layout.VOLUME_DOT
        draw.ellipse((dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2), fill=active_col)

        # 3 smaller decimal digits (w=18, h=32, baseline-aligned at y=168)
        for i in range(layout.VOLUME_DECIMAL.count):
            bx, by, bw, bh = layout.VOLUME_DECIMAL.get_box(i)
            _render_box_digit(
                bx,
                by,
                bw,
                bh,
                digit_states.get(layout.VOLUME_DECIMAL.digit_name(i), 0.0),
            )

        # Main volume unit label
        font_unit = PIL.ImageFont.load_default(size=12)
        draw.text(layout.VOLUME_UNIT_POS, "m3", fill=active_col, font=font_unit)

        # 5. Instantaneous flow rate line
        font_small = PIL.ImageFont.load_default(size=10)
        draw.text(layout.FLOW_LABEL_POS, "FLOW", fill=active_col, font=font_small)

        # 2 flow integer digits
        for i in range(layout.FLOW_INTEGER.count):
            bx, by, bw, bh = layout.FLOW_INTEGER.get_box(i)
            _render_box_digit(
                bx, by, bw, bh, digit_states.get(layout.FLOW_INTEGER.digit_name(i), 0.0)
            )

        # Flow rate decimal dot
        f_dot_x, f_dot_y = layout.FLOW_DOT
        draw.ellipse(
            (f_dot_x - 2, f_dot_y - 2, f_dot_x + 2, f_dot_y + 2), fill=active_col
        )

        # 3 flow decimal digits
        for i in range(layout.FLOW_DECIMAL.count):
            bx, by, bw, bh = layout.FLOW_DECIMAL.get_box(i)
            _render_box_digit(
                bx, by, bw, bh, digit_states.get(layout.FLOW_DECIMAL.digit_name(i), 0.0)
            )

        # Flow unit label
        draw.text(layout.FLOW_UNIT_POS, "m3/h", fill=active_col, font=font_unit)
    else:
        # Standard 5-digit LCD window
        center_x = canvas.width // 2
        center_y = canvas.height // 2
        win_w = 264
        win_x = center_x - win_w // 2
        win_y = center_y - 100

        dw, dh = 39, 66
        gap = 10
        start_dx = win_x + 14
        dy = win_y + 10

        for i in range(5):
            digit_name = f"digit{i+1}"
            x = start_dx + i * (dw + gap)
            y = dy
            _render_box_digit(x, y, dw, dh, digit_states.get(digit_name, 0.0))

        if has_decimal_dot:
            dot_x = start_dx + 4 * (dw + gap) - 5
            dot_y = dy + dh - 10
            draw.ellipse((dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3), fill=active_col)
