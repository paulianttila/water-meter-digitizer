from typing import Callable

from nicegui import ui

from configuration import Config
from .step_base import BaseStep

HELP_TEXT = (
    "- **Background Poller**: Enable scheduled periodic readouts without "
    "external cron.\n"
    "- **MQTT & Home Assistant**: Stream meter values and auto-configure "
    "HA entities.\n"
    "- **History & Retention**: Configure database storage backend and "
    "automated pruning.\n"
    "- **Global Settings**: Configure data directories and minimum "
    "confidence threshold."
)


class ServicesStep(BaseStep):
    def __init__(
        self,
        name: str,
        set_image_callback: Callable[[str], None] = None,
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            set_image_callback=set_image_callback,
            spinner=spinner,
        )

    def load_from_config(self, config: Config) -> None:
        # Poller
        self.poller_enabled.value = config.poller.enabled
        self.poller_interval.value = config.poller.interval_seconds
        self.poller_run_on_startup.value = config.poller.run_on_startup
        self.poller_save_images.value = config.poller.save_images
        self.poller_retry_interval.value = config.poller.retry_interval_seconds

        # MQTT
        self.mqtt_enabled.value = config.mqtt.enabled
        self.mqtt_broker.value = config.mqtt.broker
        self.mqtt_port.value = config.mqtt.port
        self.mqtt_username.value = config.mqtt.username
        self.mqtt_password.value = config.mqtt.password
        self.mqtt_client_id.value = config.mqtt.client_id
        self.mqtt_topic_prefix.value = config.mqtt.topic_prefix
        self.mqtt_keepalive.value = config.mqtt.keepalive
        self.mqtt_tls.value = config.mqtt.tls
        self.mqtt_retain.value = config.mqtt.retain
        self.mqtt_ha_discovery.value = config.mqtt.homeassistant_discovery
        self.mqtt_discovery_prefix.value = config.mqtt.discovery_prefix
        self.mqtt_device_name.value = config.mqtt.device_name
        self.mqtt_device_id.value = config.mqtt.device_id

        # History
        self.history_enabled.value = config.history.enabled
        self.history_backend.value = config.history.backend
        self.history_retention_days.value = config.history.retention_days
        self.history_max_records.value = config.history.max_records
        self.history_auto_vacuum.value = config.history.auto_vacuum
        self.history_prune_interval.value = config.history.prune_interval

        # Zero-Flow & Leak Monitor
        self.zero_flow_enabled.value = config.zero_flow_monitor.enabled
        self.zero_flow_meter_name.value = config.zero_flow_monitor.meter_name
        self.zero_flow_hours.value = config.zero_flow_monitor.continuous_flow_hours
        self.zero_flow_min_volume.value = config.zero_flow_monitor.min_leak_volume
        self.zero_flow_threshold.value = config.zero_flow_monitor.flow_threshold
        self.zero_flow_debounce_count.value = (
            config.zero_flow_monitor.resolve_debounce_count
        )
        self.zero_flow_max_history.value = config.zero_flow_monitor.max_history_events

        # Global
        self.data_dir.value = config.data_dir
        self.min_confidence_threshold.value = config.min_confidence_threshold

    def apply_to_config(self, config: Config) -> None:
        # Poller
        config.poller.enabled = bool(self.poller_enabled.value)
        config.poller.interval_seconds = int(self.poller_interval.value or 300)
        config.poller.run_on_startup = bool(self.poller_run_on_startup.value)
        config.poller.save_images = bool(self.poller_save_images.value)
        config.poller.retry_interval_seconds = int(
            self.poller_retry_interval.value or 30
        )

        # MQTT
        config.mqtt.enabled = bool(self.mqtt_enabled.value)
        config.mqtt.broker = str(self.mqtt_broker.value or "localhost")
        config.mqtt.port = int(self.mqtt_port.value or 1883)
        config.mqtt.username = str(self.mqtt_username.value or "")
        config.mqtt.password = str(self.mqtt_password.value or "")
        config.mqtt.client_id = str(
            self.mqtt_client_id.value or "water-meter-digitizer"
        )
        config.mqtt.topic_prefix = str(self.mqtt_topic_prefix.value or "watermeter")
        config.mqtt.keepalive = int(self.mqtt_keepalive.value or 60)
        config.mqtt.tls = bool(self.mqtt_tls.value)
        config.mqtt.retain = bool(self.mqtt_retain.value)
        config.mqtt.homeassistant_discovery = bool(self.mqtt_ha_discovery.value)
        config.mqtt.discovery_prefix = str(
            self.mqtt_discovery_prefix.value or "homeassistant"
        )
        config.mqtt.device_name = str(
            self.mqtt_device_name.value or "Water Meter Digitizer"
        )
        config.mqtt.device_id = str(
            self.mqtt_device_id.value or "water_meter_digitizer"
        )

        # History
        config.history.enabled = bool(self.history_enabled.value)
        config.history.backend = str(self.history_backend.value or "sqlite")
        config.history.retention_days = int(self.history_retention_days.value or 30)
        config.history.max_records = int(self.history_max_records.value or 50000)
        config.history.auto_vacuum = bool(self.history_auto_vacuum.value)
        config.history.prune_interval = int(self.history_prune_interval.value or 50)

        # Zero-Flow & Leak Monitor
        config.zero_flow_monitor.enabled = bool(self.zero_flow_enabled.value)
        config.zero_flow_monitor.meter_name = str(
            self.zero_flow_meter_name.value or "total"
        )
        config.zero_flow_monitor.continuous_flow_hours = float(
            self.zero_flow_hours.value or 2.0
        )
        config.zero_flow_monitor.min_leak_volume = float(
            self.zero_flow_min_volume.value or 0.010
        )
        config.zero_flow_monitor.flow_threshold = float(
            self.zero_flow_threshold.value or 0.001
        )
        config.zero_flow_monitor.resolve_debounce_count = int(
            self.zero_flow_debounce_count.value or 2
        )
        config.zero_flow_monitor.max_history_events = int(
            self.zero_flow_max_history.value or 50
        )

        # Global
        config.data_dir = str(self.data_dir.value or "/data")
        config.min_confidence_threshold = float(
            self.min_confidence_threshold.value or 50.0
        )

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            with ui.column().classes("w-full gap-3 my-2"):
                # Poller Section Card
                with ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "p-4 gap-3 shadow-md"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes(
                            "items-center gap-2 text-slate-300 font-semibold"
                        ):
                            ui.icon("schedule", size="sm").classes("text-amber-400")
                            ui.label("Scheduled Background Poller")
                        self.poller_enabled = ui.switch("Enabled").tooltip(
                            "Enable automated background scheduled image capture "
                            "and readout"
                        )

                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        self.poller_run_on_startup = ui.checkbox(
                            "Run on Startup", value=True
                        ).tooltip(
                            "Trigger an immediate readout when the server starts up"
                        )
                        self.poller_save_images = ui.checkbox(
                            "Save Debug Images", value=False
                        ).tooltip(
                            "Save intermediate diagnostic debug crop images to "
                            "disk on each scheduled run"
                        )

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(180px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.poller_interval = ui.number(
                            "Interval (seconds)", value=300, min=5, step=10
                        ).tooltip(
                            "Time between automatic readouts (e.g. 300 = 5 minutes)"
                        )
                        self.poller_retry_interval = ui.number(
                            "Retry Interval (seconds)", value=30, min=5, step=5
                        ).tooltip("Delay before retrying after a failure")

                # MQTT Section Card
                with ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "p-4 gap-3 shadow-md"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes(
                            "items-center gap-2 text-slate-300 font-semibold"
                        ):
                            ui.icon("sensors", size="sm").classes("text-emerald-400")
                            ui.label("MQTT & Home Assistant Discovery")
                        self.mqtt_enabled = ui.switch("Enabled").tooltip(
                            "Enable MQTT telemetry publishing for meter readings"
                        )

                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        self.mqtt_tls = ui.checkbox(
                            "TLS Encryption", value=False
                        ).tooltip(
                            "Enable TLS/SSL encryption for secure MQTT broker "
                            "connection"
                        )
                        self.mqtt_retain = ui.checkbox(
                            "Retain Messages", value=True
                        ).tooltip(
                            "Publish telemetry with MQTT retain flag so subscribers "
                            "receive last known state on connect"
                        )
                        self.mqtt_ha_discovery = ui.checkbox(
                            "Home Assistant Discovery", value=True
                        ).tooltip(
                            "Automatically publish Home Assistant MQTT Auto-Discovery "
                            "configuration payloads"
                        )

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(160px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.mqtt_broker = ui.input(
                            "Broker Host", value="localhost"
                        ).tooltip("MQTT broker IP address or hostname")
                        self.mqtt_port = ui.number(
                            "Port", value=1883, min=1, max=65535, step=1
                        ).tooltip(
                            "MQTT broker port (e.g. 1883 for standard, 8883 for TLS)"
                        )
                        self.mqtt_keepalive = ui.number(
                            "Keepalive (s)", value=60, min=5, step=5
                        ).tooltip("MQTT keepalive interval in seconds (default: 60)")

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(180px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.mqtt_username = ui.input(
                            "Username", placeholder="Optional username"
                        ).tooltip("Optional MQTT broker username authentication")
                        self.mqtt_password = ui.input(
                            "Password", password=True, placeholder="Optional password"
                        ).tooltip("Optional MQTT broker password authentication")

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(180px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.mqtt_topic_prefix = ui.input(
                            "Topic Prefix", value="watermeter"
                        ).tooltip("Base MQTT topic prefix (e.g. watermeter)")
                        self.mqtt_client_id = ui.input(
                            "Client ID", value="water-meter-digitizer"
                        ).tooltip("MQTT client identifier sent in connect packet")

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(180px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.mqtt_discovery_prefix = ui.input(
                            "HA Discovery Prefix", value="homeassistant"
                        ).tooltip(
                            "Home Assistant MQTT discovery root topic prefix "
                            "(default: homeassistant)"
                        )
                        self.mqtt_device_name = ui.input(
                            "Device Name", value="Water Meter Digitizer"
                        ).tooltip(
                            "Friendly device name displayed in Home Assistant "
                            "device registry"
                        )
                        self.mqtt_device_id = ui.input(
                            "Device ID", value="water_meter_digitizer"
                        ).tooltip(
                            "Unique device identifier for Home Assistant "
                            "entity mapping"
                        )

                # History & Storage Card
                with ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "p-4 gap-3 shadow-md"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes(
                            "items-center gap-2 text-slate-300 font-semibold"
                        ):
                            ui.icon("history", size="sm").classes("text-blue-400")
                            ui.label("History & Storage Backend")
                        self.history_enabled = ui.switch("Enabled").tooltip(
                            "Enable persistent historical timeseries storage "
                            "for meter readouts"
                        )

                    with ui.row().classes("w-full items-center gap-4"):
                        self.history_auto_vacuum = ui.checkbox(
                            "Auto-Vacuum SQLite", value=True
                        ).tooltip(
                            "Enable automatic VACUUM on SQLite database to "
                            "reclaim free disk space"
                        )

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(150px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.history_backend = ui.select(
                            ["sqlite", "memory"], label="Backend", value="sqlite"
                        ).tooltip(
                            "Storage engine backend: SQLite (persistent file) "
                            "or Memory (in-RAM)"
                        )
                        self.history_retention_days = ui.number(
                            "Retention (Days)", value=30, min=0, step=1
                        ).tooltip("0 to retain forever")
                        self.history_max_records = ui.number(
                            "Max Records", value=50000, min=0, step=1000
                        ).tooltip("0 to disable record limit")
                        self.history_prune_interval = ui.number(
                            "Prune Interval", value=50, min=1, step=5
                        ).tooltip("Readouts between automated pruning cycles")

                # Zero-Flow & Leak Monitor Card
                with ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "p-4 gap-3 shadow-md"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes(
                            "items-center gap-2 text-slate-300 font-semibold"
                        ):
                            ui.icon("water_damage", size="sm").classes("text-cyan-400")
                            ui.label("Zero-Flow Tracking & Leak Monitor")
                        self.zero_flow_enabled = ui.switch("Enabled").tooltip(
                            "Detect continuous non-zero flow sustained over time "
                            "without quiet periods"
                        )

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(170px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.zero_flow_meter_name = ui.input(
                            "Target Meter Name", value="total"
                        ).tooltip("Meter name to monitor for continuous flow")
                        self.zero_flow_hours = ui.number(
                            "Continuous Flow Alert (Hours)",
                            value=2.0,
                            min=0.1,
                            step=0.5,
                        ).tooltip(
                            "Hours of continuous flow before triggering a leak alert"
                        )
                        self.zero_flow_min_volume = ui.number(
                            "Min Leak Volume", value=0.010, min=0.0001, step=0.005
                        ).tooltip(
                            "Minimum cumulative volume required to trigger alert "
                            "(filters optical jitter)"
                        )

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(170px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.zero_flow_threshold = ui.number(
                            "Flow Threshold", value=0.001, min=0.0001, step=0.0005
                        ).tooltip(
                            "Minimum delta between readings to count as active flow"
                        )
                        self.zero_flow_debounce_count = ui.number(
                            "Resolve Debounce Count", value=2, min=1, step=1
                        ).tooltip(
                            "Consecutive zero readings required to auto-resolve alert"
                        )
                        self.zero_flow_max_history = ui.number(
                            "Max History Events", value=50, min=5, step=10
                        ).tooltip("Maximum historical leak events to retain")

                # Global Defaults Card
                with ui.card().classes(
                    "w-full bg-slate-900/60 border border-white/10 rounded-xl "
                    "p-4 gap-3 shadow-md"
                ):
                    with ui.row().classes(
                        "w-full items-center gap-2 text-slate-300 font-semibold"
                    ):
                        ui.icon("settings", size="sm").classes("text-slate-400")
                        ui.label("Global Settings")

                    with ui.grid(
                        columns="repeat(auto-fit, minmax(220px, 1fr))"
                    ).classes("w-full gap-3"):
                        self.data_dir = ui.input(
                            "Data Directory", value="/data"
                        ).tooltip(
                            "Directory path for database, previous values, "
                            "and debug artifacts"
                        )
                        self.min_confidence_threshold = ui.number(
                            "Min Confidence Threshold (%)",
                            value=50.0,
                            min=0.0,
                            max=100.0,
                            step=1.0,
                        ).tooltip("Reject readings below this confidence score")

            super().add_navigator(stepper, first_step, last_step)
