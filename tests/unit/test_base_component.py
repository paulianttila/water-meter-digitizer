"""Unit tests for BaseComponent lifecycle and component cleanup."""

from unittest.mock import MagicMock

from callbacks import Callbacks
from gui.components.base_component import BaseComponent
from gui.components.consumption_card import ConsumptionCard
from gui.components.diagnostics_card import DiagnosticsCard
from gui.components.history_table_card import HistoryTableCard
from gui.components.leak_monitor_card import LeakMonitorCard
from gui.components.services_status_card import ServicesStatusCard
from gui.components.time_machine_card import TimeMachineCard
from gui.page_meter import MeterPage
from gui.page_services import ServicesPage


def test_base_component_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    component = BaseComponent(callbacks)

    assert not component.is_mounted
    assert component.container is None

    mock_container = MagicMock()
    component.render(mock_container)
    assert component.is_mounted
    assert component.container == mock_container

    component.dispose()
    assert not component.is_mounted
    assert component.container is None


def test_diagnostics_card_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    card = DiagnosticsCard(callbacks)
    card._data = {"status": "healthy"}

    mock_container = MagicMock()
    card.render(mock_container)
    assert card.is_mounted
    assert card.container == mock_container

    card.dispose()
    assert not card.is_mounted
    assert card.container is None
    assert card._data == {}


def test_services_status_card_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    card = ServicesStatusCard(callbacks)
    card._poller_data = {"enabled": True}
    card._mqtt_data = {"connected": True}

    mock_container = MagicMock()
    card.render(mock_container)
    assert card.is_mounted

    card.dispose()
    assert not card.is_mounted
    assert card.container is None
    assert card._poller_data == {}
    assert card._mqtt_data == {}


def test_leak_monitor_card_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    card = LeakMonitorCard(callbacks)
    card._data = {"leak_detected": False}

    mock_container = MagicMock()
    card.render(mock_container)
    assert card.is_mounted

    card.dispose()
    assert not card.is_mounted
    assert card.container is None
    assert card._data == {}


def test_consumption_and_history_card_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    callbacks.get_storage.return_value = None
    consumption_card = ConsumptionCard(callbacks)
    history_card = HistoryTableCard(callbacks)

    mock_container = MagicMock()
    consumption_card.render(mock_container)
    history_card.render(mock_container)

    assert consumption_card.is_mounted
    assert history_card.is_mounted

    consumption_card.dispose()
    history_card.dispose()

    assert not consumption_card.is_mounted
    assert not history_card.is_mounted


def test_time_machine_card_lifecycle():
    callbacks = MagicMock(spec=Callbacks)
    card = TimeMachineCard(callbacks)
    mock_timer = MagicMock()
    card._timer = mock_timer
    card.is_playing = True
    card.timeline_records = [{"id": 1}]

    mock_container = MagicMock()
    card.render(mock_container)
    assert card.is_mounted

    card.dispose()
    assert not card.is_mounted
    assert card.container is None
    assert not card.is_playing
    assert card._timer is None
    assert card.timeline_records == []
    mock_timer.cancel.assert_called_once()


def test_meter_page_and_services_page_dispose():
    callbacks = MagicMock(spec=Callbacks)
    meter_page = MeterPage(callbacks)
    mock_timer = MagicMock()
    meter_page._auto_timer = mock_timer

    mock_task = MagicMock()
    mock_task.done.return_value = False
    meter_page._fetch_task = mock_task

    meter_page.dispose()
    assert meter_page._auto_timer is None
    mock_timer.cancel.assert_called_once()
    mock_task.cancel.assert_called_once()
    assert not meter_page.consumption_card.is_mounted

    services_page = ServicesPage(callbacks)
    services_page.dispose()
    assert not services_page.diagnostics_card.is_mounted
    assert not services_page.leak_card.is_mounted
    assert not services_page.services_card.is_mounted
