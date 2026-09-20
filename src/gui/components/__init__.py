"""NiceGUI Dashboard and Telemetry Components."""

from .consumption_card import ConsumptionCard
from .diagnostics_card import DiagnosticsCard
from .engine_test_dialog import run_engine_test_dialog, show_engine_test_modal
from .history_table_card import HistoryTableCard
from .leak_monitor_card import LeakMonitorCard
from .services_status_card import ServicesStatusCard
from .time_machine_card import TimeMachineCard

__all__ = [
    "ConsumptionCard",
    "DiagnosticsCard",
    "HistoryTableCard",
    "LeakMonitorCard",
    "ServicesStatusCard",
    "TimeMachineCard",
    "run_engine_test_dialog",
    "show_engine_test_modal",
]
