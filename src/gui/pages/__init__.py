"""Pages for the NiceGUI web interface."""

from .about import AboutPage
from .api_console import ApiConsolePage
from .base import BasePage
from .config import ConfigPage
from .help import HelpPage
from .meter import MeterPage
from .previous_values import PreviousValuesPage
from .services import ServicesPage
from .setup import SetupPage

__all__ = [
    "AboutPage",
    "ApiConsolePage",
    "BasePage",
    "ConfigPage",
    "HelpPage",
    "MeterPage",
    "PreviousValuesPage",
    "ServicesPage",
    "SetupPage",
]
