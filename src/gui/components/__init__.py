"""NiceGUI Dashboard and Telemetry Components."""

from .async_data_loader import async_fetch_and_render
from .base_component import BaseComponent
from .code_inspect_dialog import open_code_inspect_dialog
from .config_history_dialog import format_diff_html, open_config_history_dialog
from .confirm_dialog import open_confirm_dialog
from .consumption_card import ConsumptionCard
from .diagnostics_card import DiagnosticsCard
from .engine_test_dialog import run_engine_test_dialog, show_engine_test_modal
from .history_table_card import HistoryTableCard
from .leak_monitor_card import LeakMonitorCard
from .page_header import card_header, page_header, render_page_header
from .services_status_card import ServicesStatusCard
from .time_machine_card import TimeMachineCard
from .validation_banner import ValidationBanner

__all__ = [
    "BaseComponent",
    "ConsumptionCard",
    "DiagnosticsCard",
    "HistoryTableCard",
    "LeakMonitorCard",
    "ServicesStatusCard",
    "TimeMachineCard",
    "ValidationBanner",
    "async_fetch_and_render",
    "card_header",
    "format_diff_html",
    "open_code_inspect_dialog",
    "open_config_history_dialog",
    "open_confirm_dialog",
    "page_header",
    "render_page_header",
    "run_engine_test_dialog",
    "show_engine_test_modal",
]
