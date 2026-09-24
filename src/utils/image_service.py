"""Service helpers for image caching, extraction, and base64 retrieval."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import utils.image
from processor.image import ImageProcessor

if TYPE_CHECKING:
    from configuration import Config
    from utils.cache import ImageCache


def get_cached_image_base64(
    cache: ImageCache | None,
    image_name: str,
    config: Config | None = None,
) -> str | None:
    """Retrieve an image from cache as base64 string, generating ROI overlay on demand if needed."""
    if cache is None:
        return None
    img = cache.get(image_name)
    if img is not None:
        return utils.image.convert_image_base64str(img)

    if image_name == "roi":
        with contextlib.suppress(Exception):
            source_img = cache.get("final")
            if source_img is None:
                source_img = cache.get("aligned")
            if source_img is not None and config is not None:
                proc = (
                    ImageProcessor()
                    .set_image(source_img.copy())
                    .draw_meter_rois(config)
                )
                return proc.get_image_as_base64_str()
    return None
