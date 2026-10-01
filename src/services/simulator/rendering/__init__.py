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
from .drum import (
    DRUM_THEME_OPTIONS,
    DRUM_THEMES,
    compute_drum_wheel_positions,
    draw_drum_bezel,
    draw_drum_wheel,
    get_drum_font,
    overlay_drum_counter,
)
from .effects import apply_perturbations, inject_glare

__all__ = [
    "DRUM_THEMES",
    "DRUM_THEME_OPTIONS",
    "LCD_FONTS",
    "LCD_FONT_OPTIONS",
    "SEGMENTS_7",
    "apply_perturbations",
    "compute_drum_wheel_positions",
    "draw_7segment_digit",
    "draw_7segment_font_digit",
    "draw_drum_bezel",
    "draw_drum_wheel",
    "draw_needle",
    "draw_needle_patch",
    "get_drum_font",
    "get_lcd_font",
    "inject_glare",
    "overlay_analog_needles",
    "overlay_drum_counter",
    "overlay_lcd_digits",
    "resolve_lcd_bg_color",
    "resolve_lcd_theme",
]
