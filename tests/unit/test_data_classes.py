"""Unit tests for data classes and model validation."""

import pytest
from pydantic import ValidationError

from data_classes import CutImageOptions


def test_cut_image_options_defaults():
    opts = CutImageOptions()
    assert opts.autocontrast is False
    assert opts.cutoff_low == 2.0
    assert opts.cutoff_high == 45.0
    assert opts.ignore == 2
    assert opts.glare_suppression is False
    assert opts.glare_mode == "clahe"
    assert opts.glare_inpaint_threshold == 230
    assert opts.glare_inpaint_radius == 3
    assert opts.glare_clahe_clip_limit == 2.0
    assert opts.glare_clahe_grid_size == 8
    assert opts.unsharp is False
    assert opts.unsharp_radius == 1.0
    assert opts.unsharp_amount == 1.5
    assert opts.unsharp_threshold == 3


def test_cut_image_options_valid_custom():
    opts = CutImageOptions(
        cutoff_low=5.5,
        cutoff_high=35.0,
        ignore=None,
        glare_clahe_grid_size=16,
        glare_clahe_clip_limit=3.5,
        glare_inpaint_radius=5,
        unsharp_radius=2.0,
    )
    assert opts.cutoff_low == 5.5
    assert opts.cutoff_high == 35.0
    assert opts.ignore is None
    assert opts.glare_clahe_grid_size == 16


@pytest.mark.parametrize(
    "field,value",
    [
        ("cutoff_low", -1),
        ("cutoff_low", 101),
        ("cutoff_high", -1),
        ("cutoff_high", 101),
        ("ignore", -1),
        ("ignore", 256),
        ("glare_inpaint_threshold", -1),
        ("glare_inpaint_threshold", 256),
        ("glare_inpaint_radius", 0),
        ("glare_inpaint_radius", 51),
        ("glare_clahe_clip_limit", 0.05),
        ("glare_clahe_clip_limit", 45.0),
        ("glare_clahe_grid_size", 0),
        ("glare_clahe_grid_size", 65),
        ("unsharp_radius", 0.05),
        ("unsharp_radius", 25.0),
        ("unsharp_amount", -0.5),
        ("unsharp_amount", 15.0),
        ("unsharp_threshold", -1),
        ("unsharp_threshold", 256),
    ],
)
def test_cut_image_options_out_of_bounds(field, value):
    with pytest.raises(ValidationError):
        CutImageOptions(**{field: value})


def test_cut_image_options_cutoff_sum_exceeds_100():
    with pytest.raises(ValidationError, match="must be less than 100"):
        CutImageOptions(cutoff_low=60, cutoff_high=45)

    with pytest.raises(ValidationError, match="must be less than 100"):
        CutImageOptions(cutoff_low=50, cutoff_high=50)
