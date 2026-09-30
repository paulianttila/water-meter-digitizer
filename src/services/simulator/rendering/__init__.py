"""Simulator rendering modules (digits, dials, and optical effects)."""

from .dials import draw_needle, draw_needle_patch, overlay_analog_needles
from .digits import (
    LCD_FONT_OPTIONS,
    LCD_FONTS,
    SEGMENTS_7,
    draw_7segment_digit,
    draw_7segment_font_digit,
    get_lcd_font,
    overlay_lcd_digits,
    resolve_lcd_bg_color,
    resolve_lcd_theme,
)
from .effects import apply_perturbations, inject_glare

__all__ = [
    "LCD_FONTS",
    "LCD_FONT_OPTIONS",
    "SEGMENTS_7",
    "apply_perturbations",
    "draw_7segment_digit",
    "draw_7segment_font_digit",
    "draw_needle",
    "draw_needle_patch",
    "get_lcd_font",
    "inject_glare",
    "overlay_analog_needles",
    "overlay_lcd_digits",
    "resolve_lcd_bg_color",
    "resolve_lcd_theme",
]
