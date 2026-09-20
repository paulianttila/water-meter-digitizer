"""Unit tests for reusable page and card header components."""

from unittest.mock import MagicMock, patch

from gui.components.page_header import card_header, page_header, render_page_header


def test_render_page_header() -> None:
    """Test render_page_header function returns a row."""
    with (
        patch("nicegui.ui.row") as mock_row,
        patch("nicegui.ui.element") as mock_el,
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.column") as mock_col,
        patch("nicegui.ui.label"),
    ):
        mock_row.return_value.__enter__ = MagicMock()
        mock_row.return_value.__exit__ = MagicMock()
        mock_el.return_value.__enter__ = MagicMock()
        mock_el.return_value.__exit__ = MagicMock()
        mock_col.return_value.__enter__ = MagicMock()
        mock_col.return_value.__exit__ = MagicMock()

        row = render_page_header(
            title="Test Page",
            subtitle="Test Subtitle",
            icon="settings",
            color="cyan",
        )
        assert row is not None


def test_page_header_context_manager() -> None:
    """Test page_header context manager yields an action row."""
    with (
        patch("nicegui.ui.row") as mock_row,
        patch("nicegui.ui.element") as mock_el,
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.column") as mock_col,
        patch("nicegui.ui.label"),
    ):
        mock_row.return_value.__enter__ = MagicMock(return_value="actions_row")
        mock_row.return_value.__exit__ = MagicMock()
        mock_el.return_value.__enter__ = MagicMock()
        mock_el.return_value.__exit__ = MagicMock()
        mock_col.return_value.__enter__ = MagicMock()
        mock_col.return_value.__exit__ = MagicMock()

        with page_header(
            title="Test Page",
            subtitle="Test Subtitle",
        ) as actions:
            assert actions is not None


def test_card_header_basic() -> None:
    """Test card_header without subtitle or badge."""
    with (
        patch("nicegui.ui.row") as mock_row,
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.label"),
    ):
        mock_row.return_value.__enter__ = MagicMock(return_value="actions_row")
        mock_row.return_value.__exit__ = MagicMock()

        with card_header(
            title="Card Title",
            icon="hub",
            color="cyan",
        ) as actions:
            assert actions is not None


def test_card_header_with_badge_and_subtitle() -> None:
    """Test card_header with subtitle and badge."""
    with (
        patch("nicegui.ui.row") as mock_row,
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.column") as mock_col,
        patch("nicegui.ui.element") as mock_el,
        patch("nicegui.ui.label"),
    ):
        mock_row.return_value.__enter__ = MagicMock(return_value="actions_row")
        mock_row.return_value.__exit__ = MagicMock()
        mock_col.return_value.__enter__ = MagicMock()
        mock_col.return_value.__exit__ = MagicMock()
        mock_el.return_value.__enter__ = MagicMock()
        mock_el.return_value.__exit__ = MagicMock()

        with card_header(
            title="Card Title",
            subtitle="Card Subtitle",
            icon="health_and_safety",
            color="cyan",
            badge_text="HEALTHY",
            badge_cls="bg-emerald-950",
        ) as actions:
            assert actions is not None
