"""Unit tests for ROI placement and bounding box drawing steps in Setup Wizard."""

from unittest.mock import MagicMock, patch

from data_classes import ImagePosition, RefImage
from gui.wizard.steps.draw_analog_rois import DrawAnalogRoisStep
from gui.wizard.steps.draw_digital_rois import DrawDigitalRoisStep
from gui.wizard.steps.draw_refs import DrawRefsStep
from gui.wizard.steps.draw_rois_base import DrawRoisBaseStep, Roi


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
    with patch("gui.wizard.steps.draw_rois_base.ui") as mock_ui:
        mock_bar = MagicMock()
        mock_bar._classes = ["roi-shortcut-bar"]
        mock_ui.row.return_value.classes.return_value.__enter__.return_value = mock_bar
        bar = step.build_shortcuts_bar()
        assert bar is not None
        assert "roi-shortcut-bar" in bar._classes


def test_digital_roi_inner_box_twenty_percent_border():
    """Verify that DrawDigitalRoisStep._draw_roi_func creates an inner box with 20% border on all sides."""
    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    x, y, w, h = 100, 200, 50, 100
    svg = step._draw_roi_func(x, y, w, h, "red", "digit1")

    # Outer rect: x=100, y=200, width=50, height=100
    assert f'<rect x="{x}" y="{y}" width="{w}" height="{h}"' in svg

    # Inner rect: border is 20% of width (50*0.2 = 10) and 20% of height (100*0.2 = 20)
    # inner_x = 100 + 10 = 110.0
    # inner_y = 200 + 20 = 220.0
    # inner_w = 50 - 20 = 30.0 (leaves 10px on left, 10px on right -> 20% on each side)
    # inner_h = 100 - 40 = 60.0 (leaves 20px on top, 20px on bottom -> 20% on each side)
    expected_inner_x = x + w * 0.2  # 110.0
    expected_inner_y = y + h * 0.2  # 220.0
    expected_inner_w = w - w * 0.4  # 30.0
    expected_inner_h = h - h * 0.4  # 60.0
    assert (
        f'<rect x="{expected_inner_x}" y="{expected_inner_y}" width="{expected_inner_w}" height="{expected_inner_h}"'
        in svg
    )

    # Center horizontal dividing line across the inner box at y + h/2
    assert (
        f'<line x1="{expected_inner_x}" y1="{y + h / 2}" x2="{x + w - w * 0.2}" y2="{y + h / 2}"'
        in svg
    )


def test_digital_roi_sizing_guide_dialog():
    """Verify that _open_sizing_guide_dialog displays the visual sizing guide image and opens dialog."""
    from unittest.mock import patch

    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    with patch("gui.wizard.steps.draw_digital_rois.ui") as mock_ui:
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        step._open_sizing_guide_dialog()

        mock_dialog.open.assert_called_once()
        # Verify the visual illustration image was loaded
        mock_ui.image.assert_called_once_with("/static/images/ROI_drawing.jpg")


def test_draw_rois_keyboard_nudging_and_resizing():
    from gui.wizard.steps.draw_digital_rois import DrawDigitalRoisStep

    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    with patch("gui.wizard.steps.draw_rois_base.ui"):
        step.load_rois([ImagePosition(name="digit1", x=100, y=100, w=50, h=80)])
        assert len(step.rois) == 1
        roi = step.rois[0]

        # Arrow keys nudging (1px default)
        assert step.handle_keyboard_event("ArrowUp", shift=False) is True
        assert roi.y == 99

        assert step.handle_keyboard_event("ArrowDown", shift=False) is True
        assert roi.y == 100

        assert step.handle_keyboard_event("ArrowLeft", shift=False) is True
        assert roi.x == 99

        assert step.handle_keyboard_event("ArrowRight", shift=False) is True
        assert roi.x == 100

        # Arrow keys with Shift (10px step)
        assert step.handle_keyboard_event("ArrowUp", shift=True) is True
        assert roi.y == 90

        assert step.handle_keyboard_event("ArrowLeft", shift=True) is True
        assert roi.x == 90

        assert step.handle_keyboard_event("ArrowDown", shift=True) is True
        assert roi.y == 100

        assert step.handle_keyboard_event("ArrowRight", shift=True) is True
        assert roi.x == 100

        # Resize + and -
        assert step.handle_keyboard_event("+", shift=False) is True
        assert roi.w == 51 and roi.h == 81

        assert step.handle_keyboard_event("-", shift=False) is True
        assert roi.w == 50 and roi.h == 80

        assert step.handle_keyboard_event("=", shift=True) is True
        assert roi.w == 60 and roi.h == 90

        assert step.handle_keyboard_event("_", shift=True) is True
        assert roi.w == 50 and roi.h == 80

        # Unknown key returns False
        assert step.handle_keyboard_event("Escape") is False

        # No enabled ROIs returns False
        roi.enabled = False
        assert step.handle_keyboard_event("ArrowUp") is False


def test_draw_rois_keyboard_delete_and_duplicate():
    from gui.wizard.steps.draw_digital_rois import DrawDigitalRoisStep

    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    with patch("gui.wizard.steps.draw_rois_base.ui"):
        step.load_rois([ImagePosition(name="digit1", x=100, y=100, w=50, h=80)])

        # Duplicate via Ctrl+D
        res = step.handle_keyboard_event("d", ctrl=True)
        assert res is True
        assert len(step.rois) == 2
        dup = step.rois[1]
        assert dup.name == "digit2"
        assert dup.x == 100 + 50 + 2
        assert dup.y == 100
        assert dup.w == 50
        assert dup.h == 80
        assert dup.enabled is True

        # Delete via Delete key
        assert step.handle_keyboard_event("Delete") is True
        assert len(step.rois) == 1
        assert step.rois[0].name == "digit1"


def test_draw_rois_base_zoom_controls():
    """Verify zoom buttons invoke zoom_callback with expected delta/zoom/fit."""
    mock_zoom_cb = MagicMock()
    mock_get_text = MagicMock(return_value="150%")
    step = DrawRoisBaseStep(
        name="Test",
        name_template="roi_",
        set_image_callback=MagicMock(),
        draw_roi_func=MagicMock(return_value="<svg></svg>"),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        zoom_callback=mock_zoom_cb,
        get_zoom_text=mock_get_text,
    )
    # Test _zoom_in
    step._zoom_in()
    mock_zoom_cb.assert_called_with(delta=0.25)

    # Test _zoom_out
    step._zoom_out()
    mock_zoom_cb.assert_called_with(delta=-0.25)

    # Test _zoom_1_1
    step._zoom_1_1()
    mock_zoom_cb.assert_called_with(zoom=1.0)

    # Test _zoom_fit
    step._zoom_fit()
    mock_zoom_cb.assert_called_with(fit=True)

    # Test update_zoom_display
    step.step_zoom_label = MagicMock()
    step.update_zoom_display("200%")
    assert step.step_zoom_label.text == "200%"
