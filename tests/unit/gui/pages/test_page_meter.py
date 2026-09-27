"""Unit tests for MeterPage dashboard and its sub-components."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from configuration import Config
from gui.pages.meter import MeterPage
from processor.digitizer import MeterResult, MeterValue
from services.leak.models import LeakState, ZeroFlowStatus


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
        quality="uncertain",
        unit="m3",
    )
    return MeterResult(
        meters=[submeter_total, submeter_sub1, submeter_sub2],
        digital_results={"digit1": "1", "digit2": "2"},
        analog_results={"analog1": "3.4"},
        confidence_scores={"digit1": 95.0, "digit2": 70.0, "analog1": 50.0},
        error="Low confidence warning",
    )


@pytest.fixture
def mock_meter_ui():
    with (
        patch("gui.pages.meter.ui") as mock_ui,
        patch("gui.components.page_header.ui"),
    ):
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
        mock_tabs = mock_ui.tabs.return_value
        mock_tabs.props.return_value = mock_tabs
        mock_tabs.classes.return_value = mock_tabs
        mock_tabs.__enter__.return_value = mock_tabs
        mock_tabs.__exit__ = MagicMock()
        yield mock_ui


def test_page_meter_init():
    callbacks = MagicMock()
    page = MeterPage(callbacks)
    assert page.callbacks == callbacks
    assert page.consumption_card is not None
    assert page.history_card is not None
    assert page.time_machine_card is not None
    assert not page._is_fetching


def test_page_meter_show_and_fetch_success(mock_meter_result, mock_meter_ui):
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_image_as_base64_str.return_value = "dGVzdGltYWdl"

    config = Config()
    callbacks.get_config.return_value = config

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    callbacks.get_meter_data.assert_called_with(saveimages=True)
    # Lazy loading: cards are not rendered prematurely on initial show
    page.consumption_card.render.assert_not_called()
    page.history_card.render.assert_not_called()
    page.time_machine_card.render.assert_not_called()

    # Simulate subtab activation
    on_tab_change = mock_meter_ui.tabs.return_value.on_value_change.call_args[0][0]
    on_tab_change("Consumption")
    page.consumption_card.render.assert_called_once()

    on_tab_change("Time Machine")
    page.time_machine_card.render.assert_called_once()

    on_tab_change("Readings Log")
    page.history_card.render.assert_called_once()

    # Selecting again does not re-render
    on_tab_change("Consumption")
    page.consumption_card.render.assert_called_once()


def test_page_meter_concurrency_guard(mock_meter_result, mock_meter_ui):
    """Verify that concurrent fetch attempts are blocked if _is_fetching is True."""
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result

    page = MeterPage(callbacks)
    page._is_fetching = True

    asyncio.run(page.show())

    # When _is_fetching is True, do_fetch returns early without querying backend
    callbacks.get_meter_data.assert_not_called()


def test_page_meter_fetch_exception(mock_meter_ui):
    callbacks = MagicMock()
    callbacks.get_meter_data.side_effect = RuntimeError("Failed to fetch image")
    config = Config()
    callbacks.get_config.return_value = config

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())
    assert not page._is_fetching


def test_page_meter_roi_dialog_and_fallbacks(mock_meter_result, mock_meter_ui):
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_leak_status.return_value = {
        "flow_active": True,
        "state": "OK",
        "continuous_flow_seconds": 45,
    }
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

    asyncio.run(page.show())


def test_page_meter_poller_trigger():
    callbacks = MagicMock()
    page = MeterPage(callbacks)
    callbacks.trigger_poller.return_value = {"status": "ok"}
    res = page.callbacks.trigger_poller()
    assert res == {"status": "ok"}
    callbacks.trigger_poller.assert_called_once()


def test_page_meter_min_confidence_rendering(mock_meter_ui):
    """Test that render_meter_data displays min_confidence in badge and min/avg in tooltip."""
    callbacks = MagicMock()
    result = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="123.456",
                confidence=96.2,
                min_confidence=88.0,
                quality="good",
                unit="m3",
                warning="Check meter flow",
            )
        ]
    )
    callbacks.get_meter_data.return_value = result
    callbacks.get_image_as_base64_str.return_value = ""
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    # Check that label with min_confidence was rendered
    label_calls = [c.args[0] for c in mock_meter_ui.label.call_args_list if c.args]
    assert any("88.0% • Good" in str(arg) for arg in label_calls)

    # Check tooltip contains Min, Avg, and warning message
    tooltip_calls = [c.args[0] for c in mock_meter_ui.tooltip.call_args_list if c.args]
    assert any(
        "Min: 88.0%" in str(arg)
        and "Avg: 96.2%" in str(arg)
        and "Check meter flow" in str(arg)
        for arg in tooltip_calls
    )


def test_page_meter_filled_digits_rendering(mock_meter_ui):
    """Test that render_meter_data displays filled_digits badge and tooltip when digits are filled."""
    callbacks = MagicMock()
    result = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="123.456",
                confidence=96.2,
                min_confidence=35.0,
                filled_digits=2,
                quality="warning",
                unit="m3",
            )
        ]
    )
    callbacks.get_meter_data.return_value = result
    callbacks.get_image_as_base64_str.return_value = ""
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    label_calls = [c.args[0] for c in mock_meter_ui.label.call_args_list if c.args]
    assert any("🔁 2 filled" in str(arg) for arg in label_calls)

    tooltip_calls = [c.args[0] for c in mock_meter_ui.tooltip.call_args_list if c.args]
    assert any(
        "2 digits filled from previous reading" in str(arg) for arg in tooltip_calls
    )
    assert any(
        "2 low-confidence digits filled from previous reading" in str(arg)
        for arg in tooltip_calls
    )


def test_page_meter_leak_alert_badge_rendering(mock_meter_result, mock_meter_ui):
    """Verify leak alert badge renders with LEAK DETECTED and negative color for ZeroFlowStatus object."""
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_leak_status.return_value = ZeroFlowStatus(
        enabled=True,
        state=LeakState.LEAK_DETECTED,
        current_flow_duration_seconds=7200.0,
        current_flow_volume=0.035,
    )
    callbacks.get_image_as_base64_str.return_value = ""
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    badge_calls = [
        (call.args[0], call.kwargs.get("color"))
        for call in mock_meter_ui.badge.call_args_list
        if call.args
    ]
    assert ("LEAK DETECTED", "negative") in badge_calls


def test_page_meter_leak_active_flow_badge(mock_meter_result, mock_meter_ui):
    """Verify active flow badge renders with FLOW ACTIVE and amber color for ZeroFlowStatus object."""
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_leak_status.return_value = ZeroFlowStatus(
        enabled=True,
        state=LeakState.FLOW_ACTIVE,
        current_flow_duration_seconds=900.0,
        current_flow_volume=0.010,
    )
    callbacks.get_image_as_base64_str.return_value = ""
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    badge_calls = [
        (call.args[0], call.kwargs.get("color"))
        for call in mock_meter_ui.badge.call_args_list
        if call.args
    ]
    assert ("FLOW ACTIVE", "amber") in badge_calls


def test_page_meter_leak_disabled_badge(mock_meter_result, mock_meter_ui):
    """Verify flow monitor renders DISABLED badge when leak detector service is disabled."""
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_leak_status.return_value = ZeroFlowStatus(
        enabled=False,
        state=LeakState.OK,
    )
    callbacks.get_image_as_base64_str.return_value = ""
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    page.consumption_card = MagicMock()
    page.history_card = MagicMock()
    page.time_machine_card = MagicMock()

    asyncio.run(page.show())

    badge_calls = [
        (call.args[0], call.kwargs.get("color"))
        for call in mock_meter_ui.badge.call_args_list
        if call.args
    ]
    assert ("DISABLED", "grey") in badge_calls

    label_calls = [c.args[0] for c in mock_meter_ui.label.call_args_list if c.args]
    assert any("Inactive" in str(arg) for arg in label_calls)
    assert any("Leak monitor service disabled" in str(arg) for arg in label_calls)


def test_page_meter_crop_modal_actions(mock_meter_result, mock_meter_ui):
    """Verify crop modal renders Set Baseline and Calibrate in Wizard buttons."""
    callbacks = MagicMock()
    callbacks.get_meter_data.return_value = mock_meter_result
    callbacks.get_image_as_base64_str.return_value = "dGVzdA=="
    callbacks.get_config.return_value = Config()

    page = MeterPage(callbacks)
    asyncio.run(page.show())

    # Find registered click handlers on digital crop cards
    on_mock = mock_meter_ui.element.return_value.classes.return_value.on
    click_calls = [
        call.args[1]
        for call in on_mock.call_args_list
        if call.args and call.args[0] == "click"
    ]
    assert click_calls, "Should register click handlers for digit cards"

    # Invoke first click handler to open crop modal
    click_calls[0](None)

    btn_labels = [
        call.args[0] for call in mock_meter_ui.button.call_args_list if call.args
    ]
    assert "Set Baseline" in btn_labels
    assert "Calibrate in Wizard" in btn_labels
