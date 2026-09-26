"""Unit tests for config_onboarding_dialog."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from gui.dialogs.config_onboarding_dialog import show_config_onboarding_dialog


def test_show_config_onboarding_dialog_wizard_flow():
    callbacks = MagicMock()
    callbacks.get_target_config_file.return_value = "config/custom/config.ini"
    callbacks.init_profile_for_wizard.return_value = True

    tabs = MagicMock()
    setup_tab = MagicMock()
    load_tab_fn = AsyncMock()

    with (patch("gui.dialogs.config_onboarding_dialog.ui") as mock_ui,):
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_dialog.props.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        show_config_onboarding_dialog(
            callbacks=callbacks,
            tabs=tabs,
            setup_tab=setup_tab,
            load_tab_fn=load_tab_fn,
        )

        mock_dialog.open.assert_called_once()
        # Find Continue button on_click callback
        button_calls = mock_ui.button.call_args_list
        assert len(button_calls) >= 1
        continue_click = button_calls[0].kwargs.get("on_click")
        assert continue_click is not None

        # Execute Continue callback (default selected_mode is "wizard")
        asyncio.run(continue_click())

        callbacks.init_profile_for_wizard.assert_called_once()
        callbacks.use_config.assert_called_once()
        tabs.set_value.assert_called_once_with(setup_tab)
        load_tab_fn.assert_called_once_with(setup_tab)
        mock_dialog.close.assert_called_once()


def test_show_config_onboarding_dialog_demo_flow():
    callbacks = MagicMock()
    callbacks.get_target_config_file.return_value = "config/custom/config.ini"
    callbacks.copy_default_config.return_value = True

    tabs = MagicMock()
    setup_tab = MagicMock()

    with (patch("gui.dialogs.config_onboarding_dialog.ui") as mock_ui,):
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_dialog.props.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_cards = []

        def make_card(*args, **kwargs):
            card = MagicMock()
            card.__enter__.return_value = card
            card.classes.return_value = card
            mock_cards.append(card)
            return card

        mock_ui.card.side_effect = make_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        mock_icon = MagicMock()
        mock_icon.classes.return_value = mock_icon
        mock_ui.icon.return_value = mock_icon

        mock_lbl = MagicMock()
        mock_lbl.classes.return_value = mock_lbl
        mock_ui.label.return_value = mock_lbl

        show_config_onboarding_dialog(
            callbacks=callbacks,
            tabs=tabs,
            setup_tab=setup_tab,
        )

        # mock_cards[0] is dialog card, [1] is wizard card, [2] is demo card
        assert len(mock_cards) >= 3
        wizard_card = mock_cards[1]
        demo_card = mock_cards[2]

        # Simulate clicking demo card
        demo_click_fn = demo_card.on.call_args[0][1]
        demo_click_fn()

        # Verify demo card received active classes and wizard card received inactive classes
        demo_card.classes.assert_called()
        wizard_card.classes.assert_called()

        # Find Continue button on_click callback
        button_calls = mock_ui.button.call_args_list
        continue_click = button_calls[0].kwargs.get("on_click")
        assert continue_click is not None

        # Execute Continue callback
        asyncio.run(continue_click())

        callbacks.copy_default_config.assert_called_once()
        callbacks.use_config.assert_called_once()
        mock_ui.run_javascript.assert_called_once()
        mock_dialog.close.assert_called_once()
