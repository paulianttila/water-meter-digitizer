"""Unit tests for AdjustStep and side-by-side comparison."""

import asyncio
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

import utils.image as img_utils
from configuration import Config
from gui.step_adjust import AdjustStep


@pytest.fixture
def sample_pil_image() -> Image.Image:
    """Generate a simple 100x100 RGB PIL image."""
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[20:40, 20:40] = [255, 0, 0]
    arr[60:80, 60:80] = [0, 255, 0]
    return Image.fromarray(arr)


def test_side_by_side_comparison(sample_pil_image: Image.Image) -> None:
    """Verify side-by-side comparison generator creates horizontal composite."""
    comp = img_utils.create_side_by_side_comparison(
        sample_pil_image, sample_pil_image, label_left="BEFORE", label_right="AFTER"
    )
    assert isinstance(comp, Image.Image)
    # Width should be w1 + w2 + 4 separator
    assert comp.size[0] == 100 + 100 + 4
    assert comp.size[1] == 100


def test_side_by_side_comparison_none_inputs() -> None:
    """Verify ValueError on None inputs."""
    with pytest.raises(ValueError, match="Both images must be provided"):
        img_utils.create_side_by_side_comparison(None, None)  # type: ignore


def test_adjust_step_init() -> None:
    """Verify AdjustStep initializes with expected attributes."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    assert step.name == "Adjust"
    assert step.set_image_callback == cb
    assert step.org_image == ""


def test_adjust_step_load_from_config(sample_pil_image: Image.Image) -> None:
    """Verify AdjustStep loads parameters from Config object."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)

    # Mock UI elements
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
    step.rotate_angle = MagicMock()
    step.rotate_enabled = MagicMock()

    config = Config()
    config.crop.enabled = True
    config.crop.x = 10
    config.crop.y = 20
    config.image_processing.enabled = True
    config.image_processing.contrast = 1.5
    config.image_processing.glare_suppression.enabled = True
    config.image_processing.glare_suppression.clahe_clip_limit = 3.5

    step.load_from_config(config)

    assert step.crop_enabled.value is True
    assert step.crop_x.value == 10
    assert step.crop_y.value == 20
    assert step.adjust_contrast.value == 1.5
    assert step.glare_clahe_clip_limit.value == 3.5


def test_adjust_step_do_adjust(sample_pil_image: Image.Image) -> None:
    """Verify _do_adjust applies processing transformations."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)

    # Initialize mocked UI elements
    step.crop_enabled = MagicMock(value=False)
    step.crop_x = MagicMock(value=0)
    step.crop_y = MagicMock(value=0)
    step.crop_w = MagicMock(value=0)
    step.crop_h = MagicMock(value=0)
    step.resize_enabled = MagicMock(value=False)
    step.resize_w = MagicMock(value=0)
    step.resize_h = MagicMock(value=0)
    step.rotate_enabled = MagicMock(value=False)
    step.rotate_angle = MagicMock(value=0.0)
    step.adjust_enabled = MagicMock(value=True)
    step.adjust_contrast = MagicMock(value=1.2)
    step.adjust_brightness = MagicMock(value=1.1)
    step.adjust_sharpness = MagicMock(value=1.0)
    step.adjust_color = MagicMock(value=1.0)
    step.grayscale_enabled = MagicMock(value=False)
    step.autocontrast_enabled = MagicMock(value=False)
    step.autocontrast_cutoff_low = MagicMock(value=0.0)
    step.autocontrast_cutoff_high = MagicMock(value=0.0)
    step.glare_enabled = MagicMock(value=False)
    step.glare_mode = MagicMock(value="clahe")
    step.glare_inpaint_threshold = MagicMock(value=230)
    step.glare_inpaint_radius = MagicMock(value=3)
    step.glare_clahe_clip_limit = MagicMock(value=2.0)
    step.glare_clahe_grid_size = MagicMock(value=8)

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig

    result_b64 = step._do_adjust(b64_orig)
    assert isinstance(result_b64, str)
    assert len(result_b64) > 0


def test_adjust_step_debounced_on_param_change(
    sample_pil_image: Image.Image,
) -> None:
    """Verify _on_param_change debounces and triggers preview callback."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)

    step.live_preview = MagicMock(value=True)
    step.compare_mode = MagicMock(value="Single")
    step.crop_enabled = MagicMock(value=False)
    step.crop_x = MagicMock(value=0)
    step.crop_y = MagicMock(value=0)
    step.crop_w = MagicMock(value=0)
    step.crop_h = MagicMock(value=0)
    step.resize_enabled = MagicMock(value=False)
    step.resize_w = MagicMock(value=0)
    step.resize_h = MagicMock(value=0)
    step.rotate_enabled = MagicMock(value=False)
    step.rotate_angle = MagicMock(value=0.0)
    step.adjust_enabled = MagicMock(value=False)
    step.adjust_contrast = MagicMock(value=1.0)
    step.adjust_brightness = MagicMock(value=1.0)
    step.adjust_sharpness = MagicMock(value=1.0)
    step.adjust_color = MagicMock(value=1.0)
    step.grayscale_enabled = MagicMock(value=False)
    step.autocontrast_enabled = MagicMock(value=False)
    step.autocontrast_cutoff_low = MagicMock(value=0.0)
    step.autocontrast_cutoff_high = MagicMock(value=0.0)
    step.glare_enabled = MagicMock(value=False)
    step.glare_mode = MagicMock(value="clahe")
    step.glare_inpaint_threshold = MagicMock(value=230)
    step.glare_inpaint_radius = MagicMock(value=3)
    step.glare_clahe_clip_limit = MagicMock(value=2.0)
    step.glare_clahe_grid_size = MagicMock(value=8)

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig

    async def run_debounce_test():
        step._on_param_change()
        await asyncio.sleep(0.2)
        cb.assert_called()

    asyncio.run(run_debounce_test())


def test_adjust_step_comparison_callback_side_by_side(
    sample_pil_image: Image.Image,
) -> None:
    """Verify side-by-side mode emits composite to set_comparison_callback."""
    cb = MagicMock()
    comp_cb = MagicMock()
    step = AdjustStep(
        name="Adjust",
        set_image_callback=cb,
        set_comparison_callback=comp_cb,
    )

    step.live_preview = MagicMock(value=True)
    step.compare_mode = MagicMock(value="Side-by-Side")
    step.crop_enabled = MagicMock(value=False)
    step.crop_x = MagicMock(value=0)
    step.crop_y = MagicMock(value=0)
    step.crop_w = MagicMock(value=0)
    step.crop_h = MagicMock(value=0)
    step.resize_enabled = MagicMock(value=False)
    step.resize_w = MagicMock(value=0)
    step.resize_h = MagicMock(value=0)
    step.rotate_enabled = MagicMock(value=False)
    step.rotate_angle = MagicMock(value=0.0)
    step.adjust_enabled = MagicMock(value=False)
    step.adjust_contrast = MagicMock(value=1.0)
    step.adjust_brightness = MagicMock(value=1.0)
    step.adjust_sharpness = MagicMock(value=1.0)
    step.adjust_color = MagicMock(value=1.0)
    step.grayscale_enabled = MagicMock(value=False)
    step.autocontrast_enabled = MagicMock(value=False)
    step.autocontrast_cutoff_low = MagicMock(value=0.0)
    step.autocontrast_cutoff_high = MagicMock(value=0.0)
    step.glare_enabled = MagicMock(value=False)
    step.glare_mode = MagicMock(value="clahe")
    step.glare_inpaint_threshold = MagicMock(value=230)
    step.glare_inpaint_radius = MagicMock(value=3)
    step.glare_clahe_clip_limit = MagicMock(value=2.0)
    step.glare_clahe_grid_size = MagicMock(value=8)

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig

    async def run_test():
        step._on_param_change()
        await asyncio.sleep(0.2)
        cb.assert_called_with(b64_orig)
        comp_cb.assert_called()
        # Non-empty base64 string
        args, _ = comp_cb.call_args
        assert isinstance(args[0], str)
        assert len(args[0]) > 0

    asyncio.run(run_test())


def test_adjust_step_comparison_callback_single_clears(
    sample_pil_image: Image.Image,
) -> None:
    """Verify single mode clears comparison image via set_comparison_callback."""
    cb = MagicMock()
    comp_cb = MagicMock()
    step = AdjustStep(
        name="Adjust",
        set_image_callback=cb,
        set_comparison_callback=comp_cb,
    )

    step.live_preview = MagicMock(value=True)
    step.compare_mode = MagicMock(value="Single")
    step.crop_enabled = MagicMock(value=False)
    step.crop_x = MagicMock(value=0)
    step.crop_y = MagicMock(value=0)
    step.crop_w = MagicMock(value=0)
    step.crop_h = MagicMock(value=0)
    step.resize_enabled = MagicMock(value=False)
    step.resize_w = MagicMock(value=0)
    step.resize_h = MagicMock(value=0)
    step.rotate_enabled = MagicMock(value=False)
    step.rotate_angle = MagicMock(value=0.0)
    step.adjust_enabled = MagicMock(value=False)
    step.adjust_contrast = MagicMock(value=1.0)
    step.adjust_brightness = MagicMock(value=1.0)
    step.adjust_sharpness = MagicMock(value=1.0)
    step.adjust_color = MagicMock(value=1.0)
    step.grayscale_enabled = MagicMock(value=False)
    step.autocontrast_enabled = MagicMock(value=False)
    step.autocontrast_cutoff_low = MagicMock(value=0.0)
    step.autocontrast_cutoff_high = MagicMock(value=0.0)
    step.glare_enabled = MagicMock(value=False)
    step.glare_mode = MagicMock(value="clahe")
    step.glare_inpaint_threshold = MagicMock(value=230)
    step.glare_inpaint_radius = MagicMock(value=3)
    step.glare_clahe_clip_limit = MagicMock(value=2.0)
    step.glare_clahe_grid_size = MagicMock(value=8)

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig

    async def run_test():
        step._on_param_change()
        await asyncio.sleep(0.2)
        cb.assert_called()
        comp_cb.assert_called_with("")

    asyncio.run(run_test())
