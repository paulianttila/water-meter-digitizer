"""Unit tests for AdjustStep and side-by-side comparison."""

import asyncio
from unittest.mock import MagicMock, patch

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
    step.adjust_gamma = MagicMock()
    step.adjust_contrast = MagicMock()
    step.adjust_brightness = MagicMock()
    step.adjust_sharpness = MagicMock()
    step.adjust_color = MagicMock()
    step.grayscale_enabled = MagicMock()
    step.sharpness_mode = MagicMock()
    step.unsharp_radius = MagicMock()
    step.unsharp_amount = MagicMock()
    step.unsharp_threshold = MagicMock()
    step.auto_sharpen_cut_images = MagicMock()
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
    config.image_processing.gamma = 0.8
    config.image_processing.contrast = 1.5
    config.image_processing.sharpness_mode = "unsharp_mask"
    config.image_processing.unsharp_amount = 2.0
    config.image_processing.glare_suppression.enabled = True
    config.image_processing.glare_suppression.clahe_clip_limit = 3.5

    step.load_from_config(config)

    assert step.crop_enabled.value is True
    assert step.crop_x.value == 10
    assert step.crop_y.value == 20
    assert step.adjust_gamma.value == 0.8
    assert step.adjust_contrast.value == 1.5
    assert step.sharpness_mode.value == "unsharp_mask"
    assert step.unsharp_amount.value == 2.0
    assert step.glare_clahe_clip_limit.value == 3.5


def _mock_adjust_step_ui(
    step: AdjustStep,
    sample_image: Image.Image | None = None,
    **overrides,
) -> None:
    """Helper to initialize mock UI element values on AdjustStep instance."""
    defaults = {
        "live_preview": True,
        "compare_mode": "Single",
        "crop_enabled": False,
        "crop_x": 0,
        "crop_y": 0,
        "crop_w": 0,
        "crop_h": 0,
        "resize_enabled": False,
        "resize_w": 0,
        "resize_h": 0,
        "rotate_enabled": False,
        "rotate_angle": 0.0,
        "adjust_enabled": False,
        "adjust_gamma": 1.0,
        "adjust_contrast": 1.0,
        "adjust_brightness": 1.0,
        "adjust_sharpness": 1.0,
        "adjust_color": 1.0,
        "sharpness_mode": "standard",
        "unsharp_radius": 1.0,
        "unsharp_amount": 1.5,
        "unsharp_threshold": 3,
        "grayscale_enabled": False,
        "autocontrast_enabled": False,
        "autocontrast_cutoff_low": 0.0,
        "autocontrast_cutoff_high": 0.0,
        "glare_enabled": False,
        "glare_mode": "clahe",
        "glare_inpaint_threshold": 230,
        "glare_inpaint_radius": 3,
        "glare_clahe_clip_limit": 2.0,
        "glare_clahe_grid_size": 8,
    }
    defaults.update(overrides)
    for attr, val in defaults.items():
        setattr(step, attr, MagicMock(value=val))

    if sample_image is not None:
        b64_orig = img_utils.convert_image_base64str(sample_image)
        step.org_image = b64_orig


def test_adjust_step_do_adjust(sample_pil_image: Image.Image) -> None:
    """Verify _do_adjust applies processing transformations."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    _mock_adjust_step_ui(
        step,
        sample_pil_image,
        adjust_enabled=True,
        adjust_gamma=0.9,
        adjust_contrast=1.2,
        adjust_brightness=1.1,
        sharpness_mode="unsharp_mask",
    )

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    result_b64 = step._do_adjust(b64_orig)
    assert isinstance(result_b64, str)
    assert len(result_b64) > 0


def test_adjust_step_presets(sample_pil_image: Image.Image) -> None:
    """Verify presets set appropriate parameters."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    step.adjust_enabled = MagicMock()
    step.adjust_gamma = MagicMock()
    step.adjust_contrast = MagicMock()
    step.adjust_brightness = MagicMock()
    step.adjust_sharpness = MagicMock()
    step.adjust_color = MagicMock()
    step.sharpness_mode = MagicMock()
    step.unsharp_radius = MagicMock()
    step.unsharp_amount = MagicMock()
    step.unsharp_threshold = MagicMock()
    step.grayscale_enabled = MagicMock()
    step.autocontrast_enabled = MagicMock()
    step.glare_enabled = MagicMock()
    step.glare_mode = MagicMock()
    step.glare_clahe_clip_limit = MagicMock()

    with patch("nicegui.ui.notify"):
        step._apply_preset("crisp")
        assert step.sharpness_mode.value == "unsharp_mask"
        assert step.unsharp_amount.value == 1.6

        step._apply_preset("basement")
        assert step.adjust_gamma.value == 0.75
        assert step.adjust_brightness.value == 1.15


def test_adjust_step_debounced_on_param_change(
    sample_pil_image: Image.Image,
) -> None:
    """Verify _on_param_change debounces and triggers preview callback."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    _mock_adjust_step_ui(step, sample_pil_image)

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
    _mock_adjust_step_ui(step, sample_pil_image, compare_mode="Side-by-Side")
    b64_orig = img_utils.convert_image_base64str(sample_pil_image)

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
    _mock_adjust_step_ui(step, sample_pil_image, compare_mode="Single")

    async def run_test():
        step._on_param_change()
        await asyncio.sleep(0.2)
        cb.assert_called()
        comp_cb.assert_called_with("")

    asyncio.run(run_test())


def test_adjust_step_show():
    cb = MagicMock()
    comp_cb = MagicMock()
    step = AdjustStep(
        name="Adjust",
        set_image_callback=cb,
        set_comparison_callback=comp_cb,
    )

    with (
        patch("gui.step_adjust.ui") as mock_ui,
        patch("gui.step_base.ui") as mock_base_ui,
    ):
        mock_ui.step.return_value.__enter__ = MagicMock()
        mock_ui.step.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.column.return_value.__enter__ = MagicMock()
        mock_ui.column.return_value.__exit__ = MagicMock()
        mock_ui.grid.return_value.__enter__ = MagicMock()
        mock_ui.grid.return_value.__exit__ = MagicMock()
        mock_ui.expansion.return_value.__enter__ = MagicMock()
        mock_ui.expansion.return_value.__exit__ = MagicMock()
        mock_base_ui.expansion.return_value.__enter__ = MagicMock()
        mock_base_ui.expansion.return_value.__exit__ = MagicMock()
        mock_base_ui.column.return_value.__enter__ = MagicMock()
        mock_base_ui.column.return_value.__exit__ = MagicMock()

        stepper = MagicMock()
        asyncio.run(step.show(stepper))
        assert step.live_preview is not None
        assert step.crop_enabled is not None
        assert step.adjust_enabled is not None


def test_adjust_step_do_adjust_with_missing_ref_files(
    sample_pil_image: Image.Image,
) -> None:
    """Verify _do_adjust does not fail if ref_images point to non-existent files."""
    from data_classes import RefImage

    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    step.ref_images = [
        RefImage(
            name="Ref0", x=10, y=10, w=20, h=20, file_name="/nonexistent/ref0.jpg"
        ),
        RefImage(
            name="Ref1", x=50, y=10, w=20, h=20, file_name="/nonexistent/ref1.jpg"
        ),
        RefImage(
            name="Ref2", x=30, y=60, w=20, h=20, file_name="/nonexistent/ref2.jpg"
        ),
    ]
    _mock_adjust_step_ui(
        step,
        sample_pil_image,
        adjust_enabled=True,
        adjust_contrast=1.5,
    )

    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    # Should not raise FileNotFoundError, should successfully apply contrast
    result_b64 = step._do_adjust(b64_orig)
    assert isinstance(result_b64, str)
    assert len(result_b64) > 0


def test_adjust_step_preview_error_fallback(sample_pil_image: Image.Image) -> None:
    """Verify _update_preview_canvas falls back to original image on error."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig
    step.compare_mode = MagicMock(value="Single")

    with patch.object(step, "_do_adjust", side_effect=RuntimeError("Test error")):
        step._update_preview_canvas()
        cb.assert_called_with(b64_orig)
        assert step.image == b64_orig


def test_adjust_step_async_update_preview_offload(
    sample_pil_image: Image.Image,
) -> None:
    """Verify _async_update_preview_canvas offloads _do_adjust via asyncio.to_thread."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    b64_orig = img_utils.convert_image_base64str(sample_pil_image)
    step.org_image = b64_orig
    step.compare_mode = MagicMock(value="Single")

    async def run_test():
        with patch.object(
            step, "_do_adjust", return_value="adjusted_result"
        ) as mock_do:
            await step._async_update_preview_canvas()
            mock_do.assert_called_once_with(b64_orig)
            cb.assert_called_once_with("adjusted_result")
            assert step.image == "adjusted_result"

    asyncio.run(run_test())


def test_adjust_step_async_auto_enhance_offload(
    sample_pil_image: Image.Image,
) -> None:
    """Verify _async_apply_auto_enhance offloads auto_tune_image to worker thread."""
    cb = MagicMock()
    step = AdjustStep(name="Adjust", set_image_callback=cb)
    step.org_image = img_utils.convert_image_base64str(sample_pil_image)
    step.adjust_enabled = MagicMock()
    step.adjust_gamma = MagicMock()
    step.adjust_contrast = MagicMock()
    step.adjust_brightness = MagicMock()
    step.sharpness_mode = MagicMock()
    step.unsharp_amount = MagicMock()
    step.unsharp_radius = MagicMock()
    step.unsharp_threshold = MagicMock()

    mock_res = {
        "gamma": 1.1,
        "contrast": 1.2,
        "brightness": 1.0,
        "unsharp_amount": 1.8,
        "unsharp_radius": 1.2,
        "unsharp_threshold": 4,
        "focus_score": 250.0,
    }

    async def run_test():
        with (
            patch(
                "processor.image.ImageProcessor.get_image",
                return_value=np.zeros((10, 10, 3)),
            ),
            patch("utils.image.auto_tune_image", return_value=mock_res) as mock_tune,
            patch("nicegui.ui.notify"),
            patch.object(step, "_on_param_change"),
        ):
            await step._async_apply_auto_enhance()
            mock_tune.assert_called_once()
            assert step.adjust_gamma.value == 1.1
            assert step.adjust_contrast.value == 1.2
            assert step.sharpness_mode.value == "unsharp_mask"

    asyncio.run(run_test())
