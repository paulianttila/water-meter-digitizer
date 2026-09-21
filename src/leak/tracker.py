"""Backward-compatibility facade for leak.tracker."""

from services.leak.tracker import ZeroFlowTracker

__all__ = ["ZeroFlowTracker"]
