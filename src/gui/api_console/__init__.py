"""API Console package."""

from .mock_config_dialog import MockConfigDialog
from .mock_streaming import MockStreamingController
from .mock_studio_panel import MockStudioPanel
from .registry import (
    ENDPOINTS,
    SCENARIO_PRESETS,
    STANDARD_RESOLUTIONS,
    generate_curl_command,
)
from .rest_console_panel import RestConsolePanel

__all__ = [
    "ENDPOINTS",
    "SCENARIO_PRESETS",
    "STANDARD_RESOLUTIONS",
    "MockConfigDialog",
    "MockStreamingController",
    "MockStudioPanel",
    "RestConsolePanel",
    "generate_curl_command",
]
