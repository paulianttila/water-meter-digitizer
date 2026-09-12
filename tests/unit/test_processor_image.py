"""Unit tests for ImageProcessor in src/processor/image.py."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from data_classes import ImagePosition, RefImage
from processor.image import ImageProcessor


@pytest.fixture
def sample_image() -> Image.Image:
    arr = np.zeros((120, 120, 3), dtype=np.uint8)
    arr[30:50, 30:50] = [255, 0, 0]
    return Image.fromarray(arr)


def test_image_processor_conditional_execution(sample_image: Image.Image):
    ip = ImageProcessor()
    ip.set_image(sample_image)

    # if_ False skips method
    ip.if_(False).rotate_image(90).endif_()
    assert ip.get_image().size == (120, 120)

    # else_ switches condition
    ip.if_(False).crop_image(0, 0, 50, 50).else_().crop_image(0, 0, 60, 60).endif_()
    assert ip.get_image().size == (60, 60)


def test_image_processor_save_and_get_picture(sample_image: Image.Image):
    ip = ImageProcessor()
    ip.set_image(sample_image)

    # Saving disabled by default
    ip.save_image("orig")
    assert "orig" not in ip.get_pictures()

    # Enable saving
    ip.enable_image_saving(True)
    ip.save_image("orig")
    assert "orig" in ip.get_pictures()
    img_copy = ip.get_picture("orig")
    assert img_copy.size == sample_image.size

    # Force save
    ip.enable_image_saving(False)
    ip.save_image("forced", force_save=True)
    assert "forced" in ip.get_pictures()

    with pytest.raises(ValueError, match="No image with name non_existent available"):
        ip.get_picture("non_existent")


def test_image_processor_b64_and_download(tmp_path, sample_image: Image.Image):
    ip = ImageProcessor()
    ip.set_image(sample_image)

    b64 = ip.get_image_as_base64_str()
    assert isinstance(b64, str)

    ip2 = ImageProcessor()
    ip2.set_image_from_base64_str(b64)
    assert ip2.get_image().size == sample_image.size

    # Download image
    img_path = tmp_path / "test.jpg"
    sample_image.save(str(img_path))
    with patch("utils.download.load_file_from_url", return_value=img_path.read_bytes()):
        ip.download_image("http://fake.url/img.jpg", timeout=5, min_image_size=10)
        assert ip.get_image().size == sample_image.size


def test_image_processor_manipulations(sample_image: Image.Image):
    ip = ImageProcessor()
    ip.set_image(sample_image)

    ip.rotate_image(45.0)
    assert ip.get_image() is not None

    ip.resize_image(80, 80)
    assert ip.get_image().size == (80, 80)

    ip.adjust_image(contrast=1.2, brightness=1.1, sharpness=1.5, color=0.8)
    assert ip.get_image() is not None

    ip.autocontrast_image(cutoff_low=2, cutoff_high=10, ignore=1)
    assert ip.get_image() is not None

    ip.suppress_glare(mode="clahe", inpaint_threshold=200)
    assert ip.get_image() is not None

    ip.to_gray_scale()
    assert ip.get_image().mode == "RGB"


def test_image_processor_align_and_cutting(tmp_path, sample_image: Image.Image):
    ref_path = tmp_path / "ref.jpg"
    crop = sample_image.crop((10, 10, 25, 25))
    crop.save(str(ref_path))

    refs = [
        RefImage(name="ref0", x=10, y=10, w=15, h=15, file_name=str(ref_path)),
        RefImage(name="ref1", x=60, y=10, w=15, h=15, file_name=str(ref_path)),
        RefImage(name="ref2", x=30, y=60, w=15, h=15, file_name=str(ref_path)),
    ]

    ip = ImageProcessor()
    ip.set_image(sample_image)
    ip.align_image(refs)

    # Cutting
    pos1 = ImagePosition(name="d1", x=10, y=10, w=20, h=30)
    pos2 = ImagePosition(name="d2", x=40, y=10, w=20, h=30)

    ip.start_image_cutting()
    ip.cut_image(pos1, autocontrast=True, glare_suppression=True)
    ip.cut_images([pos2], autocontrast=True, glare_suppression=True)
    ip.stop_image_cutting()

    cut_list = ip.get_cut_images()
    assert len(cut_list) == 2
    assert cut_list[0].name == "d1"
    assert cut_list[1].name == "d2"

    ip.save_cut_images()
    pics = ip.get_pictures()
    assert "d1" in pics
    assert "d2" in pics


def test_image_processor_draw_rois(tmp_path, sample_image: Image.Image):
    ref_path = tmp_path / "ref_tmpl.jpg"
    sample_image.crop((0, 0, 20, 20)).save(str(ref_path))

    ip = ImageProcessor()
    ip.set_image(sample_image)

    # None config
    ip.draw_meter_rois(None)

    # Valid config
    mock_config = MagicMock()
    mock_config.alignment.ref_images = [
        RefImage(name="ref0", x=10, y=10, w=0, h=0, file_name=str(ref_path))
    ]
    mock_config.digital_readout.cut_images = [
        ImagePosition(name="dig1", x=20, y=20, w=15, h=25)
    ]
    mock_config.analog_readout.cut_images = [
        ImagePosition(name="ana1", x=40, y=20, w=15, h=25)
    ]

    with patch("utils.image.image_size_from_file", return_value=(20, 20)):
        ip.draw_meter_rois(
            mock_config, draw_refs=True, draw_digital=True, draw_analog=True
        )

    drawn = ip.get_image()
    assert drawn.size == sample_image.size
