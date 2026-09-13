"""Mock Camera REST API endpoint for simulated test camera feeds."""

from __future__ import annotations

import io
import logging
import random
import threading

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from testing.meter_generator import MeterImageGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])

_ticker_lock = threading.Lock()
_ticker_state = {
    "current_value": 100.0,
    "last_reset": 0.0,
}


def render_mock_camera_frame(
    value: str | None = None,
    mode: str = "fixed",  # "fixed", "ticker", "random", "flow"
    rate: float = 0.005,
    rotate: float = 0.0,
    glare: bool = False,
    glare_pos: str | None = None,
    glare_intensity: float = 1.0,
    noise: float = 0.0,
    blur: float = 0.0,
    brightness: float = 1.0,
    contrast: float = 1.0,
    lcd_color: str = "black",
    lcd_bg: str = "grey",
    needle_color: str = "red",
    width: int = 640,
    height: int = 480,
    digit1: float | None = None,
    digit2: float | None = None,
    digit3: float | None = None,
    digit4: float | None = None,
    digit5: float | None = None,
    analog1: float | None = None,
    analog2: float | None = None,
    analog3: float | None = None,
    analog4: float | None = None,
) -> tuple[bytes, dict[str, str]]:
    """Render procedural mock water meter frame and return JPEG bytes with headers."""
    generator = MeterImageGenerator()

    target_val_str = "00452.91241"
    if mode in ("ticker", "flow"):
        with _ticker_lock:
            val = _ticker_state["current_value"]
            target_val_str = f"{val:011.5f}"
            _ticker_state["current_value"] += rate
    elif mode == "random":
        r_int = random.randint(0, 99999)  # nosec B311
        r_frac = random.randint(0, 99999)  # nosec B311
        target_val_str = f"{r_int:05d}.{r_frac:05d}"
    elif value is not None:
        target_val_str = str(value)

    # Parse glare position if passed as "x,y"
    g_pos: tuple[float, float] | None = None
    if glare_pos:
        try:
            gx, gy = glare_pos.split(",")
            g_pos = (float(gx.strip()), float(gy.strip()))
        except Exception:
            g_pos = None

    # Custom per-digit and per-dial overrides
    custom_dig: dict[str, float] = {}
    if digit1 is not None:
        custom_dig["digit1"] = digit1
    if digit2 is not None:
        custom_dig["digit2"] = digit2
    if digit3 is not None:
        custom_dig["digit3"] = digit3
    if digit4 is not None:
        custom_dig["digit4"] = digit4
    if digit5 is not None:
        custom_dig["digit5"] = digit5

    custom_ana: dict[str, float] = {}
    if analog1 is not None:
        custom_ana["analog1"] = analog1
    if analog2 is not None:
        custom_ana["analog2"] = analog2
    if analog3 is not None:
        custom_ana["analog3"] = analog3
    if analog4 is not None:
        custom_ana["analog4"] = analog4

    img = generator.generate(
        value=target_val_str,
        rotate=rotate,
        glare=glare,
        glare_pos=g_pos,
        glare_intensity=glare_intensity,
        noise=noise,
        blur=blur,
        brightness=brightness,
        contrast=contrast,
        lcd_color=lcd_color,
        lcd_bg=lcd_bg,
        needle_color=needle_color,
        width=width,
        height=height,
        custom_digital_values=custom_dig if custom_dig else None,
        custom_analog_values=custom_ana if custom_ana else None,
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)

    parts = target_val_str.split(".")
    int_part = parts[0].zfill(5)[-5:]
    frac_part = (parts[1] + "0000")[:4] if len(parts) > 1 else "0000"

    headers = {
        "X-Mock-Meter-Value": target_val_str,
        "X-Mock-Digital-Value": int_part,
        "X-Mock-Analog-Value": frac_part,
    }
    return buf.getvalue(), headers


def render_mock_camera_from_url(url: str) -> bytes:
    """Parse query parameters from URL and render mock camera JPEG bytes directly."""
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    def _get_str(k: str, default: str | None = None) -> str | None:
        return params[k][0] if params.get(k) else default

    def _get_float(k: str, default: float | None = None) -> float | None:
        if params.get(k):
            try:
                return float(params[k][0])
            except ValueError:
                return default
        return default

    def _get_int(k: str, default: int) -> int:
        if params.get(k):
            try:
                return int(params[k][0])
            except ValueError:
                return default
        return default

    def _get_bool(k: str, default: bool) -> bool:
        if params.get(k):
            return params[k][0].lower() in ("true", "1", "yes")
        return default

    frame_bytes, _ = render_mock_camera_frame(
        value=_get_str("value"),
        mode=_get_str("mode", "fixed") or "fixed",
        rate=_get_float("rate", 0.005) or 0.005,
        rotate=_get_float("rotate", 0.0) or 0.0,
        glare=_get_bool("glare", False),
        glare_pos=_get_str("glare_pos"),
        glare_intensity=_get_float("glare_intensity", 1.0) or 1.0,
        noise=_get_float("noise", 0.0) or 0.0,
        blur=_get_float("blur", 0.0) or 0.0,
        brightness=_get_float("brightness", 1.0) or 1.0,
        contrast=_get_float("contrast", 1.0) or 1.0,
        lcd_color=_get_str("lcd_color", "black") or "black",
        lcd_bg=_get_str("lcd_bg", "grey") or "grey",
        needle_color=_get_str("needle_color", "red") or "red",
        width=_get_int("width", 640),
        height=_get_int("height", 480),
        digit1=_get_float("digit1"),
        digit2=_get_float("digit2"),
        digit3=_get_float("digit3"),
        digit4=_get_float("digit4"),
        digit5=_get_float("digit5"),
        analog1=_get_float("analog1"),
        analog2=_get_float("analog2"),
        analog3=_get_float("analog3"),
        analog4=_get_float("analog4"),
    )
    return frame_bytes


@router.get("/api/mock_camera")
@router.get("/mock_camera")
def get_mock_camera_frame(
    request: Request,
    value: str | None = None,
    mode: str = "fixed",  # "fixed", "ticker", "random", "flow"
    rate: float = 0.005,
    rotate: float = 0.0,
    glare: bool = False,
    glare_pos: str | None = None,
    glare_intensity: float = 1.0,
    noise: float = 0.0,
    blur: float = 0.0,
    brightness: float = 1.0,
    contrast: float = 1.0,
    lcd_color: str = "black",
    lcd_bg: str = "grey",
    needle_color: str = "red",
    width: int = 640,
    height: int = 480,
    digit1: float | None = None,
    digit2: float | None = None,
    digit3: float | None = None,
    digit4: float | None = None,
    digit5: float | None = None,
    analog1: float | None = None,
    analog2: float | None = None,
    analog3: float | None = None,
    analog4: float | None = None,
) -> Response:
    """Generate and return a simulated dynamic camera JPEG image.

    Can be used directly as the `[ImageSource] URL = http://localhost:3000/api/mock_camera?value=00789.1234`
    during automated testing, poller simulation, and CI workflows.
    """
    frame_bytes, headers = render_mock_camera_frame(
        value=value,
        mode=mode,
        rate=rate,
        rotate=rotate,
        glare=glare,
        glare_pos=glare_pos,
        glare_intensity=glare_intensity,
        noise=noise,
        blur=blur,
        brightness=brightness,
        contrast=contrast,
        lcd_color=lcd_color,
        lcd_bg=lcd_bg,
        needle_color=needle_color,
        width=width,
        height=height,
        digit1=digit1,
        digit2=digit2,
        digit3=digit3,
        digit4=digit4,
        digit5=digit5,
        analog1=analog1,
        analog2=analog2,
        analog3=analog3,
        analog4=analog4,
    )
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers=headers,
    )


@router.post("/api/mock_camera/reset")
def reset_mock_camera_ticker(start_value: float = 100.0) -> JSONResponse:
    """Reset the ticker mode value for reproducible simulation runs."""
    with _ticker_lock:
        _ticker_state["current_value"] = start_value
    return JSONResponse(
        {"status": "success", "message": f"Mock ticker reset to {start_value}"}
    )
