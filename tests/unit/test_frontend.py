"""Unit tests for frontend GUI initialization and main layout."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI

import gui.frontend as frontend


def test_init_gui():
    app = FastAPI()
    callbacks = MagicMock()

    with (patch("gui.frontend.ui") as mock_ui,):
        mock_ui.page.return_value = lambda func: func
        frontend.init(app, callbacks)

        assert frontend._callbacks == callbacks
        mock_ui.run_with.assert_called_once()


def test_frontend_show_callback():
    app = FastAPI()
    callbacks = MagicMock()
    captured_show = None

    def capture_decorator(*args, **kwargs):
        def wrapper(func):
            nonlocal captured_show
            captured_show = func
            return func

        return wrapper

    with (
        patch("gui.frontend.MeterPage") as MockMeterPage,
        patch("gui.frontend.ServicesPage") as MockServicesPage,
        patch("gui.frontend.SetupPage") as MockSetupPage,
        patch("gui.frontend.ConfigPage") as MockConfigPage,
        patch("gui.frontend.PreviousValuesPage") as MockPreviousValuesPage,
        patch("gui.frontend.ApiConsolePage") as MockApiConsolePage,
        patch("gui.frontend.HelpPage") as MockHelpPage,
        patch("gui.frontend.AboutPage") as MockAboutPage,
        patch("gui.frontend.ui") as mock_ui,
    ):
        mock_ui.page.side_effect = capture_decorator

        # Configure async show methods
        MockMeterPage.return_value.show = AsyncMock()
        MockServicesPage.return_value.show = AsyncMock()
        MockSetupPage.return_value.show = AsyncMock()

        # Configure context managers on mock_ui
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.splitter.return_value.__enter__ = MagicMock()
        mock_ui.splitter.return_value.__exit__ = MagicMock()
        mock_ui.tab_panels.return_value.__enter__ = MagicMock()
        mock_ui.tab_panels.return_value.__exit__ = MagicMock()
        mock_ui.tab_panel.return_value.__enter__ = MagicMock()
        mock_ui.tab_panel.return_value.__exit__ = MagicMock()
        mock_ui.tabs.return_value.__enter__ = MagicMock()
        mock_ui.tabs.return_value.__exit__ = MagicMock()

        frontend.init(app, callbacks)
        assert captured_show is not None

        # Execute show callback
        asyncio.run(captured_show())

        MockMeterPage.return_value.show.assert_called_once()
        MockServicesPage.return_value.show.assert_called_once()
        MockSetupPage.return_value.show.assert_called_once()
        MockConfigPage.return_value.show.assert_called_once()
        MockPreviousValuesPage.return_value.show.assert_called_once()
        MockApiConsolePage.return_value.show.assert_called_once()
        MockHelpPage.return_value.show.assert_called_once()
        MockAboutPage.return_value.show.assert_called_once()
