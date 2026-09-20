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
