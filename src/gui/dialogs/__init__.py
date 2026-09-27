"""Dialogs and modals for the NiceGUI frontend."""

from .benchmark import open_model_benchmark_dialog
from .config_onboarding_dialog import show_config_onboarding_dialog
from .model_alignment_dialog import open_model_alignment_dialog

__all__ = [
    "open_model_alignment_dialog",
    "open_model_benchmark_dialog",
    "show_config_onboarding_dialog",
]
