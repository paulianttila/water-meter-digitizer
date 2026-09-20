"""Streaming timer lifecycle and background tasks management for Mock Camera Studio."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nicegui import ui

if TYPE_CHECKING:
    pass


class MockStreamingController:
    """Manages live mock camera streaming timer and async background rendering tasks."""

    def __init__(
        self,
        frame_generator: Callable[[], Any],
        interval_seconds: float = 1.0,
    ) -> None:
        self.frame_generator = frame_generator
        self.interval_seconds = interval_seconds
        self.is_streaming = False
        self.stream_timer: ui.timer | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()

    def start_streaming(self) -> None:
        """Activate live frame streaming."""
        self.is_streaming = True
        if self.stream_timer is None:
            self.stream_timer = ui.timer(
                self.interval_seconds,
                callback=self.frame_generator,
                active=True,
            )
        else:
            self.stream_timer.active = True
        ui.notify("Live Mock Stream Active (1 frame/sec)", type="info")

    def stop_streaming(self) -> None:
        """Deactivate live frame streaming."""
        self.is_streaming = False
        if self.stream_timer is not None:
            self.stream_timer.active = False

    def toggle_streaming(self, value: bool | None = None) -> bool:
        """Toggle streaming state."""
        target = not self.is_streaming if value is None else bool(value)
        if target:
            self.start_streaming()
        else:
            self.stop_streaming()
        return self.is_streaming

    def spawn_task(self, coro: Any) -> asyncio.Task[None]:
        """Spawn and track a background task."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def dispose(self) -> None:
        """Clean up streaming timer and cancel pending background tasks."""
        self.stop_streaming()
        if self.stream_timer is not None:
            with contextlib.suppress(Exception):
                self.stream_timer.cancel()
            self.stream_timer = None
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()
        self._background_tasks.clear()
