"""Base component with lifecycle hooks for NiceGUI dashboard cards."""

from typing import Any

from nicegui import ui

from callbacks import Callbacks


class BaseComponent:
    """Base class for dashboard components with lifecycle management."""

    def __init__(self, callbacks: Callbacks | Any) -> None:
        self.callbacks = callbacks
        self.container: ui.element | None = None
        self._mounted = False

    def render(self, container: ui.element | None = None) -> None:
        """Mount the component into the given container."""
        if container is not None:
            self.container = container
        self._mounted = True

    def dispose(self) -> None:
        """Clean up widget references and cancel timers."""
        self._mounted = False
        self.container = None

    @property
    def is_mounted(self) -> bool:
        return self._mounted
