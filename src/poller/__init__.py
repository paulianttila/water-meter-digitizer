"""Backward-compatibility facade for poller package."""

from services.poller.scheduler import BackgroundPoller

__all__ = ["BackgroundPoller"]
