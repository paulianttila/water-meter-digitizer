import json
import logging
import ssl
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

from configuration import MQTT
from data_classes import MeterConfig
from processor.digitizer import MeterResult
from version import __version__

from .discovery import build_homeassistant_discovery_payloads

logger = logging.getLogger(__name__)


class MQTTService:
    """Manages MQTT connection, Home Assistant Auto-Discovery, and state publishing."""

    def __init__(
        self,
        config: MQTT,
        meter_configs: list[MeterConfig] | None = None,
        version: str = __version__,
    ) -> None:
        self.config = config
        self.meter_configs = meter_configs or []
        self.version = version
        self.is_connected = False
        self._connect_failed_logged = False
        self._client: mqtt.Client | None = None
        self.last_published_topics: dict[str, str] = {}
        self.last_published_readout: dict[str, Any] | None = None

        if self.config.enabled:
            self._setup_client()

    def _setup_client(self) -> None:
        client_id = self.config.client_id or "water-meter-digitizer"

        # Compatibility with paho-mqtt v1 and v2 CallbackAPIVersion if available
        try:
            from paho.mqtt.enums import CallbackAPIVersion

            self._client = mqtt.Client(
                CallbackAPIVersion.VERSION2,
                client_id=client_id,
            )
        except (ImportError, AttributeError):
            self._client = mqtt.Client(client_id=client_id)

        if self.config.username:
            self._client.username_pw_set(
                username=self.config.username,
                password=self.config.password or None,
            )

        if self.config.tls:
            self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        # Last Will and Testament (LWT)
        status_topic = f"{self.config.topic_prefix}/status"
        self._client.will_set(
            topic=status_topic,
            payload="offline",
            qos=1,
            retain=self.config.retain,
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        if hasattr(self._client, "on_connect_fail"):
            self._client.on_connect_fail = self._on_connect_fail

    def _on_connect_fail(self, client: Any, userdata: Any) -> None:
        self.is_connected = False
        if not self._connect_failed_logged:
            logger.warning(
                "Failed to connect to MQTT broker %s:%d (connection refused / unreachable). Retrying in background...",
                self.config.broker,
                self.config.port,
            )
            self._connect_failed_logged = True

    def _on_connect(
        self, client: Any, userdata: Any, flags: Any, rc: Any, *args: Any
    ) -> None:
        # In paho v2, rc is a ReasonCode object; in v1, rc is an int (0 = success)
        rc_code = getattr(rc, "value", rc)
        if rc_code == 0:
            self.is_connected = True
            self._connect_failed_logged = False
            logger.info(
                "Connected to MQTT broker %s:%d",
                self.config.broker,
                self.config.port,
            )
            # Publish online status
            if self._client is not None:
                status_topic = f"{self.config.topic_prefix}/status"
                self._client.publish(
                    topic=status_topic,
                    payload="online",
                    qos=1,
                    retain=self.config.retain,
                )

            # Publish Home Assistant Discovery if enabled
            if self.config.homeassistant_discovery:
                self.publish_discovery()
        else:
            self.is_connected = False
            logger.warning(
                "Failed to connect to MQTT broker, return code %s",
                str(rc),
            )

    def _on_disconnect(self, client: Any, userdata: Any, *args: Any) -> None:
        self.is_connected = False
        # In paho v2 (VERSION2): args = (disconnect_flags, reason_code, properties)
        # In paho v1 (VERSION1): args = (rc,)
        if len(args) >= 2:
            rc = args[1]
        elif len(args) == 1:
            rc = args[0]
        else:
            rc = 0

        is_error = getattr(rc, "is_failure", None)
        if is_error is not None:
            if is_error:
                logger.warning(
                    "Unexpected disconnection from MQTT broker (reason=%s)", str(rc)
                )
            else:
                logger.info("Disconnected from MQTT broker (%s)", str(rc))
        else:
            rc_code = getattr(rc, "value", rc)
            if rc_code != 0:
                logger.warning(
                    "Unexpected disconnection from MQTT broker (rc=%s)", str(rc)
                )
            else:
                logger.info("Disconnected from MQTT broker")

    def start(self) -> None:
        """Start background connection loop."""
        if not self.config.enabled or self._client is None:
            return

        self._connect_failed_logged = False
        try:
            logger.info(
                "Starting MQTT client connecting to %s:%d...",
                self.config.broker,
                self.config.port,
            )
            self._client.connect_async(
                host=self.config.broker,
                port=self.config.port,
                keepalive=self.config.keepalive,
            )
            self._client.loop_start()
        except Exception as e:
            logger.error("Error starting MQTT client: %s", e)

    def stop(self) -> None:
        """Publish offline status and stop background loop."""
        if self._client is None:
            return

        try:
            if self.is_connected:
                status_topic = f"{self.config.topic_prefix}/status"
                self._client.publish(
                    topic=status_topic,
                    payload="offline",
                    qos=1,
                    retain=self.config.retain,
                )
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as e:
            logger.warning("Error stopping MQTT client: %s", e)
        finally:
            self.is_connected = False

    def publish_discovery(self) -> None:
        """Publish Home Assistant Auto-Discovery payloads."""
        if not self.config.enabled or not self.is_connected or self._client is None:
            return

        payloads = build_homeassistant_discovery_payloads(
            mqtt_config=self.config,
            meter_configs=self.meter_configs,
            version=self.version,
        )

        for topic, payload in payloads:
            try:
                self._client.publish(
                    topic=topic,
                    payload=json.dumps(payload),
                    qos=1,
                    retain=True,
                )
                logger.debug("Published HA discovery to %s", topic)
            except Exception as e:
                logger.warning("Failed to publish HA discovery to %s: %s", topic, e)

    def publish_meter_result(
        self,
        meter_result: MeterResult,
        processing_time_sec: float = 0.0,
    ) -> None:
        """Publish meter readout results to configured MQTT topics."""
        if not self.config.enabled or not self.is_connected or self._client is None:
            return

        prefix = self.config.topic_prefix
        retain = self.config.retain
        now_iso = datetime.now().astimezone().isoformat()

        topics_published: dict[str, str] = {}

        try:
            # 1. Individual meter readings
            for meter in meter_result.meters:
                if meter.value is not None:
                    # Clean numerical state for HA / openHAB
                    topics_published[f"{prefix}/{meter.name}/value"] = str(meter.value)
                    self._client.publish(
                        topic=f"{prefix}/{meter.name}/value",
                        payload=str(meter.value),
                        qos=1,
                        retain=retain,
                    )

                    # Diagnostic confidence score
                    conf = getattr(meter, "confidence", 100.0)
                    topics_published[f"{prefix}/{meter.name}/confidence"] = (
                        f"{conf:.1f}"
                    )
                    self._client.publish(
                        topic=f"{prefix}/{meter.name}/confidence",
                        payload=f"{conf:.1f}",
                        qos=1,
                        retain=retain,
                    )

                    # Rich JSON attributes
                    attrs = {
                        "value": meter.value,
                        "unit": meter.unit,
                        "quality": getattr(meter, "quality", "good"),
                        "confidence": conf,
                        "timestamp": now_iso,
                    }
                    attrs_json = json.dumps(attrs)
                    topics_published[f"{prefix}/{meter.name}/attributes"] = attrs_json
                    self._client.publish(
                        topic=f"{prefix}/{meter.name}/attributes",
                        payload=attrs_json,
                        qos=1,
                        retain=retain,
                    )

                    # Single meter JSON payload
                    topics_published[f"{prefix}/{meter.name}/json"] = attrs_json
                    self._client.publish(
                        topic=f"{prefix}/{meter.name}/json",
                        payload=attrs_json,
                        qos=1,
                        retain=retain,
                    )

            # 2. System error & processing time
            err = getattr(meter_result, "error", "") or ""
            topics_published[f"{prefix}/error"] = err
            self._client.publish(
                topic=f"{prefix}/error",
                payload=err,
                qos=1,
                retain=retain,
            )

            if processing_time_sec > 0:
                topics_published[f"{prefix}/processing_time"] = (
                    f"{processing_time_sec:.2f}"
                )
                self._client.publish(
                    topic=f"{prefix}/processing_time",
                    payload=f"{processing_time_sec:.2f}",
                    qos=1,
                    retain=retain,
                )

            # 3. Complete readout JSON payload for generic integrations / openHAB
            full_payload = meter_result.model_dump(mode="json")
            full_payload["timestamp"] = now_iso
            full_payload["processing_time_seconds"] = round(processing_time_sec, 3)

            readout_json = json.dumps(full_payload)
            topics_published[f"{prefix}/readout/json"] = readout_json
            self._client.publish(
                topic=f"{prefix}/readout/json",
                payload=readout_json,
                qos=1,
                retain=retain,
            )

            self.last_published_topics = topics_published
            self.last_published_readout = full_payload
            logger.info("Published meter readout to MQTT prefix '%s'", prefix)
        except Exception as e:
            logger.error("Failed to publish meter result to MQTT: %s", e)

    def publish_error(self, error_msg: str) -> None:
        """Publish an error message to the MQTT error topic."""
        if not self.config.enabled or not self.is_connected or self._client is None:
            return

        try:
            self._client.publish(
                topic=f"{self.config.topic_prefix}/error",
                payload=error_msg,
                qos=1,
                retain=self.config.retain,
            )
        except Exception as e:
            logger.warning("Failed to publish error to MQTT: %s", e)

    def publish_zero_flow_status(self, status: Any) -> None:
        """Publish zero-flow tracking and leak status metrics to MQTT."""
        if not self.config.enabled or not self.is_connected or self._client is None:
            return

        try:
            prefix = self.config.topic_prefix or "watermeter"
            retain = self.config.retain
            status_dict = status.to_dict() if hasattr(status, "to_dict") else status

            is_leak = status_dict.get("state") == "LEAK_DETECTED"
            alert_payload = "ON" if is_leak else "OFF"
            state_str = str(status_dict.get("state", "OK"))
            duration_min = str(status_dict.get("current_flow_duration_minutes", 0.0))
            json_payload = json.dumps(status_dict)

            self._client.publish(
                topic=f"{prefix}/leak/alert",
                payload=alert_payload,
                qos=1,
                retain=retain,
            )
            self._client.publish(
                topic=f"{prefix}/leak/state",
                payload=state_str,
                qos=1,
                retain=retain,
            )
            self._client.publish(
                topic=f"{prefix}/leak/duration",
                payload=duration_min,
                qos=1,
                retain=retain,
            )
            self._client.publish(
                topic=f"{prefix}/leak/status",
                payload=json_payload,
                qos=1,
                retain=retain,
            )
            logger.debug("Published zero-flow status to MQTT: state=%s", state_str)
        except Exception as e:
            logger.warning("Failed to publish zero-flow status to MQTT: %s", e)

    def get_status(self) -> dict[str, Any]:
        """Return MQTT service status and metrics."""
        return {
            "enabled": self.config.enabled,
            "connected": self.is_connected,
            "broker": self.config.broker,
            "port": self.config.port,
            "topic_prefix": self.config.topic_prefix,
            "homeassistant_discovery": self.config.homeassistant_discovery,
            "client_id": self.config.client_id,
            "last_published_topics": self.last_published_topics,
            "last_published_readout": self.last_published_readout,
        }
