"""Endpoint metadata, scenario presets, and cURL helpers for the API Console."""

from __future__ import annotations

from typing import Any

ENDPOINTS: list[dict[str, Any]] = [
    # System & Diagnostics
    {
        "category": "System & Diagnostics",
        "label": "GET /health (Diagnostics & Telemetry)",
        "url": "/health",
        "method": "GET",
    },
    {
        "category": "System & Diagnostics",
        "label": "GET /healthcheck (Liveness Probe)",
        "url": "/healthcheck",
        "method": "GET",
    },
    {
        "category": "System & Diagnostics",
        "label": "GET /version (App Version)",
        "url": "/version",
        "method": "GET",
    },
    # Meter & Digitization
    {
        "category": "Meter & Digitization",
        "label": "GET /meter (Raw Meter Deductions as JSON)",
        "url": "/meter?format=json&saveimages=false",
        "method": "GET",
    },
    {
        "category": "Meter & Digitization",
        "label": "GET /reload (Reload Configuration as JSON)",
        "url": "/reload?format=json",
        "method": "GET",
    },
    {
        "category": "Meter & Digitization",
        "label": "GET /get_previous_values (Stored Baseline Readings)",
        "url": "/get_previous_values",
        "method": "GET",
    },
    # Poller & MQTT Services
    {
        "category": "Poller & MQTT Services",
        "label": "GET /poller/status (Poller Schedule)",
        "url": "/poller/status",
        "method": "GET",
    },
    {
        "category": "Poller & MQTT Services",
        "label": "POST /poller/trigger (Trigger Immediate Readout)",
        "url": "/poller/trigger",
        "method": "POST",
    },
    {
        "category": "Poller & MQTT Services",
        "label": "GET /mqtt/status (MQTT Broker Telemetry)",
        "url": "/mqtt/status",
        "method": "GET",
    },
    # Leak Protection & History
    {
        "category": "Leak Protection & History",
        "label": "GET /leak/status (Zero-Flow Leak Telemetry)",
        "url": "/leak/status",
        "method": "GET",
    },
    {
        "category": "Leak Protection & History",
        "label": "POST /leak/reset (Reset Leak State)",
        "url": "/leak/reset",
        "method": "POST",
    },
    {
        "category": "Leak Protection & History",
        "label": "GET /history/consumption (Historical Aggregates)",
        "url": "/history/consumption?meter_name=total&interval=daily&days=7",
        "method": "GET",
    },
    {
        "category": "Leak Protection & History",
        "label": "GET /history/records (Reading Records Log)",
        "url": "/history/records?limit=10",
        "method": "GET",
    },
    # Mock Camera Generator
    {
        "category": "Mock Camera Studio",
        "label": "GET /api/mock_camera (Mock Camera Generator Feed)",
        "url": "/api/mock_camera?value=00452.91241",
        "method": "GET",
    },
    {
        "category": "Mock Camera Studio",
        "label": "POST /api/mock_camera/reset (Reset Mock Ticker)",
        "url": "/api/mock_camera/reset?start_value=100.0",
        "method": "POST",
    },
]

SCENARIO_PRESETS: list[dict[str, Any]] = [
    {
        "name": "Clean Daytime",
        "icon": "wb_sunny",
        "desc": "Standard VGA, clean digits & analog dials, optimal contrast",
        "config": {
            "mode": "fixed",
            "value": "00452.91241",
            "rate": 0.005,
            "rotate": 0.0,
            "glare": False,
            "glare_pos": "320,240",
            "glare_intensity": 1.0,
            "noise": 0.0,
            "blur": 0.0,
            "brightness": 1.0,
            "contrast": 1.0,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["", "", "", "", ""],
            "analog_overrides": ["", "", "", ""],
        },
    },
    {
        "name": "Tilted & Noisy Sensor",
        "icon": "screen_rotation",
        "desc": "15° camera angle tilt, 8% sensor noise, slight lens blur",
        "config": {
            "mode": "fixed",
            "value": "00452.91241",
            "rate": 0.005,
            "rotate": 15.0,
            "glare": False,
            "glare_pos": "320,240",
            "glare_intensity": 1.0,
            "noise": 8.0,
            "blur": 1.2,
            "brightness": 0.95,
            "contrast": 1.05,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["", "", "", "", ""],
            "analog_overrides": ["", "", "", ""],
        },
    },
    {
        "name": "Harsh Specular Glare",
        "icon": "flash_on",
        "desc": "Intense flashlight/sun reflection directly over central dials",
        "config": {
            "mode": "fixed",
            "value": "00452.91241",
            "rate": 0.005,
            "rotate": 0.0,
            "glare": True,
            "glare_pos": "320,240",
            "glare_intensity": 1.6,
            "noise": 2.0,
            "blur": 0.5,
            "brightness": 1.1,
            "contrast": 1.1,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["", "", "", "", ""],
            "analog_overrides": ["", "", "", ""],
        },
    },
    {
        "name": "Dim Cellar / Low Light",
        "icon": "nightlight",
        "desc": "Low illumination (brightness 0.65, contrast 0.85) with dark noise",
        "config": {
            "mode": "fixed",
            "value": "00452.91241",
            "rate": 0.005,
            "rotate": 0.0,
            "glare": False,
            "glare_pos": "320,240",
            "glare_intensity": 1.0,
            "noise": 6.0,
            "blur": 0.8,
            "brightness": 0.65,
            "contrast": 0.85,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["", "", "", "", ""],
            "analog_overrides": ["", "", "", ""],
        },
    },
    {
        "name": "High-Speed Dynamic Flow",
        "icon": "waves",
        "desc": "Continuous flowing simulation running ticker at 0.05 / frame",
        "config": {
            "mode": "flow",
            "value": "00452.91241",
            "rate": 0.05,
            "rotate": 0.0,
            "glare": False,
            "glare_pos": "320,240",
            "glare_intensity": 1.0,
            "noise": 1.0,
            "blur": 0.4,
            "brightness": 1.0,
            "contrast": 1.0,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["", "", "", "", ""],
            "analog_overrides": ["", "", "", ""],
        },
    },
    {
        "name": "Transitioning Digit Drum",
        "icon": "change_circle",
        "desc": "Digit 5 transitioning halfway (2.9) across zero-crossing",
        "config": {
            "mode": "fixed",
            "value": "00452.91241",
            "rate": 0.005,
            "rotate": 0.0,
            "glare": False,
            "glare_pos": "320,240",
            "glare_intensity": 1.0,
            "noise": 0.0,
            "blur": 0.0,
            "brightness": 1.0,
            "contrast": 1.0,
            "lcd_color": "black",
            "lcd_bg": "grey",
            "needle_color": "red",
            "width": 640,
            "height": 480,
            "digit_overrides": ["0", "0", "4", "5", "2.9"],
            "analog_overrides": ["", "", "", ""],
        },
    },
]

STANDARD_RESOLUTIONS = {
    "640x480": "640x480 (VGA Default)",
    "800x600": "800x600 (SVGA)",
    "1024x768": "1024x768 (XGA)",
    "1600x1200": "1600x1200 (UXGA)",
    "custom": "Custom Resolution",
}


def generate_curl_command(
    method: str,
    full_url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    """Generate exact copyable cURL terminal command."""
    parts = [f"curl -X {method}"]
    if headers:
        for k, v in headers.items():
            parts.append(f"-H '{k}: {v}'")
    if body and method in ("POST", "PUT", "PATCH"):
        escaped_body = body.replace("'", "'\\''")
        parts.append(f"--data '{escaped_body}'")
    parts.append(f"'{full_url}'")
    return " \\\n  ".join(parts)


__all__ = [
    "ENDPOINTS",
    "SCENARIO_PRESETS",
    "STANDARD_RESOLUTIONS",
    "generate_curl_command",
]
