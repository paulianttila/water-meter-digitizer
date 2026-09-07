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

        # Global
        config.data_dir = str(self.data_dir.value or "/data")
        config.min_confidence_threshold = float(
            self.min_confidence_threshold.value or 50.0
        )

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            # Poller Section
            with ui.expansion("Scheduled Background Poller", icon="schedule").classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl mb-2"
            ):
                with ui.row().classes("w-full items-center"):
                    self.poller_enabled = ui.checkbox(
                        "Enable Background Poller", value=False
                    ).tooltip(
                        "Enable automated background scheduled image capture "
                        "and readout"
                    )
                    self.poller_run_on_startup = ui.checkbox(
                        "Run on Startup", value=True
                    ).tooltip("Trigger an immediate readout when the server starts up")
                    self.poller_save_images = ui.checkbox(
                        "Save Debug Images", value=False
                    ).tooltip(
                        "Save intermediate diagnostic debug crop images to disk on "
                        "each scheduled run"
                    )

                with ui.grid(columns="1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.poller_interval = ui.number(
                        "Interval (seconds)", value=300, min=5, step=10
                    ).tooltip("Time between automatic readouts (e.g. 300 = 5 minutes)")
                    self.poller_retry_interval = ui.number(
                        "Retry Interval (seconds)", value=30, min=5, step=5
                    ).tooltip("Delay before retrying after a failure")

            # MQTT Section
            with ui.expansion(
                "MQTT & Home Assistant Discovery", icon="sensors"
            ).classes("w-full bg-slate-900/60 border border-white/10 rounded-xl mb-2"):
                with ui.row().classes("w-full items-center"):
                    self.mqtt_enabled = ui.checkbox("Enable MQTT", value=False).tooltip(
                        "Enable MQTT telemetry publishing for meter readings"
                    )
                    self.mqtt_tls = ui.checkbox("TLS Encryption", value=False).tooltip(
                        "Enable TLS/SSL encryption for secure MQTT broker connection"
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

                with ui.grid(columns="2fr 1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.mqtt_broker = ui.input(
                        "Broker Host", value="localhost"
                    ).tooltip("MQTT broker IP address or hostname")
                    self.mqtt_port = ui.number(
                        "Port", value=1883, min=1, max=65535, step=1
                    ).tooltip("MQTT broker port (e.g. 1883 for standard, 8883 for TLS)")
                    self.mqtt_keepalive = ui.number(
                        "Keepalive (s)", value=60, min=5, step=5
                    ).tooltip("MQTT keepalive interval in seconds (default: 60)")

                with ui.grid(columns="1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.mqtt_username = ui.input(
                        "Username", placeholder="Optional username"
                    ).tooltip("Optional MQTT broker username authentication")
                    self.mqtt_password = ui.input(
                        "Password", password=True, placeholder="Optional password"
                    ).tooltip("Optional MQTT broker password authentication")

                with ui.grid(columns="1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.mqtt_topic_prefix = ui.input(
                        "Topic Prefix", value="watermeter"
                    ).tooltip("Base MQTT topic prefix (e.g. watermeter)")
                    self.mqtt_client_id = ui.input(
                        "Client ID", value="water-meter-digitizer"
                    ).tooltip("MQTT client identifier sent in connect packet")

                with ui.grid(columns="1fr 1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.mqtt_discovery_prefix = ui.input(
                        "HA Discovery Prefix", value="homeassistant"
                    ).tooltip(
                        "Home Assistant MQTT discovery root topic prefix "
                        "(default: homeassistant)"
                    )
                    self.mqtt_device_name = ui.input(
                        "Device Name", value="Water Meter Digitizer"
                    ).tooltip(
                        "Friendly device name displayed in Home Assistant device "
                        "registry"
                    )
                    self.mqtt_device_id = ui.input(
                        "Device ID", value="water_meter_digitizer"
                    ).tooltip(
                        "Unique device identifier for Home Assistant entity mapping"
                    )

            # History Section
            with ui.expansion("History & Storage", icon="history").classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl mb-2"
            ):
                with ui.row().classes("w-full items-center"):
                    self.history_enabled = ui.checkbox(
                        "Enable History Logging", value=True
                    ).tooltip(
                        "Enable persistent historical timeseries storage for "
                        "meter readouts"
                    )
                    self.history_auto_vacuum = ui.checkbox(
                        "Auto-Vacuum SQLite", value=True
                    ).tooltip(
                        "Enable automatic VACUUM on SQLite database to reclaim "
                        "free disk space"
                    )

                with ui.grid(columns="1fr 1fr 1fr 1fr").classes("w-full gap-3 mt-2"):
                    self.history_backend = ui.select(
                        ["sqlite", "memory"], label="Backend", value="sqlite"
                    ).tooltip(
                        "Storage engine backend: SQLite (persistent file) or "
                        "Memory (in-RAM)"
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

            # Global Defaults Section
            with ui.expansion("Global Settings", icon="settings").classes(
                "w-full bg-slate-900/60 border border-white/10 rounded-xl mb-2"
            ):
                with ui.grid(columns="1fr 1fr").classes("w-full gap-3"):
                    self.data_dir = ui.input("Data Directory", value="/data").tooltip(
                        "Directory path for database, previous values, and "
                        "debug artifacts"
                    )
                    self.min_confidence_threshold = ui.number(
                        "Min Confidence Threshold (%)",
                        value=50.0,
                        min=0.0,
                        max=100.0,
                        step=1.0,
                    ).tooltip("Reject readings below this confidence score")

            super().add_navigator(stepper, first_step, last_step)
