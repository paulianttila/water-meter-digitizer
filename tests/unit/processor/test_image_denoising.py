"""Unit tests for edge-preserving image denoising in ImageProcessor and Config."""

import configparser
import io

import numpy as np
import pytest
from PIL import Image

from config.serializer import load_config_from_parser, save_config_to_io
from configuration import Config
from data_classes import CutImageOptions, ImagePosition
from processor.image import ImageProcessor


@pytest.fixture
def noisy_image() -> Image.Image:
    """Create a synthetic test image with noise and sharp edges."""
    np.random.seed(42)
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    # Bright square in center
    arr[30:70, 30:70] = [200, 200, 200]
    # Add Gaussian noise
    noise = np.random.normal(0, 25, arr.shape).astype(np.int16)
    noisy_arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_arr, mode="RGB")


def test_image_processor_denoise_methods(noisy_image: Image.Image):
    """Test all denoising methods through ImageProcessor chaining."""
    ip = ImageProcessor().set_image(noisy_image)

    # Bilateral
    ip.denoise_image(method="bilateral", diameter=5, sigma_color=50.0, sigma_space=50.0)
    out1 = ip.get_image()
    assert out1.size == (100, 100)

    # NL-Means
    ip.set_image(noisy_image)
    ip.denoise_image(
        method="nlmeans",
        strength=3.0,
        template_window=7,
        search_window=21,
    )
    out2 = ip.get_image()
    assert out2.size == (100, 100)

    # Median
    ip.set_image(noisy_image)
    ip.denoise_image(method="median", diameter=3)
    out3 = ip.get_image()
    assert out3.size == (100, 100)

    # Median + Bilateral hybrid
    ip.set_image(noisy_image)
    ip.denoise_image(
        method="median_bilateral",
        diameter=5,
        sigma_color=50.0,
        sigma_space=50.0,
    )
    out4 = ip.get_image()
    assert out4.size == (100, 100)


def test_image_processor_denoise_conditional(noisy_image: Image.Image):
    """Test conditional execution of denoise_image in processor pipeline."""
    ip = ImageProcessor().set_image(noisy_image)

    # When False, image remains identical
    ip.if_(False).denoise_image(method="bilateral", diameter=9).endif_()
    np.testing.assert_array_equal(np.array(ip.get_image()), np.array(noisy_image))

    # When True, image is modified
    ip.if_(True).denoise_image(method="bilateral", diameter=9).endif_()
    assert not np.array_equal(np.array(ip.get_image()), np.array(noisy_image))


def test_cut_image_with_denoise(noisy_image: Image.Image):
    """Test that cut_images applies denoising when options.denoise is enabled."""
    ip = ImageProcessor().set_image(noisy_image)
    positions = [ImagePosition(name="roi1", x=20, y=20, w=40, h=40)]

    # Cutting without denoise
    opts_no_denoise = CutImageOptions(denoise=False)
    ip.start_image_cutting().cut_images(
        positions, options=opts_no_denoise
    ).stop_image_cutting()
    cut_raw = ip.get_cut_images()[0].image

    # Cutting with denoise
    ip.set_image(noisy_image)
    opts_with_denoise = CutImageOptions(
        denoise=True,
        denoise_method="bilateral",
        denoise_diameter=9,
        denoise_sigma_color=75.0,
        denoise_sigma_space=75.0,
    )
    ip.start_image_cutting().cut_images(
        positions, options=opts_with_denoise
    ).stop_image_cutting()
    cut_denoised = ip.get_cut_images()[0].image

    # The denoised crop should differ from the raw crop
    assert not np.array_equal(np.array(cut_raw), np.array(cut_denoised))


def test_denoise_config_serialization_under_image_processing():
    """Verify all Denoise* parameters serialize directly under [ImageProcessing]."""
    config = Config().load_from_file("config/config.ini")

    # Modify denoise settings
    config.image_processing.denoise.enabled = True
    config.image_processing.denoise.method = "nlmeans"
    config.image_processing.denoise.diameter = 7
    config.image_processing.denoise.sigma_color = 65.0
    config.image_processing.denoise.sigma_space = 70.0
    config.image_processing.denoise.strength = 4.5
    config.image_processing.denoise.template_window = 5
    config.image_processing.denoise.search_window = 19
    config.image_processing.denoise.apply_to_cut_images = True

    # Serialize to INI string
    stream = io.StringIO()
    save_config_to_io(config, stream)
    ini_str = stream.getvalue()

    # Ensure NO separate [ImageProcessing.Denoise] or [Denoise] section exists
    parser = configparser.ConfigParser()
    parser.read_string(ini_str)
    assert not parser.has_section("ImageProcessing.Denoise")
    assert not parser.has_section("Denoise")

    # Ensure all keys are directly in [ImageProcessing]
    assert parser.has_section("ImageProcessing")
    assert parser.getboolean("ImageProcessing", "DenoiseEnabled") is True
    assert parser.get("ImageProcessing", "DenoiseMethod") == "nlmeans"
    assert parser.getint("ImageProcessing", "DenoiseDiameter") == 7
    assert parser.getfloat("ImageProcessing", "DenoiseSigmaColor") == 65.0
    assert parser.getfloat("ImageProcessing", "DenoiseSigmaSpace") == 70.0
    assert parser.getfloat("ImageProcessing", "DenoiseStrength") == 4.5
    assert parser.getint("ImageProcessing", "DenoiseTemplateWindow") == 5
    assert parser.getint("ImageProcessing", "DenoiseSearchWindow") == 19
    assert parser.getboolean("ImageProcessing", "DenoiseApplyToCutImages") is True

    # Deserialize back from INI string
    reloaded_config = Config()
    load_config_from_parser(reloaded_config, parser)
    assert reloaded_config.image_processing.denoise.enabled is True
    assert reloaded_config.image_processing.denoise.method == "nlmeans"
    assert reloaded_config.image_processing.denoise.diameter == 7
    assert reloaded_config.image_processing.denoise.sigma_color == 65.0
    assert reloaded_config.image_processing.denoise.sigma_space == 70.0
    assert reloaded_config.image_processing.denoise.strength == 4.5
    assert reloaded_config.image_processing.denoise.template_window == 5
    assert reloaded_config.image_processing.denoise.search_window == 19
    assert reloaded_config.image_processing.denoise.apply_to_cut_images is True
