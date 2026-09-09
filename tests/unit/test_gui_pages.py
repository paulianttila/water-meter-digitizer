"""Unit tests for standalone GUI pages (AboutPage, HelpPage, theme)."""

from unittest.mock import patch

import gui.theme as theme
from gui.page_about import AboutPage
from gui.page_help import HelpPage


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


def test_page_help_show():
    page = HelpPage()
    with patch("gui.page_help.ui"):
        page.show()
