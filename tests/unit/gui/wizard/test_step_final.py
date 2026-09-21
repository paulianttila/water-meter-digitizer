"""Unit tests for finalization and configuration save step in Setup Wizard."""

from unittest.mock import MagicMock, patch

from configuration import Config
from gui.wizard.steps.final import FinalStep


def test_final_step_set_config():
    callbacks = MagicMock()
    save_refs_func = MagicMock()
    step = FinalStep(
        name="Final",
        callbacks=callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=save_refs_func,
    )
    step.editor = MagicMock(value="")

    config = Config()
    config.image_source.url = "http://localhost/image.jpg"
    step.set_config(config)

    assert step.editor.value == config.save_to_string()
    assert step.txt == step.editor.value


def test_final_step_syntax_check():
    callbacks = MagicMock()
    save_refs_func = MagicMock()
    step = FinalStep(
        name="Final",
        callbacks=callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=save_refs_func,
    )

    # Valid syntax
    config = Config()
    step.editor = MagicMock(value=config.save_to_string())
    with patch("gui.wizard.steps.final.ui.notify") as mock_notify:
        assert step._syntax_check() is True
        mock_notify.assert_called_with("Syntax is correct", type="positive")

    # Invalid syntax
    step.editor = MagicMock(value="invalid [ini format ::::")
    with patch("gui.wizard.steps.final.ui.notify") as mock_notify:
        assert step._syntax_check() is False
        mock_notify.assert_called_once()
        assert "Syntax error" in mock_notify.call_args[0][0]


def test_final_step_show_config():
    callbacks = MagicMock()
    save_refs_func = MagicMock()
    step = FinalStep(
        name="Final",
        callbacks=callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=save_refs_func,
    )

    # Valid config JSON preview
    config = Config()
    step.editor = MagicMock(value=config.save_to_string())
    with patch("gui.wizard.steps.final.open_code_inspect_dialog") as mock_inspect:
        step._show_config()
        assert mock_inspect.called
        kwargs = mock_inspect.call_args.kwargs
        assert kwargs.get("title") == "Compiled Config (JSON)"
        assert '"image_source"' in kwargs.get("code_content", "")

    # Invalid config error handling
    step.editor = MagicMock(value="invalid [ini format ::::")
    with patch("gui.wizard.steps.final.ui.notify") as mock_notify:
        step._show_config()
        mock_notify.assert_called_once()
        assert "Syntax error" in mock_notify.call_args[0][0]


def test_final_step_save_and_use_config():
    callbacks = MagicMock()
    save_refs_func = MagicMock()
    step = FinalStep(
        name="Final",
        callbacks=callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=save_refs_func,
    )

    config = Config()
    step.editor = MagicMock(value=config.save_to_string())

    with patch("gui.wizard.steps.final.ui.notify"):
        step._save_config()
        assert save_refs_func.called
        callbacks.save_config_file.assert_called_once_with(step.editor.value)
        assert step.new_config_saved is True

        step._use_config()
        callbacks.use_config.assert_called_once()
        assert step.new_config_saved is False


def test_final_step_prompt_hot_reload():
    callbacks = MagicMock()
    save_refs_func = MagicMock()
    step = FinalStep(
        name="Final",
        callbacks=callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=save_refs_func,
    )
    with (
        patch("gui.wizard.steps.final.ui.dialog") as mock_dialog,
        patch("gui.wizard.steps.final.ui.card"),
        patch("gui.wizard.steps.final.ui.row"),
        patch("gui.wizard.steps.final.ui.element"),
        patch("gui.wizard.steps.final.ui.icon"),
        patch("gui.wizard.steps.final.ui.column"),
        patch("gui.wizard.steps.final.ui.label"),
        patch("gui.wizard.steps.final.ui.button"),
    ):
        dialog_inst = MagicMock()
        mock_dialog.return_value.__enter__.return_value = dialog_inst

        step._prompt_hot_reload()
        assert dialog_inst.open.called
