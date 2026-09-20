"""Unit tests for FrameService in src/storage/frame_service.py."""

from datetime import datetime
from unittest.mock import MagicMock

import cv2
import numpy as np

from storage.base import MeterReading, ReadingRecord
from storage.frame_service import FrameService


def test_frame_service_timeline_and_empty_storage():
    service_none = FrameService(storage=None)
    assert service_none.get_timeline() == []
    assert service_none.get_frame_data_uri(1) is None
    assert service_none.get_frame_diff(1).error != ""
    assert service_none.get_frame_diff_data_uri(1) is None

    mock_storage = MagicMock()
    mock_record = ReadingRecord(
        id=42,
        timestamp=datetime(2026, 5, 1, 10, 30, 0),
        meters={"total": MeterReading(value=500.25)},
        digital_results={"total": "500"},
        analog_results={},
        error="",
        frame_type="scheduled",
        frame_path=None,
        flow_detected=False,
        confidence_scores={"total": 0.98},
    )
    mock_storage.get_timeline.return_value = [mock_record]
    mock_storage.get_frame_bytes.return_value = (b"fake_bytes", "image/jpeg")

    # Test with callable storage getter
    service = FrameService(storage=lambda: mock_storage)
    timeline = service.get_timeline(
        limit=5, offset=0, anomalies_only=False, frames_only=False
    )
    assert len(timeline) == 1
    assert timeline[0].id == 42
    assert timeline[0].has_frame is True
    assert timeline[0].timestamp == "2026-05-01T10:30:00"
    assert timeline[0].meters["total"]["value"] == 500.25


def test_frame_service_frame_data_uri_encodings():
    mock_storage = MagicMock()
    service = FrameService(storage=mock_storage)

    # 1. Standard JPEG
    mock_storage.get_frame_bytes.return_value = (b"\xff\xd8\xff\xe0data", "image/jpeg")
    uri = service.get_frame_data_uri(10)
    assert uri is not None
    assert uri.startswith("data:image/jpeg;base64,")

    # 2. WebP detection fallback
    mock_storage.get_frame_bytes.return_value = (b"RIFF\x00\x00\x00\x00WEBP", None)
    uri_webp = service.get_frame_data_uri(11)
    assert uri_webp is not None
    assert uri_webp.startswith("data:image/webp;base64,")

    # 3. Missing frame data
    mock_storage.get_frame_bytes.return_value = (None, None)
    assert service.get_frame_data_uri(12) is None


def test_frame_service_diff_and_heatmaps():
    img1 = np.zeros((40, 40, 3), dtype=np.uint8)
    img2 = np.ones((40, 40, 3), dtype=np.uint8) * 128
    _, b1 = cv2.imencode(".jpg", img1)
    _, b2 = cv2.imencode(".jpg", img2)
    bytes1 = b1.tobytes()
    bytes2 = b2.tobytes()

    mock_storage = MagicMock()
    mock_storage.get_frame_bytes.side_effect = lambda rid: (
        (bytes1, "image/jpeg")
        if rid == 1
        else ((bytes2, "image/jpeg") if rid == 2 else (None, None))
    )

    service = FrameService(storage=mock_storage)

    # Self comparison
    diff_self = service.get_frame_diff(1, compare_id=None)
    assert diff_self.ssim_similarity == 1.0
    assert diff_self.is_anomaly is False
    assert diff_self.reading_id == 1

    # Cross comparison
    diff_cross = service.get_frame_diff(1, compare_id=2)
    assert diff_cross.ssim_similarity is not None
    assert diff_cross.compare_id == 2

    # Heatmap data URI
    diff_uri = service.get_frame_diff_data_uri(1, compare_id=2)
    assert diff_uri is not None
    assert diff_uri.startswith("data:image/jpeg;base64,")

    # Non-existent reading
    diff_err = service.get_frame_diff(999)
    assert diff_err.error != ""
    assert service.get_frame_diff_data_uri(999) is None

    # Corrupted image bytes
    mock_storage.get_frame_bytes.side_effect = lambda rid: (
        b"corrupted_bytes",
        "image/jpeg",
    )
    diff_corrupt = service.get_frame_diff(1, compare_id=2)
    assert diff_corrupt.error != ""
    assert service.get_frame_diff_data_uri(1, compare_id=2) is None
