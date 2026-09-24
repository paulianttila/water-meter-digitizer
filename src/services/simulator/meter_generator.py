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
from typing import Any, ClassVar

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from PIL.Image import Image

from configuration import Config
from data_classes import ImagePosition, MeterConfig, RefImage
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
    overlay_lcd_digits as _overlay_lcd_digits_fn,
)
from services.simulator.rendering import (
    resolve_lcd_bg_color as _resolve_lcd_bg_color_fn,
)
from services.simulator.rendering import (
    resolve_lcd_theme as _resolve_lcd_theme_fn,
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

    _base_cache: ClassVar[dict[tuple[int, int, str, str], Image]] = {}

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
        width: int = 640,
        height: int = 480,
        custom_digital_values: dict[str, float] | None = None,
        custom_analog_values: dict[str, float] | None = None,
    ) -> Image:
        """Generate a complete rounded water meter image with 5 LCD digits, 4 dials, and 3 ref targets."""
        # 1. Parse reading into 5 digits and 4 dials
        digit_states, dial_states = self._parse_meter_values(
            value, custom_digital_values, custom_analog_values
        )

        # 2. Build Base Rounded Water Meter Canvas on Canonical 640x480 Frame (using template cache)
        base_w, base_h = 640, 480
        if base_image is not None:
            canvas = base_image.copy().convert("RGB")
        else:
            cache_key = (
                base_w,
                base_h,
                meter_bg.lower().strip(),
                lcd_bg.lower().strip(),
            )
            if cache_key not in self._base_cache:
                self._base_cache[cache_key] = self._draw_meter_base(
                    base_w, base_h, lcd_bg=lcd_bg, meter_bg=meter_bg
                )
            canvas = self._base_cache[cache_key].copy()

        # 3. Draw 5 LCD Digital Counter Drums
        self._overlay_lcd_digits(
            canvas, digit_states, lcd_color=lcd_color, lcd_bg=lcd_bg
        )

        # 4. Draw 4 Analog Dial Needles
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
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Decompose meter reading into 5 digits and 4 dial values."""
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

        # 5 digital digits
        dig_names = ["digit1", "digit2", "digit3", "digit4", "digit5"]
        digit_states: dict[str, float] = {}
        if is_negative:
            # First digit is minus sign (-1.0), remaining 4 are padded from integer part
            pad_int = integer_part.zfill(4)[-4:]
            digit_states["digit1"] = -1.0
            for i, name in enumerate(dig_names[1:]):
                digit_states[name] = _parse_digit_char(pad_int[i])
        else:
            pad_int = integer_part.zfill(5)[-5:]
            for i, name in enumerate(dig_names):
                digit_states[name] = _parse_digit_char(pad_int[i])

        # 4 analog dials
        ana_names = ["analog1", "analog2", "analog3", "analog4"]
        pad_frac = (fractional_part + "00000")[:5]
        dial_states: dict[str, float] = {}
        for i, name in enumerate(ana_names):
            if i < len(pad_frac):
                chunk = pad_frac[i : i + 2] if len(pad_frac) > i + 1 else pad_frac[i]
                try:
                    sub_val = float(chunk) / 10.0 if len(chunk) > 1 else float(chunk)
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
    ) -> Image:
        """Draw complete circular water meter housing, LCD window, and dial faces."""
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

        # 1. LCD Counter Bezel & Window (Enlarged with increased spacing)
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

        # 3. 4 Analog Dial Faces with 0-9 Graduations and Multiplier Markers
        dial_configs = [
            (430, 300, "x0.1"),
            (360, 365, "x0.01"),
            (280, 365, "x0.001"),
            (210, 300, "x0.0001"),
        ]
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
                fill=(210, 40, 40) if meter_bg.lower() == "dark" else (180, 30, 30),
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
    ) -> None:
        """Render 5 authentic 7-segment LCD digits inside the LCD counter window."""
        _overlay_lcd_digits_fn(canvas, digit_states, lcd_color, lcd_bg)

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
    ) -> tuple[list[ImagePosition], list[ImagePosition], list[RefImage]]:
        """Compute scaled digital, analog, and reference marker ROIs for given resolution."""
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

        base_win_w = 264
        base_win_x = 320 - base_win_w // 2
        base_win_y = 240 - 100
        base_dw, base_dh = 39, 66
        base_gap = 10
        base_start_dx = base_win_x + 14
        base_dy = base_win_y + 10

        cut_digits = []
        for i in range(5):
            bx = base_start_dx + i * (base_dw + base_gap)
            by = base_dy
            sx, sy, sw, sh = _scale_pos(bx, by, base_dw, base_dh)
            cut_digits.append(ImagePosition(name=f"digit{i+1}", x=sx, y=sy, w=sw, h=sh))

        base_dial_size = 76
        dial_centers = [
            ("analog1", 430, 300),
            ("analog2", 360, 365),
            ("analog3", 280, 365),
            ("analog4", 210, 300),
        ]
        cut_analogs = []
        for name, cx, cy in dial_centers:
            bx = cx - base_dial_size // 2
            by = cy - base_dial_size // 2
            sx, sy, sw, sh = _scale_pos(bx, by, base_dial_size, base_dial_size)
            cut_analogs.append(ImagePosition(name=name, x=sx, y=sy, w=sw, h=sh))

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
    ) -> tuple[Image, Config]:
        """Create a complete standardized rounded water meter canvas and matching Config."""
        gen = cls(config=config)
        img = gen.generate(value="00000.0000", width=width, height=height)

        cut_digits, cut_analogs, ref_images = cls._compute_standard_rois(width, height)

        cfg = Config(
            digital_readout=Config().digital_readout.model_copy(
                update={"cut_images": cut_digits, "enabled": True}
            ),
            analog_readout=Config().analog_readout.model_copy(
                update={"cut_images": cut_analogs, "enabled": True}
            ),
            alignment=Config().alignment.model_copy(update={"ref_images": ref_images}),
            meter_configs=[
                MeterConfig(
                    name="total",
                    format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}",
                    consistency_enabled=True,
                    allow_negative_rates=False,
                    max_rate_value=0.2,
                    use_previous_value=True,
                    unit="m³",
                )
            ],
        )

        return img, cfg

    @classmethod
    def create_mock_meter_config(
        cls,
        width: int = 640,
        height: int = 480,
        base_config: Config | None = None,
        url: str = "",
    ) -> Config:
        """Create a dedicated Config matching the procedural mock meter dimensions and ROIs."""
        base = base_config or Config()
        cut_digits, cut_analogs, _ = cls._compute_standard_rois(width, height)

        dig_update: dict[str, Any] = {"cut_images": cut_digits, "enabled": True}
        if not base.digital_readout.model_file:
            dig_update["model_file"] = (
                "config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
            )
        if not base.digital_readout.model:
            dig_update["model"] = "digital"

        ana_update: dict[str, Any] = {"cut_images": cut_analogs, "enabled": True}
        if not base.analog_readout.model_file:
            ana_update["model_file"] = (
                "config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite"
            )
        if not base.analog_readout.model:
            ana_update["model"] = "analog"

        img_src_update: dict[str, Any] = {}
        if url:
            img_src_update["url"] = url

        return base.model_copy(
            update={
                "digital_readout": base.digital_readout.model_copy(update=dig_update),
                "analog_readout": base.analog_readout.model_copy(update=ana_update),
                "alignment": base.alignment.model_copy(
                    update={
                        "ref_images": [],
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
                "meter_configs": [
                    MeterConfig(
                        name="total",
                        format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}{analog3}{analog4}",
                        consistency_enabled=False,
                        allow_negative_rates=True,
                        use_previous_value=False,
                        unit="m³",
                    )
                ],
            }
        )
