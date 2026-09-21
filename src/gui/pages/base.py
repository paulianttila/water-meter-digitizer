"""Base class for NiceGUI pages with standard lifecycle."""

from abc import ABC, abstractmethod

from nicegui import ui

from callbacks import Callbacks


class BasePage(ABC):
    """Standard page with consistent constructor and async show lifecycle."""

    def __init__(self, callbacks: Callbacks | None = None) -> None:
        self.callbacks = callbacks
        self.spinner: ui.spinner | None = None
        self._mounted = False

    @abstractmethod
    async def show(self) -> None:
        """Render the page content. Must be async."""
        ...

    def dispose(self) -> None:
        """Clean up widget references and child components."""
        self._mounted = False
        self.spinner = None

    @property
    def is_mounted(self) -> bool:
        return self._mounted
