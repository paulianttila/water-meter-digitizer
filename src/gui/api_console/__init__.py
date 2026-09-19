"""API Console package."""

from .registry import (
    ENDPOINTS,
    SCENARIO_PRESETS,
    STANDARD_RESOLUTIONS,
    generate_curl_command,
)

__all__ = [
    "ENDPOINTS",
    "SCENARIO_PRESETS",
    "STANDARD_RESOLUTIONS",
    "generate_curl_command",
]
