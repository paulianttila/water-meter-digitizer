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
        mock_tabs = mock_ui.tabs.return_value
        mock_tabs.props.return_value = mock_tabs
        mock_tabs.classes.return_value = mock_tabs
        mock_tabs.__enter__.return_value = mock_tabs
        mock_tabs.__exit__ = MagicMock()

        frontend.init(app, callbacks)
        assert captured_show is not None

        # Execute show callback (initial render only mounts active Meter tab)
        asyncio.run(captured_show())

        MockMeterPage.return_value.show.assert_called_once()
        MockServicesPage.return_value.show.assert_not_called()
        MockSetupPage.return_value.show.assert_not_called()
        MockConfigPage.return_value.show.assert_not_called()
        MockPreviousValuesPage.return_value.show.assert_not_called()
        MockApiConsolePage.return_value.show.assert_not_called()
        MockHelpPage.return_value.show.assert_not_called()
        MockAboutPage.return_value.show.assert_not_called()

        # Retrieve tab change listener and simulate activating tabs lazily
        on_tab_change = mock_ui.tabs.return_value.on_value_change.call_args[0][0]
        tab_targets = [
            ("services", MockServicesPage),
            ("setup", MockSetupPage),
            ("config", MockConfigPage),
            ("baselines", MockPreviousValuesPage),
            ("api_console", MockApiConsolePage),
            ("help", MockHelpPage),
            ("about", MockAboutPage),
        ]
        for tab_id, mock_page in tab_targets:
            asyncio.run(on_tab_change(tab_id))
            mock_page.return_value.show.assert_called_once()
            # Calling again does not re-mount / re-execute show (keep-alive)
            asyncio.run(on_tab_change(tab_id))
            mock_page.return_value.show.assert_called_once()


def test_build_head_html_includes_static_assets():
    """Verify _build_head_html combines favicons, fonts, CSS files, and JS files."""
    head_html = frontend._build_head_html()

    # Favicon and Fonts
    assert "favicon.svg" in head_html
    assert "fonts.googleapis.com" in head_html

    # CSS contents
    assert "--bg-primary" in head_html
    assert "nicegui-interactive-image" in head_html
    assert "gui-badge-status" in head_html
    assert "::-webkit-scrollbar" in head_html

    # JS contents
    assert "initNiceGUIStatusMonitor" in head_html
    assert "shift-move-active" in head_html
