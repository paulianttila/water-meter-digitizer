from unittest.mock import MagicMock, patch

import pytest
import requests

from utils.download import DownloadFailure, _download_http_stream, load_file_from_url


def test_download_http_stream_success():
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.get", return_value=mock_resp) as mock_get:
        data = _download_http_stream("http://camera.local/stream", timeout=5.0)
        assert data == b"chunk1chunk2chunk3"
        mock_get.assert_called_once_with(
            "http://camera.local/stream",
            timeout=(5.0, 5.0),
            stream=True,
        )


def test_download_http_stream_wall_clock_timeout():
    mock_resp = MagicMock()

    # Generator simulating a slow trickle that exceeds wall-clock timeout
    def slow_generator():
        yield b"chunk1"
        # Simulate time jump exceeding timeout
        with patch("time.monotonic", side_effect=[10.0, 20.0]):
            yield b"chunk2"

    # We can control monotonic time directly
    # Call 1: start_time = 0.0
    # Inside loop: chunk 1 check: monotonic() = 1.0 (elapsed 1.0 <= 2.0)
    # Inside loop: chunk 2 check: monotonic() = 3.0 (elapsed 3.0 > 2.0 -> raises)
    monotonic_timeline = [0.0, 1.0, 3.0]

    mock_resp.iter_content.return_value = [b"a" * 100, b"b" * 100]
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch("requests.get", return_value=mock_resp),
        patch("time.monotonic", side_effect=monotonic_timeline),
    ):
        with pytest.raises(DownloadFailure) as exc_info:
            _download_http_stream("http://camera.local/trickle", timeout=2.0)

        assert "Download exceeded wall-clock timeout of 2.0s" in str(exc_info.value)


def test_download_http_stream_request_timeout():
    with patch(
        "requests.get", side_effect=requests.exceptions.ReadTimeout("Read timed out")
    ):
        with pytest.raises(DownloadFailure) as exc_info:
            _download_http_stream("http://camera.local/snap", timeout=3.0)

        assert "Download timed out after 3.0s" in str(exc_info.value)


def test_download_http_stream_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Server Error"
    )
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(DownloadFailure) as exc_info:
            _download_http_stream("http://camera.local/snap", timeout=3.0)

        assert "HTTP request error" in str(exc_info.value)


def test_load_file_from_url_min_size():
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"tiny"]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(DownloadFailure) as exc_info:
            load_file_from_url("http://camera.local/snap", timeout=5, min_file_size=100)

        assert "File too small" in str(exc_info.value)


def test_load_file_from_url_file_uri(tmp_path):
    safe_file = tmp_path / "camera.jpg"
    safe_file.write_bytes(b"image_bytes_12345")

    # Safe access
    data = load_file_from_url(
        f"file://{safe_file}",
        timeout=5,
        allowed_directories=[str(tmp_path)],
    )
    assert data == b"image_bytes_12345"

    # Denied access
    with pytest.raises(DownloadFailure) as exc_info:
        load_file_from_url(
            f"file://{safe_file}",
            timeout=5,
            allowed_directories=["/other/path"],
        )
    assert "denied" in str(exc_info.value).lower()


def test_load_file_from_url_mock_camera():
    with patch(
        "api.routes_mock_camera.render_mock_camera_from_url",
        return_value=b"mock_frame_data",
    ) as mock_render:
        data = load_file_from_url("mock://meter", timeout=5)
        assert data == b"mock_frame_data"
        mock_render.assert_called_once_with("mock://meter")
