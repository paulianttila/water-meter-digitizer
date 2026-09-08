from unittest.mock import MagicMock
from data_classes import ImagePosition, RefImage
from gui.step_draw_analog_rois import DrawAnalogRoisStep
from gui.step_draw_digital_rois import DrawDigitalRoisStep
from gui.step_draw_refs import DrawRefsStep
from gui.step_draw_rois_base import DrawRoisBaseStep, Roi


def test_draw_rois_base_load_rois_syncs_select_all():
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    step.select_all = MagicMock()
    step.select_all.value = False

    items = [
        ImagePosition(name="digit1", x=10, y=10, w=20, h=30),
        ImagePosition(name="digit2", x=35, y=10, w=20, h=30),
    ]
    step.load_rois(items)

    assert len(step.rois) == 2
    assert all(r.enabled for r in step.rois)
    assert step.select_all.value is True


def test_draw_rois_base_select_all_toggle():
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    step.select_all = MagicMock()
    step.rois = [
        Roi(name="roi1", enabled=True, x=0, y=0, w=10, h=10),
        Roi(name="roi2", enabled=True, x=20, y=0, w=10, h=10),
    ]

    # Toggle select all off
    step.select_all.value = False
    step._select_all_rois()
    assert all(not r.enabled for r in step.rois)

    # Toggle select all on
    step.select_all.value = True
    step._select_all_rois()
    assert all(r.enabled for r in step.rois)


def test_draw_rois_base_individual_roi_change_syncs_select_all():
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    step.select_all = MagicMock()
    step.select_all.value = True
    step.rois = [
        Roi(name="roi1", enabled=True, x=0, y=0, w=10, h=10),
        Roi(name="roi2", enabled=True, x=20, y=0, w=10, h=10),
    ]

    # Uncheck one ROI
    step.rois[0].enabled = False
    step._on_roi_enabled_change()
    assert step.select_all.value is False

    # Check it back
    step.rois[0].enabled = True
    step._on_roi_enabled_change()
    assert step.select_all.value is True


def test_digital_and_analog_step_classes_inherit_select_all_sync():
    digital_step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    digital_step.select_all = MagicMock()
    digital_step.select_all.value = False
    digital_step.load_rois([ImagePosition(name="d1", x=10, y=10, w=20, h=30)])
    assert digital_step.select_all.value is True

    analog_step = DrawAnalogRoisStep(
        name="Analog",
        name_template="dial",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    analog_step.select_all = MagicMock()
    analog_step.select_all.value = False
    analog_step.load_rois([ImagePosition(name="a1", x=10, y=10, w=20, h=30)])
    assert analog_step.select_all.value is True

    refs_step = DrawRefsStep(
        name="Refs",
        name_template="ref",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    refs_step.select_all = MagicMock()
    refs_step.select_all.value = False
    refs_step.load_from_config([RefImage(name="r1", x=10, y=10, w=20, h=30)])
    assert refs_step.select_all.value is True
