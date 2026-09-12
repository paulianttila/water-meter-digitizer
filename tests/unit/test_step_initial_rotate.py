"""Unit tests for InitialRotateStep in Setup Wizard."""

import asyncio
from unittest.mock import MagicMock, patch

from configuration import Alignment
from gui.step_initial_rotate import InitialRotateStep


def test_initial_rotate_init_and_load():
    set_img = MagicMock()
    step = InitialRotateStep("Rotate", set_image_callback=set_img)
    step.angle_label = MagicMock()

    alignment = Alignment(rotate_angle=90.0)
    step.load_from_config(alignment)
    assert step.angle == 90
    step.angle_label.set_text.assert_called_with("Rotate: 90°")


def test_initial_rotate_actions():
    set_img = MagicMock()
    step = InitialRotateStep("Rotate", set_image_callback=set_img)
    step.angle_label = MagicMock()

    with patch.object(
        step, "_rotate_image", side_effect=lambda img, ang: f"{img}_rot_{ang}"
    ):
        step.update_image("base_image")
        assert step.org_image == "base_image"

        asyncio.run(step._rotate_left())
        assert step.angle == -90
        step.angle_label.set_text.assert_called_with("Rotate: -90°")

        asyncio.run(step._rotate_180())
        assert step.angle == 180
        step.angle_label.set_text.assert_called_with("Rotate: 180°")

        asyncio.run(step._rotate_right())
        assert step.angle == 90
        step.angle_label.set_text.assert_called_with("Rotate: 90°")

        step._reset_image()
        assert step.angle == 0
        assert step.image == "base_image"


def test_initial_rotate_show():
    set_img = MagicMock()
    step = InitialRotateStep("Rotate", set_image_callback=set_img)

    with (
        patch("gui.step_initial_rotate.ui") as mock_ui,
        patch("gui.step_base.ui") as mock_base_ui,
    ):
        mock_ui.step.return_value.__enter__ = MagicMock()
        mock_ui.step.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_base_ui.expansion.return_value.__enter__ = MagicMock()
        mock_base_ui.expansion.return_value.__exit__ = MagicMock()
        mock_base_ui.column.return_value.__enter__ = MagicMock()
        mock_base_ui.column.return_value.__exit__ = MagicMock()

        stepper = MagicMock()
        asyncio.run(step.show(stepper))
        assert step.angle_label is not None
