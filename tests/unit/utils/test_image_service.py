"""Unit tests for utils.image_service."""

from unittest.mock import MagicMock, patch

import numpy as np

from utils.image_service import get_cached_image_base64


def test_get_cached_image_base64_none_cache():
    assert get_cached_image_base64(None, "final") is None


def test_get_cached_image_base64_found_in_cache():
    mock_cache = MagicMock()
    mock_img = np.zeros((10, 10, 3), dtype=np.uint8)
    mock_cache.get.return_value = mock_img

    with patch("utils.image.convert_image_base64str", return_value="b64_data"):
        result = get_cached_image_base64(mock_cache, "final")
        assert result == "b64_data"
        mock_cache.get.assert_called_once_with("final")


def test_get_cached_image_base64_not_found():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    result = get_cached_image_base64(mock_cache, "missing")
    assert result is None


def test_get_cached_image_base64_roi_fallback():
    mock_cache = MagicMock()
    mock_img = np.zeros((10, 10, 3), dtype=np.uint8)
    # First get("roi") is None, next get("final") returns mock_img
    mock_cache.get.side_effect = [None, mock_img]

    mock_config = MagicMock()
    with patch("utils.image_service.ImageProcessor") as MockProcessor:
        mock_proc_inst = MockProcessor.return_value
        mock_proc_inst.set_image.return_value = mock_proc_inst
        mock_proc_inst.draw_meter_rois.return_value = mock_proc_inst
        mock_proc_inst.get_image_as_base64_str.return_value = "roi_b64"

        result = get_cached_image_base64(mock_cache, "roi", mock_config)
        assert result == "roi_b64"
        mock_proc_inst.set_image.assert_called_once()
        mock_proc_inst.draw_meter_rois.assert_called_once_with(mock_config)


def test_get_cached_image_base64_roi_exception_suppression():
    mock_cache = MagicMock()
    mock_img = np.zeros((10, 10, 3), dtype=np.uint8)
    mock_cache.get.side_effect = [None, mock_img]

    mock_config = MagicMock()
    with patch("utils.image_service.ImageProcessor") as MockProcessor:
        mock_proc_inst = MockProcessor.return_value
        mock_proc_inst.set_image.side_effect = RuntimeError("Processing error")

        result = get_cached_image_base64(mock_cache, "roi", mock_config)
        assert result is None
