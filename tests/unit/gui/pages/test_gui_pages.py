"""Unit tests for NiceGUI top-level page routing and instantiation."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import gui.theme as theme
from gui.pages.about import AboutPage
from gui.pages.help import HelpPage


@pytest.fixture
def mock_callbacks():
    cb = MagicMock()
    health_payload = {
        "status": "healthy",
        "uptime": {
            "uptime_human": "1d 2h",
            "uptime_seconds": 93600,
            "started_at": "2026-09-14T10:00:00",
        },
        "camera": {
            "source": "http://192.168.1.50/capture",
            "connected": True,
            "latency_ms": 42.5,
        },
        "memory": {"rss_mb": 145.2, "peak_rss_mb": 180.5, "percent": 12.4},
        "cache": {"hits": 120, "misses": 5, "size": 30, "max_size": 100},
        "models": {
            "digital": {"name": "dig100.tflite", "loaded": True},
            "analog": {"name": "ana100.tflite", "loaded": True},
        },
        "system": {
            "cpu_percent": 15.2,
            "threads_count": 8,
            "python_version": "3.11.13",
            "platform": "Darwin-25.0.0",
        },
    }
    cb.get_health_data.return_value = health_payload
    return cb


def test_theme_constants():
    assert "slate" in theme.CARD_CONTAINER
    assert "emerald" in theme.BADGE_SUCCESS
    assert "cyan" in theme.BADGE_INFO
    assert "amber" in theme.BADGE_WARNING
    assert "rose" in theme.BADGE_ERROR


def test_theme_copy_to_clipboard():
    with patch("gui.theme.ui") as mock_ui:
        theme.copy_to_clipboard("test snippet", notify_message="Copied successfully")
        mock_ui.clipboard.write.assert_called_once_with("test snippet")
        mock_ui.notify.assert_called_once_with("Copied successfully", type="positive")


def test_page_about_show():
    page = AboutPage()
    with patch("gui.pages.about.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_about_with_callbacks(mock_callbacks):
    page = AboutPage(callbacks=mock_callbacks)
    diag = page._get_diagnostics_data()
    assert "version" in diag
    assert "python" in diag
    assert "memory" in diag
    assert "health" in diag
    with patch("gui.pages.about.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_about_with_failing_health_callback():
    mock_cb = MagicMock()
    mock_cb.get_health_data.side_effect = RuntimeError("Health failure")
    page = AboutPage(callbacks=mock_cb)
    diag = page._get_diagnostics_data()
    assert "error" in diag["health"]
    with patch("gui.pages.about.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_help_show():
    page = HelpPage()
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    with patch("gui.pages.help.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_help_with_callbacks(mock_callbacks):
    page = HelpPage(callbacks=mock_callbacks)
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    assert "System Status" in bundle
    with patch("gui.pages.help.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_help_with_failing_health_callback():
    mock_cb = MagicMock()
    mock_cb.get_health_data.side_effect = RuntimeError("Health error")
    page = HelpPage(callbacks=mock_cb)
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    with patch("gui.pages.help.ui"), patch("gui.components.page_header.ui"):
        asyncio.run(page.show())


def test_page_help_load_markdown_files():
    from gui.pages.help import _load_help

    expected_files = [
        "pipeline_architecture.md",
        "wizard_steps.md",
        "calibration_tips.md",
        "canvas_keyboard_shortcuts.md",
        "roi_best_practices.md",
        "api_reference.md",
        "mqtt_integration.md",
        "home_assistant.md",
    ]
    for filename in expected_files:
        content = _load_help(filename)
        assert len(content) > 0, f"Help file {filename} should not be empty"

    assert _load_help("non_existent_file.md") == ""


def test_page_api_console_show(mock_callbacks):
    from gui.pages.api_console import ApiConsolePage

    page = ApiConsolePage(callbacks=mock_callbacks)
    with (
        patch("gui.pages.api_console.ui"),
        patch("gui.components.page_header.ui"),
        patch.object(page.rest_panel, "render"),
        patch.object(page.mock_panel, "render"),
    ):
        asyncio.run(page.show())
