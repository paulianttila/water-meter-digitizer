"""Unit tests for BasePage lifecycle and contract."""

from unittest.mock import MagicMock

import pytest

from callbacks import Callbacks
from gui.base_page import BasePage


class DummyPage(BasePage):
    """Concrete implementation for testing BasePage."""

    def __init__(self, callbacks: Callbacks | None = None) -> None:
        super().__init__(callbacks)
        self.rendered = False

    async def show(self) -> None:
        self.rendered = True


def test_base_page_init():
    callbacks = MagicMock()
    page = DummyPage(callbacks)
    assert page.callbacks == callbacks
    assert page.spinner is None


def test_base_page_init_no_callbacks():
    page = DummyPage()
    assert page.callbacks is None
    assert page.spinner is None


@pytest.mark.anyio
async def test_base_page_async_show():
    page = DummyPage()
    assert not page.rendered
    await page.show()
    assert page.rendered


def test_base_page_dispose():
    page = DummyPage()
    page.spinner = MagicMock()
    page._mounted = True

    assert page.is_mounted
    page.dispose()
    assert not page.is_mounted
    assert page.spinner is None

    # Repeated dispose should be idempotent
    page.dispose()
    assert not page.is_mounted
    assert page.spinner is None


@pytest.mark.anyio
async def test_base_page_concurrent_mount_and_dispose():
    import anyio

    page = DummyPage()

    async def mount():
        page._mounted = True
        await page.show()

    async def unmount():
        await anyio.sleep(0.005)
        page.dispose()

    async with anyio.create_task_group() as tg:
        tg.start_soon(mount)
        tg.start_soon(unmount)

    assert not page.is_mounted
    assert page.rendered
