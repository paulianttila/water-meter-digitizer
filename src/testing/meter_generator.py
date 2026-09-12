"""Water Meter Picture Generator for simulation, calibration, and automated testing.

Generates a complete, standardized rounded water meter face from scratch:
- 5 Digital Drums with authentic 7-segment LCD font rendering
- 4 Circular Analog Dials with rotating pointer needles
- 3 Reference Crosshair Targets for computer vision alignment
- Real-world optical perturbations (glare, rotation, noise, blur, lighting)

Completely autonomous and decoupled from config.ini.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageEnhance
import PIL.ImageFilter
import PIL.ImageFont
from PIL.Image import Image

from configuration import Config
from data_classes import ImagePosition, MeterConfig, RefImage

logger = logging.getLogger(__name__)

# Segment mapping for 0-9 in standard 7-segment display (a, b, c, d, e, f, g)
SEGMENTS_7 = {
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


class MeterImageGenerator:
    """Procedural rounded water meter image generator."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

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

        # 2. Build Base Rounded Water Meter Canvas
        canvas = (
            base_image.copy().convert("RGB")
            if base_image is not None
            else self._draw_meter_base(width, height, lcd_bg=lcd_bg)
        )

        # 3. Draw 5 LCD Digital Counter Drums
        self._overlay_lcd_digits(
            canvas, digit_states, lcd_color=lcd_color, lcd_bg=lcd_bg
        )

        # 4. Draw 4 Analog Dial Needles
        self._overlay_analog_needles(canvas, dial_states, needle_color=needle_color)

        # 5. Apply Optical Perturbations
        canvas = self.apply_perturbations(
            canvas,
            rotate=rotate,
            glare=glare,
            glare_pos=glare_pos,
            glare_intensity=glare_intensity,
            noise=noise,
            brightness=brightness,
            contrast=contrast,
            blur=blur,
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
        parts = val_str.split(".")
        integer_part = parts[0]
        fractional_part = parts[1] if len(parts) > 1 else ""

        # 5 digital digits
        dig_names = ["digit1", "digit2", "digit3", "digit4", "digit5"]
        pad_int = integer_part.zfill(5)[-5:]
        digit_states: dict[str, float] = {}
        for i, name in enumerate(dig_names):
            digit_states[name] = float(pad_int[i])

        # 4 analog dials
        ana_names = ["analog1", "analog2", "analog3", "analog4"]
        pad_frac = (fractional_part + "00000")[:5]
        dial_states: dict[str, float] = {}
        for i, name in enumerate(ana_names):
            if i < len(pad_frac):
                sub_val = (
                    float(pad_frac[i : i + 2]) / 10.0
                    if len(pad_frac) > i + 1
                    else float(pad_frac[i])
                )
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
    ) -> Image:
        """Draw complete circular water meter housing, LCD window, and dial faces."""
        img = PIL.Image.new("RGB", (width, height), (222, 225, 230))
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
            fill=(244, 246, 249),
            outline=(50, 55, 65),
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
            outline=(170, 175, 185),
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
            fill=(250, 252, 255),
        )

        # Text labels and water meter rating
        font = PIL.ImageFont.load_default()
        draw.text(
            (center_x - 52, center_y - 148),
            "AQUA-DIGITIZER",
            fill=(45, 50, 60),
            font=font,
        )
        draw.text(
            (center_x - 30, center_y - 132),
            "m³  Qn 1.5",
            fill=(75, 85, 95),
            font=font,
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
        draw.text((120, 227), "MOD", fill=(45, 50, 60), font=font)
        draw.text((118, 239), "AQ-20", fill=(30, 35, 45), font=font)

        # Ref1: m³ Volume unit & pressure rating (Top-Right, shifted 50px down to y=170)
        draw.text((475, 173), "m³", fill=(25, 30, 40), font=font)
        draw.text((472, 186), "PN16", fill=(65, 70, 80), font=font)

        # Ref2: Serial Number & Barcode (Bottom-Center, shifted 10px up to y=410)
        for bx in range(280, 298, 3):
            draw.line((bx, 414, bx, 434), fill=(35, 40, 50), width=2)
        draw.text((303, 417), "SN:89421", fill=(25, 30, 40), font=font)

        # 3. 4 Analog Dial Faces with 0-9 Graduations
        dial_centers = [(430, 300), (360, 365), (280, 365), (210, 300)]
        dial_size = 76
        dial_r = dial_size // 2 - 2

        for cx, cy in dial_centers:
            ax, ay = cx - dial_size // 2, cy - dial_size // 2
            draw.ellipse(
                (ax, ay, ax + dial_size, ay + dial_size),
                fill=(252, 252, 254),
                outline=(115, 120, 130),
                width=2,
            )
            for t in range(10):
                angle_rad = math.radians(t * 36 - 90)
                tx1 = cx + int((dial_r - 5) * math.cos(angle_rad))
                ty1 = cy + int((dial_r - 5) * math.sin(angle_rad))
                tx2 = cx + int(dial_r * math.cos(angle_rad))
                ty2 = cy + int(dial_r * math.sin(angle_rad))
                draw.line(
                    (tx1, ty1, tx2, ty2),
                    fill=(35, 40, 50),
                    width=2 if t % 2 == 0 else 1,
                )
                if t % 2 == 0:
                    nx = cx + int((dial_r - 11) * math.cos(angle_rad)) - 3
                    ny = cy + int((dial_r - 11) * math.sin(angle_rad)) - 4
                    draw.text((nx, ny), str(t), fill=(55, 60, 70), font=font)

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
        center_x = canvas.width // 2
        center_y = canvas.height // 2
        win_w = 264
        win_x = center_x - win_w // 2
        win_y = center_y - 100

        dw, dh = 39, 66
        gap = 10
        start_dx = win_x + 14
        dy = win_y + 10

        theme = self._resolve_lcd_theme(lcd_color, lcd_bg)
        active_col = theme["active"]
        ghost_col = theme["ghost"]

        draw = PIL.ImageDraw.Draw(canvas)

        for i in range(5):
            digit_name = f"digit{i+1}"
            val = int(digit_states.get(digit_name, 0.0)) % 10
            x = start_dx + i * (dw + gap)
            y = dy
            self._draw_7segment_digit(
                draw,
                x=x,
                y=y,
                w=dw,
                h=dh,
                digit=val,
                active_color=active_col,
                ghost_color=ghost_col,
                slant=0,
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
        sw = max(4, int(w * 0.17))  # Segment stroke thickness (~6-7px)
        gap = 1  # Tight 1px separation between segments
        half_h = h // 2

        # 7 segment state flags: (a, b, c, d, e, f, g)
        seg_active = SEGMENTS_7.get(digit, (True, True, True, True, True, True, False))

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

    # -------------------------------------------------------------------------
    # Analog Needle Rendering
    # -------------------------------------------------------------------------

    def _overlay_analog_needles(
        self,
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
            self._draw_needle_patch(patch, dial_size, dial_size, val, needle_color)
            canvas.paste(patch, (ax, ay))

    def _draw_needle_patch(
        self,
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

    # -------------------------------------------------------------------------
    # Color Resolvers
    # -------------------------------------------------------------------------

    def _resolve_lcd_theme(self, lcd_color: str, lcd_bg: str) -> dict[str, Any]:
        key = lcd_color.lower()
        if key in COLOR_THEMES:
            theme = COLOR_THEMES[key].copy()
            if lcd_bg:
                theme["bg"] = self._resolve_lcd_bg_color(lcd_bg)
            return theme
        return COLOR_THEMES["black"]

    def _resolve_lcd_bg_color(self, lcd_bg: str) -> tuple[int, int, int]:
        bg_map = {
            "grey": (210, 216, 210),
            "green": (195, 218, 195),
            "amber": (230, 205, 155),
            "dark": (18, 26, 20),
            "blue": (205, 220, 240),
        }
        return bg_map.get(lcd_bg.lower(), (210, 216, 210))

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
    ) -> Image:
        """Apply camera and environmental artifacts for CV robustness testing."""
        img = image.copy()

        if glare:
            img = self._inject_glare(img, glare_pos, glare_intensity)

        if rotate != 0.0:
            img = img.rotate(
                rotate, resample=PIL.Image.Resampling.BICUBIC, expand=False
            )

        if brightness != 1.0:
            img = PIL.ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = PIL.ImageEnhance.Contrast(img).enhance(contrast)

        if blur > 0.0:
            img = img.filter(PIL.ImageFilter.GaussianBlur(radius=blur))

        if noise > 0.0:
            img_np = np.array(img, dtype=np.float32)
            sigma = (noise / 100.0) * 255.0
            gauss = np.random.normal(0, sigma, img_np.shape)
            noisy = np.clip(img_np + gauss, 0, 255).astype(np.uint8)
            img = PIL.Image.fromarray(noisy)

        return img

    def _inject_glare(
        self,
        image: Image,
        pos: tuple[float, float] | None = None,
        intensity: float = 1.0,
    ) -> Image:
        """Overlay a specular glare hotspot."""
        w, h = image.size
        glare_x = int((pos[0] if pos else 0.45) * w)
        glare_y = int((pos[1] if pos else 0.35) * h)
        radius = int(min(w, h) * 0.22)

        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt(((x - glare_x) ** 2) / 1.5 + ((y - glare_y) ** 2))
        glare_mask = np.clip(1.0 - dist_from_center / radius, 0.0, 1.0)
        glare_mask = np.power(glare_mask, 1.8) * min(2.0, max(0.2, intensity))

        img_np = np.array(image, dtype=np.float32)
        for c in range(3):
            img_np[:, :, c] = np.clip(img_np[:, :, c] + glare_mask * 235.0, 0, 255)

        return PIL.Image.fromarray(img_np.astype(np.uint8))

    # -------------------------------------------------------------------------
    # Synthetic Template Config Helper
    # -------------------------------------------------------------------------

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

        center_x = width // 2
        center_y = height // 2
        win_w = 264
        win_x = center_x - win_w // 2
        win_y = center_y - 100
        dw, dh = 39, 66
        gap = 10
        start_dx = win_x + 14
        dy = win_y + 10

        cut_digits = [
            ImagePosition(
                name=f"digit{i+1}", x=start_dx + i * (dw + gap), y=dy, w=dw, h=dh
            )
            for i in range(5)
        ]

        dial_size = 76
        dial_centers = [
            ("analog1", 430, 300),
            ("analog2", 360, 365),
            ("analog3", 280, 365),
            ("analog4", 210, 300),
        ]
        cut_analogs = [
            ImagePosition(
                name=name,
                x=cx - dial_size // 2,
                y=cy - dial_size // 2,
                w=dial_size,
                h=dial_size,
            )
            for name, cx, cy in dial_centers
        ]

        ref_images = [
            RefImage(
                name="ref0", x=115, y=225, w=40, h=30, file_name="/config/ref0.jpg"
            ),
            RefImage(
                name="ref1", x=468, y=170, w=36, h=30, file_name="/config/ref1.jpg"
            ),
            RefImage(
                name="ref2", x=275, y=410, w=90, h=28, file_name="/config/ref2.jpg"
            ),
        ]

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


# Alias for backward compatibility and semantic clarity
SyntheticWaterMeterGenerator = MeterImageGenerator
