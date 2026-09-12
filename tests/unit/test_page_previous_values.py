"""Unit tests for PreviousValuesPage baseline manager."""

import asyncio
from unittest.mock import MagicMock, patch

from configuration import Config, MeterConfig
from gui.page_previous_values import PreviousValuesPage


def test_previous_values_page_show_and_refresh():
    callbacks = MagicMock()
    config = Config()
    config.meter_configs = [MeterConfig(name="total", format="{digit1}")]
    callbacks.get_config.return_value = config
    callbacks.get_previous_values.return_value = {
        "total": {"value": "123.456", "time": "2026-09-12 11:00:00"}
    }

    page = PreviousValuesPage(callbacks)

    with patch("gui.page_previous_values.ui") as mock_ui:
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()

        page.show()
        assert page.table_container is not None

        # Test refresh_table
        page.refresh_table()
        callbacks.get_previous_values.assert_called()


def test_previous_values_page_save_baseline():
    callbacks = MagicMock()
    callbacks.set_previous_value.return_value = {
        "status": "success",
        "message": "Updated",
    }
    page = PreviousValuesPage(callbacks)
    page.meter_select = MagicMock(value="total")
    page.value_input = MagicMock(value="555.123")
    page.refresh_table = MagicMock()

    with patch("gui.page_previous_values.ui.notify"):
        asyncio.run(page._save_baseline())
        callbacks.set_previous_value.assert_called_with("total", "555.123")
        page.refresh_table.assert_called_once()
