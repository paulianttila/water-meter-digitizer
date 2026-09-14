from unittest.mock import MagicMock, patch

import pytest

import gui.theme as theme
from gui.page_about import AboutPage
from gui.page_help import HelpPage


@pytest.fixture
def mock_callbacks():
    cb = MagicMock()
    cb._get_health_data.return_value = {
        "status": "healthy",
        "uptime": {
            "uptime_human": "1d 2h",
            "uptime_seconds": 93600,
            "started_at": "2026-09-14T10:00:00",
        },
        "camera": {
            "reachable": True,
            "latency_ms": 12.5,
            "status_code": 200,
            "url": "http://cam.local/jpg",
        },
        "memory": {"rss_mb": 45.2, "peak_rss_mb": 50.1},
        "models": {
            "digital": {"path": "model/digital.tflite", "exists": True},
            "analog": {"path": "model/analog.tflite", "exists": True},
            "avg_inference_ms": 14.2,
        },
    }
    return cb


def test_theme_constants():
    assert "slate" in theme.CARD_CONTAINER
    assert "emerald" in theme.BADGE_SUCCESS
    assert "cyan" in theme.BADGE_INFO
    assert "amber" in theme.BADGE_WARNING
    assert "rose" in theme.BADGE_ERROR


def test_page_about_show():
    page = AboutPage()
    with patch("gui.page_about.ui"):
        page.show()


def test_page_about_with_callbacks(mock_callbacks):
    page = AboutPage(callbacks=mock_callbacks)
    diag = page._get_diagnostics_data()
    assert "version" in diag
    assert "python" in diag
    assert "memory" in diag
    assert "health" in diag
    with patch("gui.page_about.ui"):
        page.show()


def test_page_about_with_failing_health_callback():
    mock_cb = MagicMock()
    mock_cb._get_health_data.side_effect = RuntimeError("Health failure")
    page = AboutPage(callbacks=mock_cb)
    diag = page._get_diagnostics_data()
    assert "error" in diag["health"]
    with patch("gui.page_about.ui"):
        page.show()


def test_page_help_show():
    page = HelpPage()
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    with patch("gui.page_help.ui"):
        page.show()


def test_page_help_with_callbacks(mock_callbacks):
    page = HelpPage(callbacks=mock_callbacks)
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    assert "System Status" in bundle
    with patch("gui.page_help.ui"):
        page.show()


def test_page_help_with_failing_health_callback():
    mock_cb = MagicMock()
    mock_cb._get_health_data.side_effect = RuntimeError("Health error")
    page = HelpPage(callbacks=mock_cb)
    bundle = page._generate_support_bundle()
    assert "Support Diagnostic Bundle" in bundle
    with patch("gui.page_help.ui"):
        page.show()
