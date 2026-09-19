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


def test_draw_digital_and_analog_rois_load_model_with_spaces():
    from configuration import CNNParams

    # Test digital model with spaces around slashes
    digital_step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        digital_models_dir="/config/neuralnets/digital",
    )
    digital_step.cnn_file = MagicMock()
    digital_step.cnn_file.options = {
        "/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite": "class11 / dig-class11_1600_s2.tflite",
        "/config/neuralnets/digital/class100/dig-class100_0168_s2_q.tflite": "class100 / dig-class100_0168_s2_q.tflite",
    }
    digital_step.cnn_type = MagicMock()

    params = CNNParams(
        enabled=True,
        model="auto",
        model_file="${DigitalModelsDir}/class11 / dig-class11_1600_s2.tflite",
        cut_images=[],
    )
    digital_step.load_from_config(params)
    assert (
        digital_step.cnn_file.value
        == "/config/neuralnets/digital/class11/dig-class11_1600_s2.tflite"
    )

    # Test analog model with spaces around slashes
    analog_step = DrawAnalogRoisStep(
        name="Analog",
        name_template="analog",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        analog_models_dir="/config/neuralnets/analog",
    )
    analog_step.cnn_file = MagicMock()
    analog_step.cnn_file.options = {
        "/config/neuralnets/analog/continuous/ana-cont_1209_s2.tflite": "continuous / ana-cont_1209_s2.tflite"
    }
    analog_step.cnn_type = MagicMock()

    params_analog = CNNParams(
        enabled=True,
        model="auto",
        model_file="${AnalogModelsDir}/continuous / ana-cont_1209_s2.tflite",
        cut_images=[],
    )
    analog_step.load_from_config(params_analog)
    assert (
        analog_step.cnn_file.value
        == "/config/neuralnets/analog/continuous/ana-cont_1209_s2.tflite"
    )


def test_draw_rois_base_shift_move_single_roi():
    """Verify that Shift+drag moves an enabled ROI without altering width or height."""
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    roi = Roi(name="roi1", enabled=True, x=10, y=20, w=30, h=40)
    step.rois = [roi]

    down_ev = MagicMock(type="mousedown", image_x=15, image_y=25, shift=True)
    step.mouse_event(down_ev)
    assert step.is_moving is True

    move_ev = MagicMock(type="mousemove", image_x=35, image_y=55, shift=True)
    step.mouse_event(move_ev)
    assert roi.x == 30  # 10 + (35 - 15)
    assert roi.y == 50  # 20 + (55 - 25)
    assert roi.w == 30
    assert roi.h == 40

    up_ev = MagicMock(type="mouseup", image_x=35, image_y=55, shift=True)
    step.mouse_event(up_ev)
    assert step.is_moving is False
    assert roi.x == 30
    assert roi.y == 50
    assert roi.w == 30
    assert roi.h == 40


def test_draw_rois_base_shift_move_multiple_rois():
    """Verify that Shift+drag translates all enabled ROIs together in unison."""
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    roi1 = Roi(name="roi1", enabled=True, x=10, y=20, w=30, h=40)
    roi2 = Roi(name="roi2", enabled=True, x=100, y=200, w=50, h=60)
    roi3 = Roi(name="roi3", enabled=False, x=300, y=300, w=50, h=50)  # Disabled
    step.rois = [roi1, roi2, roi3]

    down_ev = MagicMock(type="mousedown", image_x=50, image_y=50, shift=True)
    step.mouse_event(down_ev)

    move_ev = MagicMock(type="mousemove", image_x=60, image_y=70, shift=True)
    step.mouse_event(move_ev)

    up_ev = MagicMock(type="mouseup", image_x=60, image_y=70, shift=True)
    step.mouse_event(up_ev)

    # roi1 moved by dx=+10, dy=+20
    assert roi1.x == 20
    assert roi1.y == 40
    assert roi1.w == 30
    assert roi1.h == 40

    # roi2 moved by dx=+10, dy=+20
    assert roi2.x == 110
    assert roi2.y == 220
    assert roi2.w == 50
    assert roi2.h == 60

    # roi3 remained untouched
    assert roi3.x == 300
    assert roi3.y == 300


def test_draw_rois_base_shift_move_clamps_to_zero():
    """Verify that moving an ROI past top-left image boundaries clamps at (0, 0)."""
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    roi = Roi(name="roi1", enabled=True, x=15, y=15, w=30, h=40)
    step.rois = [roi]

    down_ev = MagicMock(type="mousedown", image_x=50, image_y=50, shift=True)
    step.mouse_event(down_ev)

    # Move far to the top-left (-100, -100 delta)
    move_ev = MagicMock(type="mousemove", image_x=-50, image_y=-50, shift=True)
    step.mouse_event(move_ev)

    up_ev = MagicMock(type="mouseup", image_x=-50, image_y=-50, shift=True)
    step.mouse_event(up_ev)

    assert roi.x == 0
    assert roi.y == 0
    assert roi.w == 30
    assert roi.h == 40


def test_draw_rois_base_shift_move_autoselects_unselected_roi():
    """Verify that clicking inside an unenabled ROI while holding Shift auto-selects and moves it."""
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    roi = Roi(name="roi1", enabled=False, x=50, y=50, w=40, h=40)
    step.rois = [roi]

    # Click inside roi at (60, 60) with Shift
    down_ev = MagicMock(type="mousedown", image_x=60, image_y=60, shift=True)
    step.mouse_event(down_ev)

    assert roi.enabled is True
    assert step.is_moving is True

    # Drag by (+20, +15)
    move_ev = MagicMock(type="mousemove", image_x=80, image_y=75, shift=True)
    step.mouse_event(move_ev)

    up_ev = MagicMock(type="mouseup", image_x=80, image_y=75, shift=True)
    step.mouse_event(up_ev)

    assert roi.x == 70
    assert roi.y == 65
    assert roi.w == 40
    assert roi.h == 40


def test_draw_rois_base_build_shortcuts_bar():
    """Verify that build_shortcuts_bar returns a styled row element containing shortcut classes."""
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    bar = step.build_shortcuts_bar()
    assert bar is not None
    classes = " ".join(bar._classes)
    assert "roi-shortcut-bar" in classes
