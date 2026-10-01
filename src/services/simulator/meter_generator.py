"""Water Meter Picture Generator for simulation, calibration, and automated testing.

Generates a complete, standardized rounded water meter face from scratch:
- 5 Digital Drums with authentic 7-segment LCD font rendering
- 4 Circular Analog Dials with rotating pointer needles
- 3 Reference Crosshair Targets for computer vision alignment
- Real-world optical perturbations (glare, rotation, noise, blur, lighting)

Completely autonomous and decoupled from config.ini.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, ClassVar

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from PIL.Image import Image

from configuration import Config
from data_classes import ImagePosition, MeterConfig, RefImage
from services.simulator.rendering import (
    DigitalFlowScreenLayout,
)
from services.simulator.rendering import (
    apply_perturbations as _apply_perturbations,
)
from services.simulator.rendering import (
    draw_7segment_digit as _draw_7segment_digit_fn,
)
from services.simulator.rendering import (
    draw_needle_patch as _draw_needle_patch_fn,
)
from services.simulator.rendering import (
    inject_glare as _inject_glare_fn,
)
from services.simulator.rendering import (
    overlay_analog_needles as _overlay_analog_needles_fn,
)
from services.simulator.rendering import (
    overlay_drum_counter as _overlay_drum_counter_fn,
)
from services.simulator.rendering import (
    overlay_lcd_digits as _overlay_lcd_digits_fn,
)
from services.simulator.rendering import (
    resolve_lcd_bg_color as _resolve_lcd_bg_color_fn,
)
from services.simulator.rendering import (
    resolve_lcd_theme as _resolve_lcd_theme_fn,
)
from services.simulator.templates import (
    STANDARD_DIAL_CONFIGS,
    MeterTemplate,
    get_meter_template,
)

METER_BG_THEMES: dict[str, dict[str, Any]] = {
    "white": {
        "dial": (250, 252, 255),
        "casing": (244, 246, 249),
        "canvas": (222, 225, 230),
        "dial_sub": (252, 252, 254),
        "text": (45, 50, 60),
        "text_sub": (75, 85, 95),
        "border": (170, 175, 185),
    },
    "grey": {
        "dial": (222, 226, 232),
        "casing": (205, 210, 218),
        "canvas": (195, 200, 208),
        "dial_sub": (228, 232, 238),
        "text": (35, 40, 50),
        "text_sub": (65, 75, 85),
        "border": (150, 155, 165),
    },
    "blue": {
        "dial": (228, 238, 248),
        "casing": (195, 215, 238),
        "canvas": (190, 205, 220),
        "dial_sub": (235, 242, 252),
        "text": (25, 45, 75),
        "text_sub": (55, 75, 105),
        "border": (145, 175, 205),
    },
    "brass": {
        "dial": (246, 238, 215),
        "casing": (228, 208, 168),
        "canvas": (205, 192, 162),
        "dial_sub": (250, 244, 226),
        "text": (50, 42, 28),
        "text_sub": (80, 70, 50),
        "border": (180, 155, 110),
    },
    "dark": {
        "dial": (32, 36, 44),
        "casing": (22, 26, 32),
        "canvas": (15, 18, 24),
        "dial_sub": (40, 45, 55),
        "text": (225, 230, 240),
        "text_sub": (170, 180, 195),
        "border": (70, 78, 90),
    },
    "metal": {
        "dial": (214, 220, 228),
        "casing": (188, 195, 205),
        "canvas": (172, 180, 190),
        "dial_sub": (224, 230, 238),
        "text": (28, 34, 44),
        "text_sub": (58, 68, 80),
        "border": (135, 145, 160),
    },
    "worn": {
        "dial": (236, 226, 204),
        "casing": (210, 196, 168),
        "canvas": (192, 180, 156),
        "dial_sub": (240, 232, 212),
        "text": (60, 50, 40),
        "text_sub": (90, 80, 68),
        "border": (160, 145, 120),
    },
    "aged": {
        "dial": (242, 236, 220),
        "casing": (230, 222, 202),
        "canvas": (212, 205, 188),
        "dial_sub": (245, 240, 228),
        "text": (55, 48, 38),
        "text_sub": (85, 76, 62),
        "border": (175, 165, 145),
    },
}


class MeterImageGenerator:
    """Procedural rounded water meter image generator."""

    _base_cache: ClassVar[dict[tuple[int, int, str, str, str], Image]] = {}

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    @classmethod
    def clear_base_cache(cls) -> None:
        """Clear the cached static base meter images."""
        cls._base_cache.clear()

    # -------------------------------------------------------------------------
    # Public Generation API
    # -------------------------------------------------------------------------

    def generate(
        self,
        value: str | float = "00452.91241",
        base_image: Image | None = None,
        rotate: float = 0.0,
        glare: bool = False,
        glare_pos: tuple[float, float] | None = None,
        glare_intensity: float = 1.0,
        noise: float = 0.0,
        brightness: float = 1.0,
        contrast: float = 1.0,
        blur: float = 0.0,
        lcd_color: str = "black",
        lcd_bg: str = "grey",
        meter_bg: str = "white",
        needle_color: str = "red",
        lcd_font: str = "builtin",
        counter_type: str = "lcd",
        drum_style: str = "standard",
        drum_carry: str = "geneva",
        width: int = 640,
        height: int = 480,
        custom_digital_values: dict[str, float] | None = None,
        custom_analog_values: dict[str, float] | None = None,
        meter_type: str | None = None,
        flow_value: str | float | None = None,
    ) -> Image:
        """Generate a complete rounded water meter image driven by modular meter templates."""
        # Resolve active template: meter_type takes precedence, fallback to default mechanical_dials
        tpl = (
            get_meter_template(meter_type)
            if meter_type
            else get_meter_template("mechanical_dials")
        )
        effective_counter_type = (
            counter_type if (meter_type is None and counter_type) else tpl.counter_type
        )

        # 1. Parse reading into digital digits and analog dials
        digit_states, dial_states = self._parse_meter_values(
            value,
            custom_digital_values,
            custom_analog_values,
            counter_type=effective_counter_type,
            meter_type=tpl.id,
            flow_value=flow_value,
        )

        # 2. Build Base Rounded Water Meter Canvas on Canonical 640x480 Frame (using template cache)
        base_w, base_h = 640, 480
        if base_image is not None:
            canvas = base_image.copy().convert("RGB")
        else:
            cache_key: tuple[Any, ...] = (
                base_w,
                base_h,
                meter_bg.lower().strip(),
                lcd_bg.lower().strip(),
            )
            if tpl.id != "mechanical_dials":
                cache_key = (*cache_key, tpl.id)
            if cache_key not in self._base_cache:
                self._base_cache[cache_key] = self._draw_meter_base(
                    base_w, base_h, lcd_bg=lcd_bg, meter_bg=meter_bg, template=tpl
                )
            canvas = self._base_cache[cache_key].copy()

        # 3. Draw Digital Counter (LCD or Mechanical Drum)
        if effective_counter_type == "drum":
            self._overlay_drum_counter(
                canvas,
                digit_states,
                drum_style=drum_style,
                drum_carry=drum_carry,
                decimal_wheels=tpl.drum_decimals,
                has_decimal_dot=tpl.has_decimal_dot,
            )
        else:
            self._overlay_lcd_digits(
                canvas,
                digit_states,
                lcd_color=lcd_color,
                lcd_bg=lcd_bg,
                lcd_font=lcd_font,
                has_flow_display=tpl.has_flow_display,
                has_decimal_dot=tpl.has_decimal_dot,
            )

        # 4. Draw 4 Analog Dial Needles (if enabled for this template)
        if tpl.has_dials:
            self._overlay_analog_needles(canvas, dial_states, needle_color=needle_color)

        # 5. Scale to Target Resolution (if different from canonical 640x480)
        target_w = max(32, int(width))
        target_h = max(32, int(height))
        scaled_glare_pos = glare_pos
        if glare_pos is not None:
            gx, gy = glare_pos
            if 0.0 <= gx <= 1.0 and 0.0 <= gy <= 1.0:
                scaled_glare_pos = (gx, gy)
            elif canvas.size != (target_w, target_h):
                scaled_glare_pos = (
                    gx * (target_w / float(base_w)),
                    gy * (target_h / float(base_h)),
                )

        if canvas.size != (target_w, target_h):
            canvas = canvas.resize(
                (target_w, target_h), resample=PIL.Image.Resampling.LANCZOS
            )

        # 6. Apply Optical Perturbations at Target Resolution
        theme = self._resolve_meter_bg_theme(meter_bg)
        canvas = self.apply_perturbations(
            canvas,
            rotate=rotate,
            glare=glare,
            glare_pos=scaled_glare_pos,
            glare_intensity=glare_intensity,
            noise=noise,
            brightness=brightness,
            contrast=contrast,
            blur=blur,
            fillcolor=theme.get("canvas"),
        )

        return canvas

    def generate_sequence(
        self,
        start_value: float,
        rate_per_frame: float,
        count: int,
        **kwargs: Any,
    ) -> list[Image]:
        """Generate a consecutive sequence of meter images simulating continuous flow."""
        frames = []
        curr_val = start_value
        for _ in range(count):
            # 011.5f provides 5 integer and 5 decimal digits with fixed zero-padding;
            # _parse_meter_values safely extracts the appropriate subset per template
            val_str = f"{curr_val:011.5f}"
            img = self.generate(value=val_str, **kwargs)
            frames.append(img)
            curr_val += rate_per_frame
        return frames

    # -------------------------------------------------------------------------
    # Value Parsing
    # -------------------------------------------------------------------------

    def _parse_meter_values(
        self,
        value: str | float,
        custom_dig: dict[str, float] | None = None,
        custom_ana: dict[str, float] | None = None,
        counter_type: str = "lcd",
        meter_type: str | None = None,
        flow_value: str | float | None = None,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Decompose meter reading into digits and dial values based on active MeterTemplate."""
        tpl = (
            get_meter_template(meter_type)
            if meter_type
            else get_meter_template("mechanical_dials")
        )
        val_str = str(value).strip()
        is_negative = val_str.startswith("-")
        clean_val_str = val_str.lstrip("-") if is_negative else val_str
        parts = clean_val_str.split(".")
        integer_part = parts[0]
        fractional_part = parts[1] if len(parts) > 1 else ""

        def _parse_digit_char(c: str) -> float:
            if c.isdigit():
                return float(c)
            if c == "-":
                return -1.0
            return -2.0  # Blank / off segment for spaces, unreadable characters, etc.

        digit_states: dict[str, float] = {}
        dial_states: dict[str, float] = {}

        if tpl.has_flow_display:
            # 6 integer volume digits (digit1..6)
            pad_vol_int = integer_part.zfill(6)[-6:]
            for i in range(6):
                digit_states[f"digit{i+1}"] = _parse_digit_char(pad_vol_int[i])
            if is_negative:
                digit_states["digit1"] = -1.0

            # 3 decimal volume digits (decimal1..3)
            pad_vol_dec = (fractional_part + "000")[:3]
            for i in range(3):
                digit_states[f"decimal{i+1}"] = _parse_digit_char(pad_vol_dec[i])

            # Instantaneous flow rate (flow1..2, flow_dec1..3)
            f_str = str(flow_value if flow_value is not None else "00.125").strip()
            f_is_neg = f_str.startswith("-")
            f_clean = f_str.lstrip("-") if f_is_neg else f_str
            f_parts = f_clean.split(".")
            f_int = f_parts[0].zfill(2)[-2:]
            f_dec = (f_parts[1] + "000")[:3] if len(f_parts) > 1 else "000"

            digit_states["flow1"] = -1.0 if f_is_neg else _parse_digit_char(f_int[0])
            digit_states["flow2"] = _parse_digit_char(f_int[1])
            digit_states["flow_dec1"] = _parse_digit_char(f_dec[0])
            digit_states["flow_dec2"] = _parse_digit_char(f_dec[1])
            digit_states["flow_dec3"] = _parse_digit_char(f_dec[2])

        elif tpl.id == "mechanical_roller":
            # 4 integer black drums (digit1..4) + 1 red decimal drum (digit5)
            pad_int = integer_part.zfill(5)[-5:]
            for i in range(4):
                digit_states[f"digit{i+1}"] = _parse_digit_char(pad_int[i])
            base_dec = _parse_digit_char(pad_int[4])
            if fractional_part and base_dec >= 0:
                try:
                    frac_val = float(f"0.{fractional_part}")
                    base_dec = round(base_dec + frac_val, 4)
                except ValueError:
                    pass
            digit_states["digit5"] = base_dec

        elif counter_type == "drum":
            # 5 integer drums (digit1..5)
            pad_int = integer_part.zfill(5)[-5:]
            for i in range(5):
                digit_states[f"digit{i+1}"] = _parse_digit_char(pad_int[i])
            if fractional_part and digit_states.get("digit5", 0.0) >= 0:
                try:
                    frac_val = float(f"0.{fractional_part}")
                    digit_states["digit5"] = round(digit_states["digit5"] + frac_val, 4)
                except ValueError:
                    pass

        else:
            # Standard single-line LCD (digit1..5)
            dig_names = ["digit1", "digit2", "digit3", "digit4", "digit5"]
            if is_negative:
                pad_int = integer_part.zfill(4)[-4:]
                digit_states["digit1"] = -1.0
                for i, name in enumerate(dig_names[1:]):
                    digit_states[name] = _parse_digit_char(pad_int[i])
            else:
                pad_int = integer_part.zfill(5)[-5:]
                for i, name in enumerate(dig_names):
                    digit_states[name] = _parse_digit_char(pad_int[i])

        if tpl.has_dials:
            ana_names = ["analog1", "analog2", "analog3", "analog4"]
            pad_frac = (fractional_part + "00000")[:5]
            for i, name in enumerate(ana_names):
                if i < len(pad_frac):
                    chunk = (
                        pad_frac[i : i + 2] if len(pad_frac) > i + 1 else pad_frac[i]
                    )
                    try:
                        sub_val = (
                            float(chunk) / 10.0 if len(chunk) > 1 else float(chunk)
                        )
                    except ValueError:
                        sub_val = 0.0
                    dial_states[name] = sub_val
                else:
                    dial_states[name] = 0.0

        if custom_dig:
            digit_states.update(custom_dig)
        if custom_ana:
            dial_states.update(custom_ana)

        return digit_states, dial_states

    # -------------------------------------------------------------------------
    # Procedural Meter Canvas Drawing
    # -------------------------------------------------------------------------

    def _draw_meter_base(
        self,
        width: int = 640,
        height: int = 480,
        lcd_bg: str = "grey",
        meter_bg: str = "white",
        template: MeterTemplate | None = None,
    ) -> Image:
        """Draw complete circular water meter housing, counter window, and dials or flow display."""
        tpl = template or get_meter_template("mechanical_dials")
        theme = self._resolve_meter_bg_theme(meter_bg)
        img = PIL.Image.new("RGB", (width, height), theme["canvas"])
        draw = PIL.ImageDraw.Draw(img)

        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 16

        # Outer casing ring / mounting flange
        draw.ellipse(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ),
            fill=theme["casing"],
            outline=(50, 55, 65) if meter_bg.lower() != "dark" else (10, 12, 16),
            width=9,
        )

        # Inner bezel rim with metallic gradient feel
        inner_r = radius - 14
        draw.ellipse(
            (
                center_x - inner_r,
                center_y - inner_r,
                center_x + inner_r,
                center_y + inner_r,
            ),
            outline=theme["border"],
            width=2,
        )

        # Dial Face Background
        draw.ellipse(
            (
                center_x - inner_r + 2,
                center_y - inner_r + 2,
                center_x + inner_r - 2,
                center_y + inner_r - 2,
            ),
            fill=theme["dial"],
        )

        # Text labels and water meter rating with custom font sizes
        font_title = PIL.ImageFont.load_default(size=20)
        font_sub = PIL.ImageFont.load_default(size=16)
        font = PIL.ImageFont.load_default(size=14)
        font_small = PIL.ImageFont.load_default(size=10)

        text_col = theme["text"]
        text_sub_col = theme["text_sub"]

        draw.text(
            (center_x, center_y - 148),
            "AQUA-DIGITIZER",
            fill=text_col,
            font=font_title,
            anchor="mm",
        )
        draw.text(
            (center_x, center_y - 130),
            "m3  Qn 1.5",
            fill=text_sub_col,
            font=font_sub,
            anchor="mm",
        )

        # 1. LCD Counter Bezel & Window
        if tpl.has_flow_display:
            # Unified panoramic LCD screen for dual-line ultrasonic meters
            win_w, win_h = 286, 166
            win_x = center_x - win_w // 2
            win_y = 134
        else:
            win_w, win_h = 264, 86
            win_x = center_x - win_w // 2
            win_y = center_y - 100

        # Outer LCD dark casing / raised bezel
        draw.rectangle(
            (win_x, win_y, win_x + win_w, win_y + win_h),
            fill=(22, 25, 29),
            outline=(75, 80, 92),
            width=4,
        )

        # Inner LCD glass area
        bg_col = self._resolve_lcd_bg_color(lcd_bg)
        draw.rectangle(
            (win_x + 4, win_y + 4, win_x + win_w - 4, win_y + win_h - 4),
            fill=bg_col,
            outline=(50, 55, 62),
            width=1,
        )

        # 2. Realistic Reference Markers (Model text, Unit mark, Serial Number)
        # Ref0: Model info (Left)
        draw.text((120, 227), "MOD", fill=text_col, font=font)
        draw.text((118, 239), "AQ-20", fill=text_sub_col, font=font)

        # Ref1: m³ Volume unit & pressure rating (Top-Right, shifted 50px down to y=170)
        draw.text((475, 173), "m3", fill=text_col, font=font_title)
        draw.text((472, 200), "PN16", fill=text_sub_col, font=font)

        # Ref2: Serial Number & Barcode (Bottom-Center, shifted 10px up to y=410)
        barcode_col = text_col
        for bx in range(280, 298, 3):
            draw.line((bx, 414, bx, 434), fill=barcode_col, width=2)
        draw.text((303, 417), "SN:89421", fill=text_col, font=font)

        # 3. Dial Faces or Clean Faceplate with Flow Indicator / Display
        if not tpl.has_dials:
            if tpl.has_flow_indicator:
                # Central rotating flow indicator spinner cog/star
                scx, scy, sr = center_x, 320, 26
                draw.ellipse(
                    (scx - sr, scy - sr, scx + sr, scy + sr),
                    fill=theme["dial_sub"],
                    outline=theme["border"],
                    width=2,
                )
                for b in range(6):
                    b_ang = math.radians(b * 60)
                    bx = scx + int(sr * 0.8 * math.cos(b_ang))
                    by = scy + int(sr * 0.8 * math.sin(b_ang))
                    draw.line(
                        [(scx, scy), (bx, by)],
                        fill=(
                            (210, 30, 30)
                            if meter_bg.lower() != "dark"
                            else (240, 60, 60)
                        ),
                        width=3,
                    )
                draw.ellipse(
                    (scx - 5, scy - 5, scx + 5, scy + 5),
                    fill=(45, 48, 55),
                    outline=theme["border"],
                    width=1,
                )
                draw.text(
                    (center_x, 355),
                    "▶ FLOW ▶",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
                draw.text(
                    (center_x, 372),
                    "CLASS 2  IP68",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
            elif tpl.has_flow_display:
                draw.text(
                    (center_x, 345),
                    "ULTRASONIC FLOW SENSOR",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
                draw.text(
                    (center_x, 365),
                    "CLASS 2  IP68  R400",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
            else:
                # Electronic single-line LCD smart meter (no dials, no rotating wheel)
                draw.text(
                    (center_x, 345),
                    "DIGITAL FLOW SENSOR",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
                draw.text(
                    (center_x, 365),
                    "CLASS 2  IP68  SMART",
                    fill=text_sub_col,
                    font=font_small,
                    anchor="mm",
                )
        else:
            dial_configs = STANDARD_DIAL_CONFIGS
            dial_size = 76
            dial_r = dial_size // 2 - 2

            for cx, cy, mult in dial_configs:
                ax, ay = cx - dial_size // 2, cy - dial_size // 2
                draw.ellipse(
                    (ax, ay, ax + dial_size, ay + dial_size),
                    fill=theme["dial_sub"],
                    outline=theme["border"],
                    width=2,
                )

                # Dial Multiplier Marker (e.g. x0.1, x0.01, x0.001, x0.0001)
                tw = len(mult) * 6
                draw.text(
                    (cx - tw // 2, ay - 12),
                    mult,
                    fill=(
                        (210, 40, 40) if meter_bg.lower() == "dark" else (180, 30, 30)
                    ),
                    font=font_small,
                )

                for t in range(10):
                    angle_rad = math.radians(t * 36 - 90)
                    tx1 = cx + int((dial_r - 5) * math.cos(angle_rad))
                    ty1 = cy + int((dial_r - 5) * math.sin(angle_rad))
                    tx2 = cx + int(dial_r * math.cos(angle_rad))
                    ty2 = cy + int(dial_r * math.sin(angle_rad))
                    draw.line(
                        (tx1, ty1, tx2, ty2),
                        fill=text_col,
                        width=2 if t % 2 == 0 else 1,
                    )
                    if t % 2 == 0:
                        nx = cx + int((dial_r - 11) * math.cos(angle_rad)) - 3
                        ny = cy + int((dial_r - 11) * math.sin(angle_rad)) - 4
                        draw.text((nx, ny), str(t), fill=text_col, font=font)

        return img

    # -------------------------------------------------------------------------
    # 7-Segment LCD Digit Rendering Engine
    # -------------------------------------------------------------------------

    def _overlay_lcd_digits(
        self,
        canvas: Image,
        digit_states: dict[str, float],
        lcd_color: str = "black",
        lcd_bg: str = "grey",
        lcd_font: str = "builtin",
        has_flow_display: bool = False,
        has_decimal_dot: bool = False,
    ) -> None:
        """Render authentic 7-segment or 14-segment LCD digits inside the LCD counter window."""
        _overlay_lcd_digits_fn(
            canvas,
            digit_states,
            lcd_color,
            lcd_bg,
            lcd_font=lcd_font,
            has_flow_display=has_flow_display,
            has_decimal_dot=has_decimal_dot,
        )

    def _overlay_drum_counter(
        self,
        canvas: Image,
        digit_states: dict[str, float],
        drum_style: str = "standard",
        drum_carry: str = "geneva",
        decimal_wheels: int | None = None,
        has_decimal_dot: bool | None = None,
    ) -> None:
        """Render mechanical rolling drums inside the aperture window."""
        _overlay_drum_counter_fn(
            canvas,
            digit_states,
            drum_style=drum_style,
            drum_carry=drum_carry,
            decimal_wheels=decimal_wheels,
            has_decimal_dot=has_decimal_dot,
        )

    def _draw_7segment_digit(
        self,
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
        _draw_7segment_digit_fn(
            draw=draw,
            x=x,
            y=y,
            w=w,
            h=h,
            digit=digit,
            active_color=active_color,
            ghost_color=ghost_color,
            slant=slant,
        )

    def _overlay_analog_needles(
        self,
        canvas: Image,
        dial_states: dict[str, float],
        needle_color: str = "red",
    ) -> None:
        """Render rotating needles on the 4 analog dial faces."""
        _overlay_analog_needles_fn(canvas, dial_states, needle_color)

    def _draw_needle_patch(
        self,
        patch: Image,
        width: int,
        height: int,
        value: float,
        needle_color: str = "red",
    ) -> None:
        """Draw pointer needle on an analog dial patch."""
        _draw_needle_patch_fn(patch, width, height, value, needle_color)

    # -------------------------------------------------------------------------
    # Color Resolvers
    # -------------------------------------------------------------------------

    def _resolve_meter_bg_theme(self, meter_bg: str) -> dict[str, Any]:
        key = (meter_bg or "white").lower().strip()
        alias_map = {
            "metal": "metal",
            "metallic": "metal",
            "steel": "metal",
            "zinc": "metal",
            "silver": "metal",
            "gray": "grey",
            "worn": "worn",
            "aged": "worn",
            "weathered": "worn",
            "patina": "worn",
            "vintage": "worn",
            "cream": "worn",
            "gold": "brass",
            "yellow": "brass",
            "black": "dark",
            "light": "white",
        }
        resolved = alias_map.get(key, key)
        return METER_BG_THEMES.get(resolved, METER_BG_THEMES["white"])

    def _resolve_lcd_theme(self, lcd_color: str, lcd_bg: str) -> dict[str, Any]:
        return _resolve_lcd_theme_fn(lcd_color, lcd_bg)

    def _resolve_lcd_bg_color(self, lcd_bg: str) -> tuple[int, int, int]:
        return _resolve_lcd_bg_color_fn(lcd_bg)

    # -------------------------------------------------------------------------
    # Perturbations & Realism Augmentation
    # -------------------------------------------------------------------------

    def apply_perturbations(
        self,
        image: Image,
        rotate: float = 0.0,
        glare: bool = False,
        glare_pos: tuple[float, float] | None = None,
        glare_intensity: float = 1.0,
        noise: float = 0.0,
        brightness: float = 1.0,
        contrast: float = 1.0,
        blur: float = 0.0,
        fillcolor: tuple[int, int, int] | None = None,
    ) -> Image:
        """Apply camera and environmental artifacts for CV robustness testing."""
        return _apply_perturbations(
            image=image,
            rotate=rotate,
            glare=glare,
            glare_pos=glare_pos,
            glare_intensity=glare_intensity,
            noise=noise,
            brightness=brightness,
            contrast=contrast,
            blur=blur,
            fillcolor=fillcolor,
        )

    def _inject_glare(
        self,
        image: Image,
        pos: tuple[float, float] | None = None,
        intensity: float = 1.0,
    ) -> Image:
        """Overlay a specular glare hotspot."""
        return _inject_glare_fn(image, pos, intensity)

    # -------------------------------------------------------------------------
    # Synthetic Template Config Helper
    # -------------------------------------------------------------------------

    @classmethod
    def _compute_standard_rois(
        cls,
        width: int = 640,
        height: int = 480,
        meter_type: str = "mechanical_dials",
    ) -> tuple[list[ImagePosition], list[ImagePosition], list[RefImage]]:
        """Compute scaled digital, analog, and reference marker ROIs matching the selected MeterTemplate."""
        tpl = get_meter_template(meter_type)
        scale_x = width / 640.0
        scale_y = height / 480.0

        def _scale_pos(
            x: int | float, y: int | float, w: int | float, h: int | float
        ) -> tuple[int, int, int, int]:
            return (
                round(x * scale_x),
                round(y * scale_y),
                round(w * scale_x),
                round(h * scale_y),
            )

        cut_digits: list[ImagePosition] = []
        if tpl.has_flow_display:
            for group in (
                DigitalFlowScreenLayout.VOLUME_INTEGER,
                DigitalFlowScreenLayout.VOLUME_DECIMAL,
                DigitalFlowScreenLayout.FLOW_INTEGER,
                DigitalFlowScreenLayout.FLOW_DECIMAL,
            ):
                for i in range(group.count):
                    gx, gy, gw, gh = group.get_box(i)
                    sx, sy, sw, sh = _scale_pos(gx, gy, gw, gh)
                    cut_digits.append(
                        ImagePosition(name=group.digit_name(i), x=sx, y=sy, w=sw, h=sh)
                    )
        else:
            base_win_w = 264
            base_win_x = 320 - base_win_w // 2
            base_win_y = 240 - 100
            base_dw, base_dh = 39, 66
            base_gap = 10
            base_start_dx = base_win_x + 14
            base_dy = base_win_y + 10

            for i in range(5):
                bx = base_start_dx + i * (base_dw + base_gap)
                by = base_dy
                sx, sy, sw, sh = _scale_pos(bx, by, base_dw, base_dh)
                cut_digits.append(
                    ImagePosition(name=f"digit{i+1}", x=sx, y=sy, w=sw, h=sh)
                )

        cut_analogs: list[ImagePosition] = []
        if tpl.has_dials:
            base_dial_size = 76
            for i, (cx, cy, _mult) in enumerate(STANDARD_DIAL_CONFIGS):
                bx = cx - base_dial_size // 2
                by = cy - base_dial_size // 2
                sx, sy, sw, sh = _scale_pos(bx, by, base_dial_size, base_dial_size)
                cut_analogs.append(
                    ImagePosition(name=f"analog{i+1}", x=sx, y=sy, w=sw, h=sh)
                )

        base_refs = [
            ("ref0", 115, 225, 40, 30, "/config/ref0.jpg"),
            ("ref1", 468, 170, 36, 30, "/config/ref1.jpg"),
            ("ref2", 275, 410, 90, 28, "/config/ref2.jpg"),
        ]
        ref_images = []
        for name, rx, ry, rw, rh, fn in base_refs:
            sx, sy, sw, sh = _scale_pos(rx, ry, rw, rh)
            ref_images.append(RefImage(name=name, x=sx, y=sy, w=sw, h=sh, file_name=fn))

        return cut_digits, cut_analogs, ref_images

    @classmethod
    def create_synthetic_template(
        cls,
        width: int = 640,
        height: int = 480,
        config: Config | None = None,
        meter_type: str = "mechanical_dials",
    ) -> tuple[Image, Config]:
        """Create a complete standardized rounded water meter canvas and matching Config."""
        gen = cls(config=config)
        img = gen.generate(
            value="00000.0000", width=width, height=height, meter_type=meter_type
        )
        cfg = cls.create_mock_meter_config(
            width=width, height=height, base_config=config, meter_type=meter_type
        )
        return img, cfg

    @staticmethod
    def _resolve_model_path(path: str, base: Config | None = None) -> str:
        """Resolve a relative neural network model file path to an absolute existing file."""
        if os.path.isfile(path):
            return os.path.abspath(path)

        clean = path.strip()
        sub = clean
        if sub.startswith("config/"):
            sub = sub[len("config/") :]

        candidates: list[Path] = []
        if base:
            if base.config_dir:
                candidates.append(Path(base.config_dir) / clean)
                candidates.append(Path(base.config_dir) / sub)
            if "analog" in clean and base.analog_models_dir:
                sub_ana = (
                    sub[len("neuralnets/analog/") :]
                    if sub.startswith("neuralnets/analog/")
                    else sub
                )
                candidates.append(Path(base.analog_models_dir) / sub_ana)
            if "digital" in clean and base.digital_models_dir:
                sub_dig = (
                    sub[len("neuralnets/digital/") :]
                    if sub.startswith("neuralnets/digital/")
                    else sub
                )
                candidates.append(Path(base.digital_models_dir) / sub_dig)

        cfg_env = os.environ.get("CONFIG_FILE")
        if cfg_env:
            cfg_parent = Path(cfg_env).resolve().parent
            candidates.append(cfg_parent / clean)
            candidates.append(cfg_parent / sub)

        repo_root = Path(__file__).resolve().parents[3]
        candidates.append(repo_root / clean)
        candidates.append(repo_root / "config" / sub)
        candidates.append(Path("/config") / clean)
        candidates.append(Path("/config") / sub)

        for cand in candidates:
            if cand.is_file():
                return str(cand.resolve())

        return path

    @classmethod
    def create_mock_meter_config(
        cls,
        width: int = 640,
        height: int = 480,
        base_config: Config | None = None,
        url: str = "",
        meter_type: str = "mechanical_dials",
    ) -> Config:
        """Create a dedicated Config matching the procedural mock meter dimensions, ROIs, and formulas."""
        base = base_config or Config()
        tpl = get_meter_template(meter_type)
        cut_digits, cut_analogs, ref_images = cls._compute_standard_rois(
            width, height, meter_type=meter_type
        )

        dig_update: dict[str, Any] = {"cut_images": cut_digits, "enabled": True}
        if tpl.counter_type == "drum":
            dig_update["model_file"] = cls._resolve_model_path(
                "config/neuralnets/digital/class100/dig-class100_0168_s2_q.tflite", base
            )
            dig_update["model"] = "auto"
        else:
            dig_update["model_file"] = cls._resolve_model_path(
                "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite", base
            )
            dig_update["model"] = "auto"

        ana_update: dict[str, Any] = {
            "cut_images": cut_analogs,
            "enabled": tpl.has_dials,
        }
        if tpl.has_dials:
            ana_update["model_file"] = cls._resolve_model_path(
                "config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite", base
            )
            ana_update["model"] = "auto"

        img_src_update: dict[str, Any] = {}
        if url:
            img_src_update["url"] = url

        # Define meter formulas matching the template structure
        if tpl.has_dials:
            meter_configs = [
                MeterConfig(
                    name="total",
                    format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}",
                    consistency_enabled=False,
                    allow_negative_rates=True,
                    use_previous_value=False,
                    unit="m³",
                )
            ]
        elif tpl.has_flow_display:
            meter_configs = [
                MeterConfig(
                    name="total",
                    format="{digit1}{digit2}{digit3}{digit4}{digit5}{digit6}.{decimal1}{decimal2}{decimal3}",
                    consistency_enabled=False,
                    allow_negative_rates=True,
                    use_previous_value=False,
                    unit="m³",
                ),
                MeterConfig(
                    name="flow",
                    format="{flow1}{flow2}.{flow_dec1}{flow_dec2}{flow_dec3}",
                    consistency_enabled=False,
                    allow_negative_rates=True,
                    use_previous_value=False,
                    unit="m³/h",
                    detect_negative_sign=True,
                ),
            ]
        elif tpl.id == "mechanical_roller":
            meter_configs = [
                MeterConfig(
                    name="total",
                    format="{digit1}{digit2}{digit3}{digit4}.{digit5}",
                    consistency_enabled=False,
                    allow_negative_rates=True,
                    use_previous_value=False,
                    unit="m³",
                )
            ]
        else:  # digital_single
            meter_configs = [
                MeterConfig(
                    name="total",
                    format="{digit1}{digit2}{digit3}{digit4}{digit5}",
                    consistency_enabled=False,
                    allow_negative_rates=True,
                    use_previous_value=False,
                    unit="m³",
                )
            ]

        return base.model_copy(
            update={
                "digital_readout": base.digital_readout.model_copy(update=dig_update),
                "analog_readout": base.analog_readout.model_copy(update=ana_update),
                "alignment": base.alignment.model_copy(
                    update={
                        "ref_images": ref_images,
                        "rotate_angle": 0.0,
                        "post_rotate_angle": 0.0,
                    }
                ),
                "crop": base.crop.model_copy(update={"enabled": False}),
                "resize": base.resize.model_copy(update={"enabled": False}),
                "image_source": (
                    base.image_source.model_copy(update=img_src_update)
                    if img_src_update
                    else base.image_source
                ),
                "meter_configs": meter_configs,
            }
        )
