"""Unit tests for DownloadImageStep and FinalStep in src/gui/."""

import asyncio
from unittest.mock import MagicMock, patch

from callbacks import Callbacks
from configuration import Config, ImageSource
from gui.step_download import DownloadImageStep
from gui.step_final import FinalStep


def test_step_download_load_and_actions():
    set_img = MagicMock()
    err_cb = MagicMock()
    step = DownloadImageStep(
        name="Download",
        set_image_callback=set_img,
        on_error_callback=err_cb,
    )

    # load_from_config before UI elements initialized
    src = ImageSource(url="http://test.local/img.jpg", timeout=12, min_size=5000)
    step.load_from_config(src)

    # Initialize mock UI fields
    step.url = MagicMock(value="http://test.local/img.jpg")
    step.timeout = MagicMock(value=12)
    step.minsize = MagicMock(value=5000)

    # load_from_config after UI elements initialized
    src2 = ImageSource(url="http://new.local/img.jpg", timeout=20, min_size=8000)
    step.load_from_config(src2)
    assert step.url.value == "http://new.local/img.jpg"
    assert step.timeout.value == 20
    assert step.minsize.value == 8000

    # Download with empty url
    step.url.value = ""
    res = asyncio.run(step.download())
    assert res is False

    # Download success
    step.url.value = "http://valid.url/img.jpg"
    with patch("processor.image.ImageProcessor.download_image") as mock_dl:
        mock_dl.return_value.get_image_as_base64_str.return_value = "b64str"
        res = asyncio.run(step.download())
        assert res is True
        set_img.assert_called_with("b64str")

    # Download error
    with patch(
        "processor.image.ImageProcessor.download_image",
        side_effect=RuntimeError("Net error"),
    ):
        res = asyncio.run(step.download())
        assert res is False
        err_cb.assert_called_with("Net error")


def test_step_download_show():
    set_img = MagicMock()
    step = DownloadImageStep("Download", set_image_callback=set_img)

    with patch("gui.step_download.ui") as mock_ui, patch("gui.step_base.ui"):
        mock_stepper = MagicMock()
        asyncio.run(step.show(mock_stepper, first_step=True, last_step=False))
        mock_ui.step.assert_called_once_with("Download")


def test_step_final_actions():
    mock_callbacks = MagicMock(spec=Callbacks)
    set_img = MagicMock()
    save_refs = MagicMock()

    step = FinalStep(
        name="Final",
        callbacks=mock_callbacks,
        set_image_callback=set_img,
        save_refs_func=save_refs,
    )
    step.editor = MagicMock(value="[DEFAULT]\nLogLevel=DEBUG\n")

    # set_config
    cfg = Config()
    step.set_config(cfg)
    assert step.txt == step.editor.value

    # syntax check success
    assert step._syntax_check() is True

    # save config
    step._save_config()
    assert step.new_config_saved is True
    save_refs.assert_called_once()
    mock_callbacks.save_config_file.assert_called_once()

    # use config
    step._use_config()
    assert step.new_config_saved is False
    mock_callbacks.use_config.assert_called_once()

    # syntax error
    step.editor.value = "invalid ini [[["
    assert step._syntax_check() is False


def test_step_final_show_and_json_preview():
    mock_callbacks = MagicMock(spec=Callbacks)
    step = FinalStep(
        name="Final",
        callbacks=mock_callbacks,
        set_image_callback=MagicMock(),
        save_refs_func=MagicMock(),
    )

    with patch("gui.step_final.ui") as mock_ui, patch("gui.step_base.ui"):
        mock_dialog = MagicMock()
        mock_ui.dialog.return_value.__enter__.return_value = mock_dialog

        asyncio.run(step.show(MagicMock(), first_step=False, last_step=True))
        mock_ui.step.assert_called_once_with("Final")

        # Show JSON config dialog
        step.editor.value = "[DEFAULT]\n"
        step._show_config()
        mock_dialog.open.assert_called_once()

        # Show config with syntax error
        step.editor.value = "invalid ini [[["
        step._show_config()
        mock_ui.notify.assert_called()
