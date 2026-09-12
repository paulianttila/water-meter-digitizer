"""Unit tests for MeterPage dashboard and its sub-components."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from configuration import Config
from gui.page_meter import MeterPage
from processor.digitizer import MeterResult, MeterValue


@pytest.fixture
def mock_meter_result():
    submeter_total = MeterValue(
        name="total",
        value="123.456",
        confidence=96.2,
        quality="good",
        unit="m3",
    )
    submeter_sub1 = MeterValue(
        name="sub1",
        value="12.3",
        confidence=65.0,
        quality="warning",
        unit="m3",
    )
    submeter_sub2 = MeterValue(
        name="sub2",
        value="0.5",
        confidence=40.0,
        quality="bad",
        unit="m3",
    )
    return MeterResult(
        meters=[submeter_total, submeter_sub1, submeter_sub2],
        digital_results={"digit1": 1, "digit2": 2},
        analog_results={"analog1": 3.4},
        confidence_scores={"digit1": 95.0, "digit2": 70.0, "analog1": 50.0},
        error="Low confidence warning",
    )


def test_page_meter_init():
    callbacks = MagicMock()
    page = MeterPage(callbacks)
    assert page.callbacks == callbacks
    assert page.consumption_card is not None
    assert page.history_card is not None
    assert page.time_machine_card is not None


def test_page_meter_show_and_fetch_success(mock_meter_result):
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_image_as_base64_str.return_value = "dGVzdGltYWdl"

    config = Config()
    callbacks.get_config.return_value = config

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    with patch("gui.page_meter.ui") as mock_ui:
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock()
        mock_ui.dialog.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.tab_panels.return_value.__enter__ = MagicMock()
        mock_ui.tab_panels.return_value.__exit__ = MagicMock()
        mock_ui.tab_panel.return_value.__enter__ = MagicMock()
        mock_ui.tab_panel.return_value.__exit__ = MagicMock()
        asyncio.run(page.show())

    callbacks.get_meter_data.assert_called_with(saveimages=True)
    page.consumption_card.render.assert_called_once()
    page.history_card.render.assert_called_once()
    page.time_machine_card.render.assert_called_once()


def test_page_meter_fetch_exception():
    callbacks = MagicMock()
    callbacks.get_meter_data.side_effect = RuntimeError("Failed to fetch image")
    config = Config()
    callbacks.get_config.return_value = config

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    with patch("gui.page_meter.ui") as mock_ui:
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.tab_panels.return_value.__enter__ = MagicMock()
        mock_ui.tab_panels.return_value.__exit__ = MagicMock()
        mock_ui.tab_panel.return_value.__enter__ = MagicMock()
        mock_ui.tab_panel.return_value.__exit__ = MagicMock()
        asyncio.run(page.show())


def test_page_meter_roi_dialog_and_fallbacks(mock_meter_result):
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_image_as_base64_str.side_effect = [
        "dGVzdGZpbmFs",  # processed capture
        "dGVzdGRpZzE=",  # digit1
        "dGVzdGRpZzI=",  # digit2
        "dGVzdGFuYTE=",  # analog1
        "dGVzdHJvaQ==",  # open_roi_dialog -> roi
    ]
    config = Config()
    callbacks.get_config.return_value = config

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    with patch("gui.page_meter.ui") as mock_ui:
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock()
        mock_ui.dialog.return_value.__exit__ = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.tab_panels.return_value.__enter__ = MagicMock()
        mock_ui.tab_panels.return_value.__exit__ = MagicMock()
        mock_ui.tab_panel.return_value.__enter__ = MagicMock()
        mock_ui.tab_panel.return_value.__exit__ = MagicMock()
        asyncio.run(page.show())
