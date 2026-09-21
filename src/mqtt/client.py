"""Backward-compatibility facade for mqtt.client."""

from services.mqtt.client import MQTTService

__all__ = ["MQTTService"]
