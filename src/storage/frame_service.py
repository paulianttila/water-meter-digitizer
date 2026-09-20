"""Service for frame retrieval, comparison, and diff visualization."""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np

from utils.visual_diff import (
    calculate_image_ssim,
    compress_image_to_bytes,
    generate_difference_heatmap,
)

if TYPE_CHECKING:
    from storage.base import StorageBackend

logger = logging.getLogger(__name__)


class FrameService:
    """Service for frame retrieval, comparison, and diff visualization."""

    def __init__(
        self,
        storage: StorageBackend | Callable[[], StorageBackend | None] | None = None,
    ) -> None:
        self._storage = storage

    def _get_storage(self) -> StorageBackend | None:
        if self._storage is None:
            return None
        if hasattr(self._storage, "get_timeline") or hasattr(
            self._storage, "get_frame_bytes"
        ):
            return self._storage
        if callable(self._storage):
            return self._storage()
        return self._storage

    def get_timeline(
        self,
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        frames_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve timeline records as serialized dictionary objects."""
        storage = self._get_storage()
        if storage is None:
            logger.warning("FrameService.get_timeline: storage backend is None")
            return []
        records = storage.get_timeline(
            limit=limit,
            offset=offset,
            anomalies_only=anomalies_only,
            frames_only=frames_only,
        )
        logger.debug(
            "FrameService.get_timeline: retrieved %d records (limit=%s, offset=%s, anomalies_only=%s, frames_only=%s)",
            len(records),
            limit,
            offset,
            anomalies_only,
            frames_only,
        )
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "meters": {k: v.model_dump() for k, v in r.meters.items()},
                "digital_results": r.digital_results,
                "analog_results": r.analog_results,
                "error": r.error,
                "frame_type": r.frame_type,
                "has_frame": bool(
                    r.frame_type
                    or r.frame_path
                    or (
                        r.id is not None
                        and storage.get_frame_bytes(r.id)[0] is not None
                    )
                ),
                "flow_detected": r.flow_detected,
                "confidence_scores": r.confidence_scores,
            }
            for r in records
        ]

    def get_frame_data_uri(self, reading_id: int) -> str | None:
        """Retrieve stored frame bytes and encode as a Base64 data URI."""
        logger.debug(
            "FrameService.get_frame_data_uri requested for reading_id=%s", reading_id
        )
        storage = self._get_storage()
        if storage is None:
            logger.debug(
                "FrameService.get_frame_data_uri: storage is None for reading_id=%s",
                reading_id,
            )
            return None
        data, mime = storage.get_frame_bytes(reading_id)
        if not data:
            logger.debug(
                "FrameService.get_frame_data_uri: storage returned no frame data for reading_id=%s",
                reading_id,
            )
            return None

        b64 = base64.b64encode(data).decode("ascii")
        mime_type = mime or ("image/webp" if data.startswith(b"RIFF") else "image/jpeg")
        logger.debug(
            "FrameService.get_frame_data_uri: successfully generated data URI for reading_id=%s (%d raw bytes, mime=%s, b64_len=%d)",
            reading_id,
            len(data),
            mime_type,
            len(b64),
        )
        return f"data:{mime_type};base64,{b64}"

    def get_frame_diff(
        self, reading_id: int, compare_id: int | None = None
    ) -> dict[str, Any]:
        """Compute SSIM similarity between two frames."""
        storage = self._get_storage()
        if storage is None:
            return {"error": "Storage not available"}
        cur_bytes, _ = storage.get_frame_bytes(reading_id)
        if not cur_bytes:
            return {"error": "Frame not found"}
        comp_bytes = None
        if compare_id is not None:
            comp_bytes, _ = storage.get_frame_bytes(compare_id)
        if not comp_bytes:
            comp_bytes = cur_bytes

        cur_img = cv2.imdecode(np.frombuffer(cur_bytes, np.uint8), cv2.IMREAD_COLOR)
        comp_img = cv2.imdecode(np.frombuffer(comp_bytes, np.uint8), cv2.IMREAD_COLOR)
        if cur_img is None or comp_img is None:
            return {"error": "Failed decoding images"}

        ssim_score = calculate_image_ssim(cur_img, comp_img)
        return {
            "reading_id": reading_id,
            "compare_id": compare_id,
            "ssim_similarity": ssim_score,
            "is_anomaly": ssim_score < 0.85,
            "diff_image_url": f"/history/frame/{reading_id}/diff_image?compare_id={compare_id or reading_id}",
        }

    def get_frame_diff_data_uri(
        self, reading_id: int, compare_id: int | None = None
    ) -> str | None:
        """Compute diff heatmap between two frames and return as JPEG data URI."""
        logger.debug(
            "FrameService.get_frame_diff_data_uri: reading_id=%s, compare_id=%s",
            reading_id,
            compare_id,
        )
        storage = self._get_storage()
        if storage is None:
            return None
        cur_bytes, _ = storage.get_frame_bytes(reading_id)
        if not cur_bytes:
            return None
        comp_bytes = None
        if compare_id is not None and compare_id != reading_id:
            comp_bytes, _ = storage.get_frame_bytes(compare_id)
        if not comp_bytes:
            comp_bytes = cur_bytes

        cur_img = cv2.imdecode(np.frombuffer(cur_bytes, np.uint8), cv2.IMREAD_COLOR)
        comp_img = cv2.imdecode(np.frombuffer(comp_bytes, np.uint8), cv2.IMREAD_COLOR)
        if cur_img is None or comp_img is None:
            return None

        heatmap = generate_difference_heatmap(cur_img, comp_img)
        diff_bytes = compress_image_to_bytes(heatmap, format_type="jpeg", quality=80)
        b64 = base64.b64encode(diff_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
