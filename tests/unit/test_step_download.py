import asyncio
from unittest.mock import MagicMock, patch
from configuration import ImageSource
from gui.step_download import DownloadImageStep


def test_download_image_step_empty_url():
    step = DownloadImageStep(name="Download", set_image_callback=MagicMock())
    step.url = MagicMock()
    step.url.value = ""
    step.timeout = MagicMock()
    step.timeout.value = 10

    result = asyncio.run(step.download())
    assert result is False


def test_download_image_step_error_calls_callback():
    error_cb = MagicMock()
    step = DownloadImageStep(
        name="Download",
        set_image_callback=MagicMock(),
        on_error_callback=error_cb,
    )
    step.url = MagicMock()
    step.url.value = "http://unreachable-camera.local/image.jpg"
    step.timeout = MagicMock()
    step.timeout.value = 5

    with patch("gui.step_download.ImageProcessor") as mock_ip_cls:
        mock_ip = MagicMock()
        mock_ip.download_image.side_effect = TimeoutError("Connection timed out")
        mock_ip_cls.return_value = mock_ip

        result = asyncio.run(step.download())

        assert result is False
        error_cb.assert_called_once()
        assert "Connection timed out" in error_cb.call_args[0][0]


def test_download_image_step_success():
    set_img_cb = MagicMock()
    step = DownloadImageStep(
        name="Download",
        set_image_callback=set_img_cb,
    )
    step.url = MagicMock()
    step.url.value = "http://camera.local/image.jpg"
    step.timeout = MagicMock()
    step.timeout.value = 10

    with patch("gui.step_download.ImageProcessor") as mock_ip_cls:
        mock_ip = MagicMock()
        mock_ip.download_image.return_value = mock_ip
        mock_ip.get_image_as_base64_str.return_value = "base64_sample_data"
        mock_ip_cls.return_value = mock_ip

        result = asyncio.run(step.download())

        assert result is True
        set_img_cb.assert_called_once_with("base64_sample_data")


def test_download_image_step_load_from_config():
    step = DownloadImageStep(name="Download", set_image_callback=MagicMock())
    step.url = MagicMock()
    step.timeout = MagicMock()

    config_source = ImageSource()
    config_source.url = "http://192.168.1.100/jpg"
    config_source.timeout = 15

    step.load_from_config(config_source)
    assert step.url.value == "http://192.168.1.100/jpg"
    assert step.timeout.value == 15
