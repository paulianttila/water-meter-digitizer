import base64
import io
import logging
from collections.abc import Sequence
from PIL.Image import Image
import PIL.Image
import PIL.ImageEnhance
from PIL import ImageOps, ImageDraw, ImageFont
import numpy as np
import cv2

from data_classes import ImagePosition, RefImage

logger = logging.getLogger(__name__)


def save_image(image: Image, file_name: str) -> None:
    if image is None:
        raise ValueError("No image to save")
    if isinstance(image, Image):
        Image.save(image, file_name, "JPEG")
    elif isinstance(image, np.ndarray):
        cv2.imwrite(file_name, image)


def load_image_from_file(file_name: str) -> Image:
    return PIL.Image.open(file_name)


def bytes_to_image(data: bytes) -> Image:
    image = PIL.Image.open(io.BytesIO(data))
    if image.format not in ["JPEG", "PNG"]:
        raise ValueError("Invalid image format")
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def convert_image_base64str(image: Image) -> str:
    data = convert_image_to_bytes(image)
    return base64.b64encode(data).decode("utf-8")


def convert_image_to_bytes(image: Image) -> bytes:
    if image is None:
        raise ValueError("No image to convert")
    if isinstance(image, Image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return buffered.getvalue()
    elif isinstance(image, np.ndarray):
        is_success, im_buf_arr = cv2.imencode(".jpg", image)
        return im_buf_arr.tobytes()
    else:
        raise ValueError("Invalid image")


def convert_base64_str_to_image(data: str) -> Image:
    if data is None:
        raise ValueError("No image to convert")

    return bytes_to_image(base64.b64decode(data))


def convert_to_image(image: Image) -> Image:
    if isinstance(image, Image):
        return image
    elif isinstance(image, np.ndarray):
        return Image.fromarray(image)
    else:
        raise ValueError("Invalid image")


def convert_image_to_np_array(image: Image) -> np.ndarray:
    if isinstance(image, Image):
        return np.array(image)
    elif isinstance(image, np.ndarray):
        return image
    else:
        raise ValueError("Invalid image")


def convert_np_array_to_image(data: np.ndarray) -> Image:
    if isinstance(data, np.ndarray):
        return PIL.Image.fromarray(data)
    elif isinstance(data, Image):
        return data
    else:
        raise ValueError("Invalid image")


def image_size(image: Image) -> tuple:
    if image is None:
        raise ValueError("No image for size check")
    return image.size


def image_size_from_file(file_name: str) -> tuple:
    image = PIL.Image.open(file_name)
    return image.size


def rotate(image: Image, angle: float, keep_org_size: bool = True) -> Image:
    if image is None:
        raise ValueError("No image to rotate")

    expand = not keep_org_size
    return image.rotate(angle, expand=expand)


def _get_feature_detector(name: str):
    name = (name or "orb").lower()
    if name == "akaze":
        return cv2.AKAZE_create(threshold=0.0005), cv2.NORM_HAMMING
    elif name == "sift":
        return cv2.SIFT_create(), cv2.NORM_L2
    else:  # default "orb"
        return (
            cv2.ORB_create(
                nfeatures=2000,
                scaleFactor=1.2,
                nlevels=8,
                edgeThreshold=5,
                patchSize=15,
                fastThreshold=5,
            ),
            cv2.NORM_HAMMING,
        )


def _match_features_coordinate(
    image: np.ndarray,
    template: np.ndarray,
    detector_name: str = "orb",
) -> tuple[tuple[int, int] | None, float]:
    """Find template coordinates in image using feature keypoints (ORB/AKAZE/SIFT)."""
    try:
        gray_img = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )
        gray_tpl = (
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3
            else template
        )

        detector, norm_type = _get_feature_detector(detector_name)
        kp_tpl, des_tpl = detector.detectAndCompute(gray_tpl, None)
        kp_img, des_img = detector.detectAndCompute(gray_img, None)

        if des_tpl is None or des_img is None or len(kp_tpl) < 3 or len(kp_img) < 3:
            return None, 0.0

        matcher = cv2.BFMatcher(norm_type, crossCheck=True)
        matches = matcher.match(des_tpl, des_img)
        matches = sorted(matches, key=lambda x: x.distance)

        if len(matches) < 3:
            return None, 0.0

        src_pts = np.float32([kp_tpl[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_img[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        # Estimate partial affine (translation, rotation, scale)
        if len(matches) >= 4:
            M, inliers = cv2.estimateAffinePartial2D(
                src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0
            )
            if M is not None and inliers is not None and np.sum(inliers) >= 3:
                top_left = cv2.transform(np.array([[[0.0, 0.0]]], dtype=np.float32), M)[
                    0
                ][0]
                tx = int(round(top_left[0]))
                ty = int(round(top_left[1]))
                confidence = float(min(1.0, np.sum(inliers) / max(len(kp_tpl), 6)))
                return (tx, ty), confidence

        # Fallback to median shift
        dx = float(np.median(dst_pts[:, 0, 0] - src_pts[:, 0, 0]))
        dy = float(np.median(dst_pts[:, 0, 1] - src_pts[:, 0, 1]))
        conf = float(min(1.0, len(matches) / max(len(kp_tpl), 6)))
        return (int(round(dx)), int(round(dy))), conf
    except Exception as e:
        logger.debug(f"Feature matching error: {e}")
        return None, 0.0


def _get_ref_coordinate(
    image: np.ndarray,
    template: np.ndarray,
    method: str = "hybrid",
    min_match_score: float = 0.70,
    feature_detector: str = "orb",
) -> tuple[int, int]:
    """Find reference template coordinate in image using template/feature matching."""
    if template is None or image is None:
        raise ValueError("Invalid image or template for coordinate detection")

    method_lower = (method or "hybrid").lower()
    tpl_point: tuple[int, int] | None = None
    tpl_score: float = 0.0

    # 1. Try template matching if method is 'template' or 'hybrid'
    if method_lower in ("template", "hybrid"):
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        tpl_point = (int(max_loc[0]), int(max_loc[1]))
        tpl_score = float(max_val)

        if method_lower == "template" or tpl_score >= min_match_score:
            logger.debug(
                f"Template match succeeded with score {tpl_score:.3f} at {tpl_point}"
            )
            return tpl_point

        logger.debug(
            f"Template match score {tpl_score:.3f} < {min_match_score:.3f}. "
            "Attempting feature matching fallback."
        )

    # 2. Try feature matching (ORB/AKAZE/SIFT)
    detector = (
        method_lower if method_lower in ("orb", "akaze", "sift") else feature_detector
    )
    feat_point, feat_score = _match_features_coordinate(
        image, template, detector_name=detector
    )
    if feat_point is not None and feat_score > 0.15:
        logger.debug(
            f"Feature match ({detector}) succeeded with confidence "
            f"{feat_score:.3f} at {feat_point}"
        )
        return feat_point

    # 3. Fallback to best template match result if available
    if tpl_point is not None:
        logger.debug(
            f"Feature match failed, falling back to template match {tpl_point} "
            f"(score: {tpl_score:.3f})"
        )
        return tpl_point

    return (0, 0)


def align(
    image: Image,
    reference_images: Sequence[RefImage],
    method: str = "hybrid",
    min_match_score: float = 0.70,
    feature_detector: str = "orb",
    transformation: str = "auto",
) -> Image:
    """Align image against reference images using geometric transformation."""
    if image is None:
        raise ValueError("No image to align")
    if not reference_images:
        return image

    data = convert_image_to_np_array(image)
    w, h = image.size

    ref_image_coordinates = []
    alignment_ref_pos = []

    for ref in reference_images:
        template = cv2.imread(ref.file_name)
        if template is None:
            logger.warning(f"Could not load reference image: {ref.file_name}")
            continue

        matched_coord = _get_ref_coordinate(
            image=data,
            template=template,
            method=method,
            min_match_score=min_match_score,
            feature_detector=feature_detector,
        )
        ref_image_coordinates.append(matched_coord)
        alignment_ref_pos.append((ref.x, ref.y))

    n_points = len(ref_image_coordinates)
    if n_points == 0:
        return image

    pts1 = np.float32(ref_image_coordinates)
    pts2 = np.float32(alignment_ref_pos)
    trans_lower = (transformation or "auto").lower()

    if n_points == 1:
        # Single point translation
        dx = float(pts2[0][0] - pts1[0][0])
        dy = float(pts2[0][1] - pts1[0][1])
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        img = cv2.warpAffine(data, M, (w, h))
        return convert_np_array_to_image(img)

    if n_points == 2:
        # 2-point similarity transform
        M, _ = cv2.estimateAffinePartial2D(pts1, pts2)
        if M is None:
            return image
        img = cv2.warpAffine(data, M, (w, h))
        return convert_np_array_to_image(img)

    if n_points == 3:
        if trans_lower == "perspective":
            pass  # Fall through to affine since 3 points cannot define homography
        M = cv2.getAffineTransform(pts1, pts2)
        img = cv2.warpAffine(data, M, (w, h))
        return convert_np_array_to_image(img)

    # 4+ points: perspective (homography) or affine with RANSAC
    if trans_lower in ("perspective", "auto"):
        H, _ = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
        if H is not None:
            img = cv2.warpPerspective(data, H, (w, h))
            return convert_np_array_to_image(img)

    # Fallback to robust Affine for 4+ points
    M, _ = cv2.estimateAffine2D(pts1, pts2, method=cv2.RANSAC)
    if M is not None:
        img = cv2.warpAffine(data, M, (w, h))
        return convert_np_array_to_image(img)

    return image


def draw_rectangle(
    image: Image,
    x: int,
    y: int,
    w: int,
    h: int,
    rgb_colour: tuple = (255, 0, 0),
    thickness: int = 3,
) -> Image:
    if image is None:
        raise ValueError("No image to draw")
    ImageDraw.Draw(image).rectangle(
        xy=((x, y), (x + w, y + h)),
        outline=rgb_colour,
        width=thickness,
    )
    return image


def draw_text(
    image: Image,
    text: str,
    x: int,
    y: int,
    rgb_colour: tuple = (255, 0, 0),
    thickness: int = 1,
    font_size: int = 12,
) -> Image:
    if image is None:
        raise ValueError("No image to draw")
    font = ImageFont.load_default(size=font_size)
    ImageDraw.Draw(image).text(
        (x, y),
        text,
        fill=rgb_colour,
        font=font,
        width=thickness,
    )
    return image


def cut_image(
    image: Image,
    img_position: ImagePosition,
) -> Image:
    if image is None:
        raise ValueError("No image to cut")
    x, y, w, h = img_position.x, img_position.y, img_position.w, img_position.h
    return image.crop((x, y, x + w, y + h))


def crop_image(image: Image, x: int, y: int, w: int, h: int) -> Image:
    if image is None:
        raise ValueError("No image to crop")
    return image.crop((x, y, x + w, y + h))


def resize_image(image: Image, width: int, height: int) -> Image:
    if image is None:
        raise ValueError("No image to resize")
    return image.resize((width, height))


def adjust_image(
    image: Image,
    contrast: float = 1.0,
    brightness: float = 1.0,
    sharpness: float = 1.0,
    color: float = 1.0,
) -> Image:
    if image is None:
        raise ValueError("No image to adjust")
    image = PIL.ImageEnhance.Contrast(image).enhance(contrast)
    image = PIL.ImageEnhance.Brightness(image).enhance(brightness)
    image = PIL.ImageEnhance.Sharpness(image).enhance(sharpness)
    image = PIL.ImageEnhance.Color(image).enhance(color)
    return image


def convert_to_gray_scale(image: Image) -> Image:
    if image is None:
        raise ValueError("No image to convert to gray scale")
    return ImageOps.grayscale(image).convert("RGB")


def autocontrast_image(
    image: Image,
    cutoff_low: int = 0,
    cutoff_high: int = 0,
    ignore: int | None = None,
) -> Image:
    if image is None:
        raise ValueError("No image to autocontrast")
    if isinstance(image, Image):
        return ImageOps.autocontrast(
            image, cutoff=(cutoff_low, cutoff_high), ignore=ignore  # type: ignore
        )
    if isinstance(image, np.ndarray):
        return image
