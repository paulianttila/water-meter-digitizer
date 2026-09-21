"""Unit tests for ServicesPage in src/gui/page_services.py."""

import asyncio
from unittest.mock import MagicMock, patch

from callbacks import Callbacks
from gui.components import DiagnosticsCard, LeakMonitorCard, ServicesStatusCard
from gui.page_services import ServicesPage


def test_services_page_init():
    mock_callbacks = MagicMock(spec=Callbacks)
    page = ServicesPage(mock_callbacks)
    assert isinstance(page.diagnostics_card, DiagnosticsCard)
    assert isinstance(page.leak_card, LeakMonitorCard)
    assert isinstance(page.services_card, ServicesStatusCard)
    assert page.callbacks == mock_callbacks


def test_services_page_show_and_fetch():
    mock_callbacks = MagicMock(spec=Callbacks)
    mock_callbacks.get_health_data.return_value = {
        "status": "healthy",
        "cpu_percent": 12.5,
    }
    mock_callbacks.get_leak_status.return_value = {"enabled": True, "state": "OK"}
    mock_callbacks.get_poller_status.return_value = {"enabled": True, "running": True}
    mock_callbacks.get_mqtt_status.return_value = {"enabled": True, "connected": True}

    page = ServicesPage(mock_callbacks)
    page.diagnostics_card = MagicMock(spec=DiagnosticsCard)
    page.leak_card = MagicMock(spec=LeakMonitorCard)
    page.services_card = MagicMock(spec=ServicesStatusCard)

    with patch("gui.page_services.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())

        page.diagnostics_card.render.assert_called_once()
        page.leak_card.render.assert_called_once()
        page.services_card.render.assert_called_once()
        mock_callbacks.get_health_data.assert_called()
        mock_callbacks.get_leak_status.assert_called()
        mock_callbacks.get_poller_status.assert_called()
        mock_callbacks.get_mqtt_status.assert_called()


def test_services_page_dispose():
    mock_callbacks = MagicMock(spec=Callbacks)
    page = ServicesPage(mock_callbacks)
    page.diagnostics_card = MagicMock(spec=DiagnosticsCard)
    page.leak_card = MagicMock(spec=LeakMonitorCard)
    page.services_card = MagicMock(spec=ServicesStatusCard)

    page.dispose()
    page.diagnostics_card.dispose.assert_called_once()
    page.leak_card.dispose.assert_called_once()
    page.services_card.dispose.assert_called_once()
    assert not page.is_mounted


def test_services_page_fetch_all_telemetry_errors():
    mock_callbacks = MagicMock(spec=Callbacks)
    mock_callbacks.get_health_data.side_effect = RuntimeError("Health err")
    mock_callbacks.get_leak_status.side_effect = RuntimeError("Leak err")
    mock_callbacks.get_poller_status.side_effect = RuntimeError("Poller err")
    mock_callbacks.get_mqtt_status.side_effect = RuntimeError("MQTT err")

    page = ServicesPage(mock_callbacks)
    page.spinner = MagicMock()

    # Should not raise exception
    asyncio.run(page.fetch_all_telemetry())
    assert page.spinner.visible is False
