"""Reusable async data loading lifecycle with spinner, error banner, and container refresh."""

import asyncio
import contextlib
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from nicegui import ui

logger = logging.getLogger(__name__)


async def async_fetch_and_render(
    fetch_fn: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]],
    render_fn: Callable[[Any], None],
    container: ui.element | None = None,
    spinner: ui.spinner | None = None,
    error_message: str = "Failed to load data",
    notify_on_error: bool = True,
    suppress_errors: bool = False,
) -> Any | None:
    """Execute async fetch, manage spinner, handle errors, and render results.

    Args:
        fetch_fn: Sync or async callable returning data.
        render_fn: Callable receiving fetched data and rendering UI.
        container: Optional container to clear before rendering.
        spinner: Optional spinner element to show/hide.
        error_message: User-facing error prefix.
        notify_on_error: Whether to show ui.notify on failure.
        suppress_errors: If True, log warning but don't re-raise.
    """
    if spinner:
        spinner.visible = True
    try:
        if asyncio.iscoroutinefunction(fetch_fn):
            data = await fetch_fn()
        else:
            data = await asyncio.to_thread(fetch_fn)
        if container is not None:
            container.clear()
            with container:
                render_fn(data)
        else:
            render_fn(data)
        return data
    except Exception as exc:
        logger.warning("%s: %s", error_message, exc, exc_info=True)
        if notify_on_error:
            with contextlib.suppress(Exception):
                ui.notify(f"{error_message}: {exc}", type="negative")
        if not suppress_errors:
            raise
        return None
    finally:
        if spinner:
            spinner.visible = False
