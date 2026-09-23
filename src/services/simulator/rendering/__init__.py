"""Simulator rendering modules (digits, dials, and optical effects)."""

from .dials import draw_needle_patch, overlay_analog_needles
from .digits import (
    SEGMENTS_7,
    draw_7segment_digit,
    overlay_lcd_digits,
    resolve_lcd_bg_color,
    resolve_lcd_theme,
)
from .effects import apply_perturbations, inject_glare

__all__ = [
    "SEGMENTS_7",
    "apply_perturbations",
    "draw_7segment_digit",
    "draw_needle_patch",
    "inject_glare",
    "overlay_analog_needles",
    "overlay_lcd_digits",
    "resolve_lcd_bg_color",
    "resolve_lcd_theme",
]
