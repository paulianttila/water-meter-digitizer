import os
import tempfile
import cv2
import numpy as np
from PIL import Image

from configuration import Config
from data_classes import RefImage
from utils.image import (
    align,
    _get_ref_coordinate,
    _match_features_coordinate,
    _get_feature_detector,
)


def _create_synthetic_pattern(size=(100, 100)) -> np.ndarray:
    """Create a rich textured pattern with corners and shapes for feature detection."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = 220
    w, h = size[0], size[1]
    cv2.rectangle(
        img, (int(w * 0.1), int(h * 0.1)), (int(w * 0.9), int(h * 0.9)), (40, 40, 40), 2
    )
    cv2.circle(img, (int(w * 0.5), int(h * 0.5)), int(w * 0.25), (30, 30, 180), -1)
    cv2.circle(
        img, (int(w * 0.35), int(h * 0.35)), max(2, int(w * 0.1)), (0, 200, 0), -1
    )
    cv2.putText(
        img,
        "REF",
        (int(w * 0.2), int(h * 0.6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.3, w / 150.0),
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.line(
        img, (int(w * 0.1), int(h * 0.9)), (int(w * 0.9), int(h * 0.1)), (255, 0, 0), 2
    )
    return cv2.GaussianBlur(img, (3, 3), 0.5)


def test_get_feature_detector():
    orb, norm_orb = _get_feature_detector("orb")
    assert norm_orb == cv2.NORM_HAMMING

    akaze, norm_akaze = _get_feature_detector("akaze")
    assert norm_akaze == cv2.NORM_HAMMING

    sift, norm_sift = _get_feature_detector("sift")
    assert norm_sift == cv2.NORM_L2


def test_feature_matching_translation():
    tpl = _create_synthetic_pattern((80, 80))
    full_img = np.zeros((400, 400, 3), dtype=np.uint8)
    full_img[:] = 180

    target_x, target_y = 120, 100
    full_img[target_y : target_y + 80, target_x : target_x + 80] = tpl

    # Test ORB
    coord, conf = _match_features_coordinate(full_img, tpl, detector_name="orb")
    assert coord is not None
    assert abs(coord[0] - target_x) <= 2
    assert abs(coord[1] - target_y) <= 2
    assert conf > 0.3

    # Test AKAZE
    coord_akaze, conf_akaze = _match_features_coordinate(
        full_img, tpl, detector_name="akaze"
    )
    assert coord_akaze is not None
    assert abs(coord_akaze[0] - target_x) <= 2
    assert abs(coord_akaze[1] - target_y) <= 2

    # Test SIFT
    coord_sift, conf_sift = _match_features_coordinate(
        full_img, tpl, detector_name="sift"
    )
    assert coord_sift is not None
    assert abs(coord_sift[0] - target_x) <= 2
    assert abs(coord_sift[1] - target_y) <= 2


def test_feature_matching_with_slight_rotation():
    tpl = _create_synthetic_pattern((80, 80))
    full_img = np.zeros((400, 400, 3), dtype=np.uint8)
    full_img[:] = 180

    # Place rotated template in full image (5 degrees rotation)
    center = (40, 40)
    rot_mat = cv2.getRotationMatrix2D(center, 5.0, 1.0)
    rot_tpl = cv2.warpAffine(tpl, rot_mat, (80, 80))

    target_x, target_y = 150, 150
    full_img[target_y : target_y + 80, target_x : target_x + 80] = rot_tpl

    # Template matching score degrades under rotation, feature matching handles it
    coord_feat, conf_feat = _match_features_coordinate(
        full_img, tpl, detector_name="orb"
    )
    assert coord_feat is not None
    assert abs(coord_feat[0] - target_x) <= 4
    assert abs(coord_feat[1] - target_y) <= 4


def test_get_ref_coordinate_hybrid_fallback():
    tpl = _create_synthetic_pattern((60, 60))
    full_img = np.zeros((300, 300, 3), dtype=np.uint8)
    full_img[:] = 180

    # Place slightly modified / rotated template
    center = (30, 30)
    rot_mat = cv2.getRotationMatrix2D(center, 8.0, 1.0)
    rot_tpl = cv2.warpAffine(tpl, rot_mat, (60, 60))

    target_x, target_y = 80, 70
    full_img[target_y : target_y + 60, target_x : target_x + 60] = rot_tpl

    # Hybrid with high min_match_score forces feature fallback
    pt = _get_ref_coordinate(
        full_img,
        tpl,
        method="hybrid",
        min_match_score=0.99,  # Force fallback
        feature_detector="orb",
    )
    assert abs(pt[0] - target_x) <= 4
    assert abs(pt[1] - target_y) <= 4


def test_align_2points_similarity():
    with tempfile.TemporaryDirectory() as tmpdir:
        tpl1 = _create_synthetic_pattern((40, 40))
        tpl2 = _create_synthetic_pattern((40, 40))

        p1_path = os.path.join(tmpdir, "ref0.jpg")
        p2_path = os.path.join(tmpdir, "ref1.jpg")
        cv2.imwrite(p1_path, tpl1)
        cv2.imwrite(p2_path, tpl2)

        ref0 = RefImage(name="ref0", x=50, y=50, w=40, h=40, file_name=p1_path)
        ref1 = RefImage(name="ref1", x=200, y=50, w=40, h=40, file_name=p2_path)

        # Create image with shifted reference points
        full_img = np.zeros((200, 300, 3), dtype=np.uint8)
        full_img[60:100, 60:100] = tpl1
        full_img[60:100, 210:250] = tpl2

        pil_img = Image.fromarray(full_img)
        aligned = align(
            pil_img,
            [ref0, ref1],
            method="template",
        )
        assert aligned.size == (300, 200)


def test_align_3points_affine():
    with tempfile.TemporaryDirectory() as tmpdir:
        tpl1 = _create_synthetic_pattern((40, 40))
        tpl2 = _create_synthetic_pattern((40, 40))
        tpl3 = _create_synthetic_pattern((40, 40))

        p1_path = os.path.join(tmpdir, "ref0.jpg")
        p2_path = os.path.join(tmpdir, "ref1.jpg")
        p3_path = os.path.join(tmpdir, "ref2.jpg")
        cv2.imwrite(p1_path, tpl1)
        cv2.imwrite(p2_path, tpl2)
        cv2.imwrite(p3_path, tpl3)

        ref0 = RefImage(name="ref0", x=50, y=50, w=40, h=40, file_name=p1_path)
        ref1 = RefImage(name="ref1", x=200, y=50, w=40, h=40, file_name=p2_path)
        ref2 = RefImage(name="ref2", x=120, y=150, w=40, h=40, file_name=p3_path)

        full_img = np.zeros((250, 300, 3), dtype=np.uint8)
        full_img[50:90, 50:90] = tpl1
        full_img[50:90, 200:240] = tpl2
        full_img[150:190, 120:160] = tpl3

        pil_img = Image.fromarray(full_img)
        aligned = align(
            pil_img,
            [ref0, ref1, ref2],
            method="hybrid",
            feature_detector="orb",
        )
        assert aligned.size == (300, 250)


def test_alignment_config_serialization():
    ini_content = """[Alignment]
RotationAngle = 180.0
PostRotationAngle = 0.0
Method = akaze
MinMatchScore = 0.85
FeatureDetector = akaze
Transformation = perspective
Refs = ref0

[Alignment.ref0]
image = /config/ref0.jpg
x = 100
y = 200
w = 30
h = 30
"""
    cfg = Config().load_from_string(ini_content)
    assert cfg.alignment.method == "akaze"
    assert cfg.alignment.min_match_score == 0.85
    assert cfg.alignment.feature_detector == "akaze"
    assert cfg.alignment.transformation == "perspective"

    saved = cfg.save_to_string()
    assert "method=akaze" in saved.lower()
    assert "minmatchscore=0.85" in saved.lower()
    assert "featuredetector=akaze" in saved.lower()
    assert "transformation=perspective" in saved.lower()
