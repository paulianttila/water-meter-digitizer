"""Computer Vision morphology minus sign (-) detector for digital LCD counters.

Detects horizontal minus sign strokes on LCD meters indicating negative consumption/flow.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)


def detect_minus_sign(
    image: PILImage | np.ndarray,
    min_confidence: float = 60.0,
) -> tuple[bool, float]:
    """Detect whether a digital digit crop contains a horizontal minus sign ('-').

    Uses adaptive contrast, binarization, morphological horizontal filtering,
    and geometric contour heuristics (aspect ratio, vertical centrality, width fraction).

    Args:
        image: PIL Image or numpy array (RGB or Grayscale).
        min_confidence: Minimum confidence threshold to return True.

    Returns:
        tuple[bool, float]: (is_minus_detected, confidence_percentage)
    """
    img_np = np.array(image) if isinstance(image, Image.Image) else np.copy(image)

    if img_np.size == 0:
        return False, 0.0

    # Convert to grayscale if needed
    if len(img_np.shape) == 3:
        if img_np.shape[2] == 4:  # RGBA
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
        else:  # RGB
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    h_img, w_img = img_np.shape[:2]
    if h_img < 5 or w_img < 5:
        return False, 0.0

    # Apply CLAHE to normalize uneven LCD backlighting/shadows
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    img_enhanced = clahe.apply(img_np)

    best_conf = 0.0
    candidates_info: list[str] = []

    # Test both polarities: dark foreground on light background and light on dark
    for invert in (False, True):
        gray = 255 - img_enhanced if invert else img_enhanced
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Generate thresholded binary images using multiple methods
        thresh_list: list[np.ndarray] = []

        # 1. Otsu thresholding
        _, thresh_otsu = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        thresh_list.append(thresh_otsu)

        # 2. Adaptive Gaussian thresholding (robust against non-uniform backlight/shadows)
        block_size = max(5, (min(w_img, h_img) // 2) * 2 + 1)
        if block_size >= 3:
            thresh_adapt = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                block_size,
                3,
            )
            thresh_list.append(thresh_adapt)

        for thresh in thresh_list:
            total_fg = int(np.count_nonzero(thresh))
            total_pixels = w_img * h_img
            if total_fg == 0 or total_fg > int(0.75 * total_pixels):
                continue

            # Horizontal morphological opening to isolate horizontal bar
            kernel_w = max(2, int(w_img * 0.12))
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
            morphed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

            # Find contours of horizontal strokes
            contours, _ = cv2.findContours(
                morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for cnt in contours:
                _x, y, w, h = cv2.boundingRect(cnt)
                if w < 2 or h < 1:
                    continue

                mask_cnt = np.zeros_like(thresh)
                cv2.drawContours(mask_cnt, [cnt], -1, 255, -1)
                cnt_fg = int(np.count_nonzero(mask_cnt))

                isolation_ratio = float(cnt_fg) / float(max(1, total_fg))
                aspect_ratio = float(w) / float(max(1, h))
                width_ratio = float(w) / float(w_img)
                height_ratio = float(h) / float(h_img)
                cy = y + h / 2.0
                cy_ratio = cy / float(h_img)

                cand_desc = (
                    f"w={w}, h={h}, ar={aspect_ratio:.2f}, w_ratio={width_ratio:.2f}, "
                    f"h_ratio={height_ratio:.2f}, cy_ratio={cy_ratio:.2f}, iso={isolation_ratio:.2f}"
                )
                candidates_info.append(cand_desc)

                # Heuristics for an LCD minus sign '-':
                # 1. Aspect ratio: distinctly horizontal bar (w/h >= 1.5)
                # 2. Vertical position: centered within middle band (0.28 <= cy_ratio <= 0.72)
                # 3. Relative width: covers noticeable portion of digit slot (0.15 <= w/w_img <= 0.95)
                # 4. Height ratio: thin stroke (h/h_img <= 0.28)
                # 5. Isolation ratio: prominent stroke (isolation >= 0.15)
                if (
                    aspect_ratio >= 1.5
                    and 0.15 <= width_ratio <= 0.95
                    and height_ratio <= 0.28
                    and 0.28 <= cy_ratio <= 0.72
                    and isolation_ratio >= 0.15
                ):
                    aspect_score = min(100.0, (aspect_ratio / 2.2) * 85.0)
                    center_dist = abs(cy_ratio - 0.5)  # 0.0 is perfect center
                    center_score = max(0.0, 100.0 - (center_dist * 250.0))
                    width_score = min(100.0, (width_ratio / 0.35) * 90.0)
                    isolation_score = min(100.0, (isolation_ratio / 0.40) * 100.0)

                    conf = (
                        (aspect_score * 0.35)
                        + (center_score * 0.30)
                        + (width_score * 0.20)
                        + (isolation_score * 0.15)
                    )
                    conf = round(min(100.0, max(0.0, conf)), 1)
                    if conf > best_conf:
                        best_conf = conf

    is_detected = best_conf >= min_confidence
    logger.info(
        f"detect_minus_sign ({w_img}x{h_img}): detected={is_detected}, "
        f"conf={best_conf:.1f}% (threshold={min_confidence:.1f}%). "
        f"Candidates: {candidates_info[:5]}"
    )
    return is_detected, best_conf
