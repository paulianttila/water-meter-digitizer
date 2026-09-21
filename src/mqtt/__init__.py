"""Backward-compatibility facade for mqtt package."""

from services.mqtt.client import MQTTService
from services.mqtt.discovery import build_homeassistant_discovery_payloads

__all__ = ["MQTTService", "build_homeassistant_discovery_payloads"]
