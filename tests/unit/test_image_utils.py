"""Unit tests for image utilities in src/utils/image.py."""

import numpy as np
import pytest
from PIL import Image

import utils.image as img_utils
from data_classes import ImagePosition, RefImage


@pytest.fixture
def sample_pil_image() -> Image.Image:
    """Generate a simple 100x100 RGB PIL image."""
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[20:40, 20:40] = [255, 0, 0]  # Red square
    arr[60:80, 60:80] = [0, 255, 0]  # Green square
    return Image.fromarray(arr)


def test_align_missing_reference_file_returns_original(
    sample_pil_image: Image.Image,
) -> None:
    """Verify that align returns original image when a template file is missing."""
    refs = [
        RefImage(
            name=f"ref{i}",
            x=10 * i,
            y=10 * i,
            w=20,
            h=20,
            file_name=f"/non/existent/path/ref{i}.jpg",
        )
        for i in range(3)
    ]
    result = img_utils.align(sample_pil_image, refs)
    assert result == sample_pil_image


def test_align_non_three_refs_returns_original(sample_pil_image: Image.Image) -> None:
    """Verify align returns original image if number of reference markers is not exactly 3."""
    # 1 marker
    refs1 = [RefImage(name="ref1", x=10, y=10, w=20, h=20, file_name="ref1.jpg")]
    assert img_utils.align(sample_pil_image, refs1) == sample_pil_image

    # 2 markers
    refs2 = [
        RefImage(name="ref1", x=10, y=10, w=20, h=20, file_name="ref1.jpg"),
        RefImage(name="ref2", x=30, y=30, w=20, h=20, file_name="ref2.jpg"),
    ]
    assert img_utils.align(sample_pil_image, refs2) == sample_pil_image

    # 4 markers
    refs4 = [
        RefImage(
            name=f"ref{i}", x=10 * i, y=10 * i, w=20, h=20, file_name=f"ref{i}.jpg"
        )
        for i in range(4)
    ]
    assert img_utils.align(sample_pil_image, refs4) == sample_pil_image


def test_align_empty_refs_returns_original(sample_pil_image: Image.Image) -> None:
    """Verify align returns original image if no reference markers are given."""
    result = img_utils.align(sample_pil_image, [])
    assert result == sample_pil_image


def test_align_none_image_raises_value_error() -> None:
    """Verify that align raises ValueError when image is None."""
    refs = [RefImage(name="ref0", x=10, y=10, w=20, h=20, file_name="ref.jpg")]
    with pytest.raises(ValueError, match="No image to align"):
        img_utils.align(None, refs)  # type: ignore


def test_align_successful(tmp_path, sample_pil_image: Image.Image) -> None:
    """Verify 3-point affine alignment succeeds when template images exist."""
    # Create 3 small reference templates
    ref_files = []
    positions = [(10, 10), (80, 10), (50, 80)]
    for i, (rx, ry) in enumerate(positions):
        ref_path = tmp_path / f"ref_{i}.jpg"
        crop = sample_pil_image.crop((rx, ry, rx + 15, ry + 15))
        crop.save(str(ref_path))
        ref_files.append(
            RefImage(name=f"ref{i}", x=rx, y=ry, w=15, h=15, file_name=str(ref_path))
        )

    aligned = img_utils.align(sample_pil_image, ref_files)
    assert isinstance(aligned, Image.Image)
    assert aligned.size == sample_pil_image.size


def test_get_ref_coordinate_none_inputs() -> None:
    """Verify _get_ref_coordinate raises ValueError on None inputs."""
    arr = np.zeros((50, 50, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Image and template must not be None"):
        img_utils._get_ref_coordinate(None, arr)  # type: ignore

    with pytest.raises(ValueError, match="Image and template must not be None"):
        img_utils._get_ref_coordinate(arr, None)  # type: ignore


def test_conversions(sample_pil_image: Image.Image) -> None:
    """Verify image format conversion helpers."""
    # PIL to bytes
    raw_bytes = img_utils.convert_image_to_bytes(sample_pil_image)
    assert isinstance(raw_bytes, bytes)
    assert len(raw_bytes) > 0

    # bytes to PIL
    reloaded = img_utils.bytes_to_image(raw_bytes)
    assert reloaded.size == sample_pil_image.size

    # Base64 conversions
    b64_str = img_utils.convert_image_base64str(sample_pil_image)
    assert isinstance(b64_str, str)
    from_b64 = img_utils.convert_base64_str_to_image(b64_str)
    assert from_b64.size == sample_pil_image.size

    # NumPy conversions
    arr = img_utils.convert_image_to_np_array(sample_pil_image)
    assert isinstance(arr, np.ndarray)
    from_arr = img_utils.convert_np_array_to_image(arr)
    assert from_arr.size == sample_pil_image.size


def test_transformations(sample_pil_image: Image.Image) -> None:
    """Verify image transformations (rotate, crop, resize, grayscale)."""
    # Size check
    assert img_utils.image_size(sample_pil_image) == (100, 100)

    # Rotation
    rotated = img_utils.rotate(sample_pil_image, 90.0, keep_org_size=True)
    assert rotated.size == (100, 100)

    # Crop
    cropped = img_utils.crop_image(sample_pil_image, 10, 10, 30, 30)
    assert cropped.size == (30, 30)

    # Cut with ImagePosition
    pos = ImagePosition(name="digit1", x=5, y=5, w=25, h=25)
    cut = img_utils.cut_image(sample_pil_image, pos)
    assert cut.size == (25, 25)

    # Resize
    resized = img_utils.resize_image(sample_pil_image, 50, 50)
    assert resized.size == (50, 50)

    # Grayscale
    gray = img_utils.convert_to_gray_scale(sample_pil_image)
    assert gray.mode == "RGB"
    assert gray.size == (100, 100)


def test_drawing(sample_pil_image: Image.Image) -> None:
    """Verify rectangle and text drawing helpers."""
    drawn = img_utils.draw_rectangle(sample_pil_image.copy(), 10, 10, 20, 20)
    assert isinstance(drawn, Image.Image)

    text_drawn = img_utils.draw_text(sample_pil_image.copy(), "Test", 10, 10)
    assert isinstance(text_drawn, Image.Image)
