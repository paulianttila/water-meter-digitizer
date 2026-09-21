"""Backward-compatibility facade for mqtt.discovery."""

from services.mqtt.discovery import build_homeassistant_discovery_payloads

__all__ = ["build_homeassistant_discovery_payloads"]
