import os
import numpy as np
import pytest
from PIL import Image

from configuration import Config, GlareSuppression
from data_classes import ImagePosition
from processor.image import ImageProcessor
import utils.image


def create_synthetic_image_with_glare(
    width: int = 100, height: int = 100
) -> Image.Image:
    """Create test image with dark background and white glare spot."""
    arr = np.full((height, width, 3), 80, dtype=np.uint8)
    # Add a bright specular hotspot (V=255, S=0)
    arr[40:60, 40:60] = [255, 255, 255]
    return Image.fromarray(arr, mode="RGB")


def test_detect_glare_mask():
    img = create_synthetic_image_with_glare()
    img_np = np.array(img)

    mask = utils.image.detect_glare_mask(img_np, threshold=230, sat_threshold=40)
    assert mask.shape == (100, 100)
    assert mask.dtype == np.uint8
    # Center hotspot must be detected
    assert mask[50, 50] == 255
    # Non-glare corners should be 0
    assert mask[5, 5] == 0

    # Test grayscale detection
    gray_np = np.array(img.convert("L"))
    gray_mask = utils.image.detect_glare_mask(gray_np, threshold=230)
    assert gray_mask[50, 50] == 255
    assert gray_mask[5, 5] == 0

    # Test invalid input
    with pytest.raises(ValueError):
        utils.image.detect_glare_mask(None)


def test_apply_clahe():
    img = create_synthetic_image_with_glare()
    img_np = np.array(img)

    clahe_rgb = utils.image.apply_clahe(img_np, clip_limit=2.0, grid_size=8)
    assert clahe_rgb.shape == img_np.shape
    assert clahe_rgb.dtype == np.uint8

    gray_np = np.array(img.convert("L"))
    clahe_gray = utils.image.apply_clahe(gray_np, clip_limit=2.0, grid_size=8)
    assert clahe_gray.shape == gray_np.shape
    assert clahe_gray.dtype == np.uint8

    with pytest.raises(ValueError):
        utils.image.apply_clahe(None)


def test_apply_inpaint_glare():
    img = create_synthetic_image_with_glare()
    img_np = np.array(img)

    inpainted = utils.image.apply_inpaint_glare(img_np, threshold=230, inpaint_radius=3)
    assert inpainted.shape == img_np.shape
    assert inpainted.dtype == np.uint8
    # Center pixel was 255; inpainting should interpolate it down
    assert inpainted[50, 50, 0] < 255

    # Test image with no glare
    clean_np = np.full((50, 50, 3), 100, dtype=np.uint8)
    no_glare = utils.image.apply_inpaint_glare(clean_np, threshold=230)
    assert np.array_equal(clean_np, no_glare)

    with pytest.raises(ValueError):
        utils.image.apply_inpaint_glare(None)


def test_apply_illumination_normalize():
    img = create_synthetic_image_with_glare()
    img_np = np.array(img)

    norm_rgb = utils.image.apply_illumination_normalize(img_np, sigma=20.0)
    assert norm_rgb.shape == img_np.shape
    assert norm_rgb.dtype == np.uint8

    gray_np = np.array(img.convert("L"))
    norm_gray = utils.image.apply_illumination_normalize(gray_np, sigma=20.0)
    assert norm_gray.shape == gray_np.shape
    assert norm_gray.dtype == np.uint8

    with pytest.raises(ValueError):
        utils.image.apply_illumination_normalize(None)


def test_suppress_glare_modes():
    img = create_synthetic_image_with_glare()

    for mode in ["clahe", "inpaint", "illumination_normalize", "combined", "other"]:
        res = utils.image.suppress_glare(
            img,
            mode=mode,
            inpaint_threshold=230,
            inpaint_radius=3,
            clahe_clip_limit=2.0,
            clahe_grid_size=8,
        )
        assert isinstance(res, Image.Image)
        assert res.size == img.size

    with pytest.raises(ValueError):
        utils.image.suppress_glare(None)


def test_image_processor_glare_suppression():
    img = create_synthetic_image_with_glare()

    proc = (
        ImageProcessor()
        .set_image(img)
        .if_(True)
        .suppress_glare(mode="combined")
        .endif_()
    )
    res = proc.get_image()
    assert isinstance(res, Image.Image)

    # Condition is false -> image unchanged
    proc_bypassed = (
        ImageProcessor()
        .set_image(img)
        .if_(False)
        .suppress_glare(mode="combined")
        .endif_()
    )
    res_bypassed = proc_bypassed.get_image()
    assert np.array_equal(np.array(img), np.array(res_bypassed))


def test_image_processing_pipeline_autocontrast_and_glare_flags():
    """Verify ImageProcessing config correctly skips autocontrast when disabled."""
    img = create_synthetic_image_with_glare()

    config = Config()
    config.image_processing.enabled = True
    config.image_processing.autocontrast.enabled = False
    config.image_processing.glare_suppression.enabled = True
    config.image_processing.glare_suppression.mode = "clahe"

    proc = (
        ImageProcessor()
        .set_image(img)
        .enable_image_saving(True)
        .if_(config.image_processing.enabled)
        .adjust_image(
            brightness=config.image_processing.brightness,
            contrast=config.image_processing.contrast,
            sharpness=config.image_processing.sharpness,
            color=config.image_processing.color,
        )
        .endif_()
        .if_(
            config.image_processing.enabled
            and config.image_processing.autocontrast.enabled
        )
        .autocontrast_image(
            cutoff_low=config.image_processing.autocontrast.cutoff_low,
            cutoff_high=config.image_processing.autocontrast.cutoff_high,
            ignore=config.image_processing.autocontrast.ignore,
        )
        .save_image("processed")
        .endif_()
        .if_(
            config.image_processing.enabled
            and config.image_processing.glare_suppression.enabled
        )
        .suppress_glare(
            mode=config.image_processing.glare_suppression.mode,
            inpaint_threshold=config.image_processing.glare_suppression.inpaint_threshold,
            inpaint_radius=config.image_processing.glare_suppression.inpaint_radius,
            clahe_clip_limit=config.image_processing.glare_suppression.clahe_clip_limit,
            clahe_grid_size=config.image_processing.glare_suppression.clahe_grid_size,
        )
        .save_image("glare_suppressed")
        .endif_()
    )

    pics = proc.get_pictures()
    # "processed" (autocontrast) should NOT be saved because
    # autocontrast.enabled is False
    assert "processed" not in pics
    # "glare_suppressed" MUST be saved because
    # glare_suppression.enabled is True
    assert "glare_suppressed" in pics


def test_cut_images_with_glare_suppression():
    img = create_synthetic_image_with_glare()
    pos = ImagePosition(name="digit1", x=30, y=30, w=40, h=40)

    proc = (
        ImageProcessor()
        .set_image(img)
        .start_image_cutting()
        .cut_image(pos, glare_suppression=True, glare_mode="inpaint")
        .stop_image_cutting()
    )
    cut = proc.get_cut_images()[0]
    assert cut.name == "digit1"
    assert cut.image.size == (40, 40)

    # Test multiple cuts
    proc2 = (
        ImageProcessor()
        .set_image(img)
        .start_image_cutting()
        .cut_images([pos], glare_suppression=True, glare_mode="clahe")
        .stop_image_cutting()
    )
    assert len(proc2.get_cut_images()) == 1


def test_config_glare_serialization():
    temp_file = "temp_glare_test.ini"
    try:
        config = Config().load_from_file("config/config.ini")
        config.image_processing.glare_suppression = GlareSuppression(
            enabled=True,
            mode="combined",
            inpaint_threshold=220,
            inpaint_radius=5,
            clahe_clip_limit=3.5,
            clahe_grid_size=16,
            apply_to_cut_images=True,
        )
        config.save_to_file(temp_file)

        reloaded = Config().load_from_file(temp_file)
        glare = reloaded.image_processing.glare_suppression
        assert glare.enabled is True
        assert glare.mode == "combined"
        assert glare.inpaint_threshold == 220
        assert glare.inpaint_radius == 5
        assert glare.clahe_clip_limit == 3.5
        assert glare.clahe_grid_size == 16
        assert glare.apply_to_cut_images is True
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_step_adjust_load_autocontrast_cut_images():
    from unittest.mock import MagicMock
    from gui.step_adjust import AdjustStep

    step = AdjustStep(name="Adjust", set_image_callback=MagicMock())
    step.crop_enabled = MagicMock()
    step.crop_x = MagicMock()
    step.crop_y = MagicMock()
    step.crop_w = MagicMock()
    step.crop_h = MagicMock()
    step.resize_enabled = MagicMock()
    step.resize_w = MagicMock()
    step.resize_h = MagicMock()
    step.adjust_enabled = MagicMock()
    step.adjust_contrast = MagicMock()
    step.adjust_brightness = MagicMock()
    step.adjust_sharpness = MagicMock()
    step.adjust_color = MagicMock()
    step.grayscale_enabled = MagicMock()
    step.autocontrast_enabled = MagicMock()
    step.autocontrast_cutoff_low = MagicMock()
    step.autocontrast_cutoff_high = MagicMock()
    step.autocontrast_cut_images_enabled = MagicMock()
    step.autocontrast_cut_images_cutoff_low = MagicMock()
    step.autocontrast_cut_images_cutoff_high = MagicMock()
    step.glare_enabled = MagicMock()
    step.glare_mode = MagicMock()
    step.glare_inpaint_threshold = MagicMock()
    step.glare_inpaint_radius = MagicMock()
    step.glare_clahe_clip_limit = MagicMock()
    step.glare_clahe_grid_size = MagicMock()
    step.glare_apply_to_cut_images = MagicMock()
    step.alignment_method = MagicMock()
    step.alignment_min_match_score = MagicMock()
    step.alignment_feature_detector = MagicMock()
    step.alignment_transformation = MagicMock()
    step.rotate_angle = MagicMock()
    step.rotate_enabled = MagicMock()

    config = Config()
    config.image_processing.autocontrast_cut_images.enabled = True
    config.image_processing.autocontrast_cut_images.cutoff_low = 3.5
    config.image_processing.autocontrast_cut_images.cutoff_high = 40.0
    config.image_processing.glare_suppression.enabled = True
    config.image_processing.glare_suppression.mode = "inpaint"

    step.load_from_config(config)

    assert step.autocontrast_cut_images_enabled.value is True
    assert step.autocontrast_cut_images_cutoff_low.value == 3.5
    assert step.autocontrast_cut_images_cutoff_high.value == 40.0
    assert step.glare_enabled.value is True
    assert step.glare_mode.value == "inpaint"


def test_step_draw_rois_cut_images_with_glare():
    from unittest.mock import MagicMock
    from gui.step_draw_rois_base import DrawRoisBaseStep, Roi

    step = DrawRoisBaseStep(
        name="Digital ROIs",
        name_template="digit",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value=""),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    img = create_synthetic_image_with_glare()
    b64 = utils.image.convert_image_base64str(img)

    step.rois = [Roi(name="digit1", x=10, y=10, w=30, h=30, color="red", enabled=True)]
    step.update_image(
        b64,
        autocontrast=False,
        glare_suppression=True,
        glare_mode="clahe",
    )
    cuts = step._cut_images()
    assert len(cuts) == 1
    assert cuts[0].name == "digit1"
    assert cuts[0].image.size == (30, 30)
