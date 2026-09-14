"""Unit tests for PreviousValuesPage baseline manager."""

import asyncio
from unittest.mock import MagicMock, patch

from configuration import Config, MeterConfig
from gui.page_previous_values import PreviousValuesPage


def test_previous_values_page_show_and_refresh():
    callbacks = MagicMock()
    config = Config()
    config.meter_configs = [
        MeterConfig(name="total", format="{digit1}", use_previous_value=True)
    ]
    callbacks.get_config.return_value = config
    callbacks.get_previous_values.return_value = {
        "total": {"value": "123.4560", "time": "2026-09-12 11:00:00"}
    }
    meter_data = MagicMock()
    mock_meter = MagicMock()
    mock_meter.name = "total"
    mock_meter.value = 123.7060
    meter_data.meters = [mock_meter]
    callbacks.get_meter_data.return_value = meter_data

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
        assert page.cards_container is not None

        # Test refresh_table
        page.refresh_table()
        callbacks.get_previous_values.assert_called()


def test_previous_values_stepper_and_live_presets():
    callbacks = MagicMock()
    page = PreviousValuesPage(callbacks)
    page.value_input = MagicMock(value="10.5000")
    page.meter_select = MagicMock(value="total")
    page._live_readouts = {"total": "15.7500"}

    # Stepper increments
    page._apply_stepper_delta(1.0)
    assert page.value_input.value == "11.5"

    page._apply_stepper_delta(-0.1)
    assert page.value_input.value == "11.4"

    # Use live in form
    with patch("gui.page_previous_values.ui.notify"):
        page._use_live_in_form()
        assert page.value_input.value == "15.7500"


def test_previous_values_export_and_modal():
    callbacks = MagicMock()
    callbacks.get_previous_values.return_value = {
        "total": {"value": "100.000", "time": "2026-09-14 12:00:00"}
    }
    page = PreviousValuesPage(callbacks)

    with (
        patch("gui.page_previous_values.ui.download") as mock_download,
        patch("gui.page_previous_values.ui.notify"),
    ):
        page._export_csv()
        mock_download.assert_called_once()
        args, kwargs = mock_download.call_args
        assert kwargs["filename"] == "meter_baselines.csv"
        assert b"total,100.000" in args[0]

    with (
        patch("gui.page_previous_values.ui.dialog") as mock_dialog,
        patch("gui.page_previous_values.ui.card"),
    ):
        mock_dialog.return_value.__enter__ = MagicMock()
        mock_dialog.return_value.__exit__ = MagicMock()
        page._open_raw_prevalue_modal()


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
