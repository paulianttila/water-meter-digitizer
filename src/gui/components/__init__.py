"""NiceGUI Dashboard and Telemetry Components."""

from .consumption_card import ConsumptionCard
from .diagnostics_card import DiagnosticsCard
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
]
