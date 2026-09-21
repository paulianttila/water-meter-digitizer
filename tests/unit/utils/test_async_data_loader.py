"""Unit tests for async_data_loader utility."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from gui.components.async_data_loader import async_fetch_and_render


def test_async_fetch_and_render_sync_fetch_success():
    async def _test():
        mock_container = MagicMock()
        mock_spinner = MagicMock()
        rendered_data = []

        def sync_fetch():
            return {"status": "ok", "value": 42}

        def render(data):
            rendered_data.append(data)

        result = await async_fetch_and_render(
            fetch_fn=sync_fetch,
            render_fn=render,
            container=mock_container,
            spinner=mock_spinner,
        )

        assert result == {"status": "ok", "value": 42}
        assert rendered_data == [{"status": "ok", "value": 42}]
        assert mock_spinner.visible is False
        mock_container.clear.assert_called_once()

    asyncio.run(_test())


def test_async_fetch_and_render_async_fetch_success():
    async def _test():
        rendered_data = []

        async def async_fetch():
            return "async_result"

        def render(data):
            rendered_data.append(data)

        result = await async_fetch_and_render(
            fetch_fn=async_fetch,
            render_fn=render,
            container=None,
            spinner=None,
        )

        assert result == "async_result"
        assert rendered_data == ["async_result"]

    asyncio.run(_test())


def test_async_fetch_and_render_error_suppressed():
    async def _test():
        mock_spinner = MagicMock()

        def failing_fetch():
            raise ValueError("Connection lost")

        render = MagicMock()

        with patch("nicegui.ui.notify") as mock_notify:
            result = await async_fetch_and_render(
                fetch_fn=failing_fetch,
                render_fn=render,
                spinner=mock_spinner,
                error_message="Test failed",
                notify_on_error=True,
                suppress_errors=True,
            )

        assert result is None
        assert mock_spinner.visible is False
        render.assert_not_called()
        mock_notify.assert_called_once_with(
            "Test failed: Connection lost", type="negative"
        )

    asyncio.run(_test())


def test_async_fetch_and_render_error_re_raised():
    async def _test():
        mock_spinner = MagicMock()

        def failing_fetch():
            raise RuntimeError("Fatal crash")

        render = MagicMock()

        with (
            patch("nicegui.ui.notify") as mock_notify,
            pytest.raises(RuntimeError, match="Fatal crash"),
        ):
            await async_fetch_and_render(
                fetch_fn=failing_fetch,
                render_fn=render,
                spinner=mock_spinner,
                error_message="Fatal error",
                notify_on_error=False,
                suppress_errors=False,
            )

        assert mock_spinner.visible is False
        render.assert_not_called()
        mock_notify.assert_not_called()

    asyncio.run(_test())
