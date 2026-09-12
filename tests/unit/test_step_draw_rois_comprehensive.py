"""Comprehensive unit tests for DrawRoisBaseStep, DrawDigitalRoisStep, DrawAnalogRoisStep, and StepDrawRefs."""

import asyncio
from unittest.mock import MagicMock, patch

from configuration import CNNParams
from data_classes import ImagePosition
from gui.step_draw_analog_rois import DrawAnalogRoisStep
from gui.step_draw_digital_rois import DrawDigitalRoisStep
from gui.step_draw_refs import DrawRefsStep
from gui.step_draw_rois_base import DrawRoisBaseStep
from processor.digitizer import ReadoutResult


def test_draw_rois_base_alignments_and_resizing():
    set_img = MagicMock()
    draw_roi = MagicMock(return_value="<rect />")
    set_svg = MagicMock()
    show_temp = MagicMock()

    step = DrawRoisBaseStep(
        name="ROIs",
        name_template="roi",
        set_image_callback=set_img,
        draw_roi_func=draw_roi,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
    )

    items = [
        ImagePosition(name="roi1", x=10, y=20, w=30, h=40),
        ImagePosition(name="roi2", x=50, y=30, w=35, h=45),
        ImagePosition(name="roi3", x=90, y=10, w=25, h=35),
    ]

    with patch("gui.step_draw_rois_base.ui"):
        step.load_rois(items)
        assert len(step.rois) == 3

        # Test Align Top
        step._align_top()
        assert step.rois[0].y == 20
        assert step.rois[1].y == 20
        assert step.rois[2].y == 20

        # Test Align Left
        step._align_left()
        assert step.rois[0].x == 10
        assert step.rois[1].x == 10
        assert step.rois[2].x == 10

        # Test Align Bottom
        step._align_bottom()
        assert step.rois[0].y == step.rois[1].y + (step.rois[1].h - step.rois[0].h)

        # Test Align Right
        step._align_right()
        assert step.rois[0].x == step.rois[1].x + (step.rois[1].w - step.rois[0].w)

        # Test Align Center
        step._align_center()

        # Test Resize All
        step._resize_all()
        assert step.rois[1].w == step.rois[0].w
        assert step.rois[1].h == step.rois[0].h
        assert step.rois[2].w == step.rois[0].w
        assert step.rois[2].h == step.rois[0].h

        # Test Distribute Horizontally
        step.rois[0].x = 0
        step.rois[1].x = 40
        step.rois[2].x = 100
        step._distribute_horizontally()
        assert step.rois[1].x == 50


def test_draw_rois_base_mouse_events_and_roi_ops():
    set_img = MagicMock()
    draw_roi = MagicMock(return_value="<rect />")
    set_svg = MagicMock()
    show_temp = MagicMock()

    step = DrawRoisBaseStep(
        name="ROIs",
        name_template="roi",
        set_image_callback=set_img,
        draw_roi_func=draw_roi,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
    )

    with patch("gui.step_draw_rois_base.ui"):
        step.load_rois([ImagePosition(name="roi1", x=10, y=10, w=20, h=20)])

        # Simulate Mouse Down
        ev_down = MagicMock(type="mousedown", image_x=15, image_y=15)
        step.mouse_event(ev_down)
        assert step.draw_on is True

        # Simulate Mouse Move
        ev_move = MagicMock(type="mousemove", image_x=35, image_y=45)
        step.mouse_event(ev_move)
        show_temp.assert_called()

        # Simulate Mouse Up
        ev_up = MagicMock(type="mouseup", image_x=40, image_y=50)
        step.mouse_event(ev_up)
        assert step.draw_on is False
        assert step.rois[0].w == 25
        assert step.rois[0].h == 35

        # Test Create New ROI
        new_roi = step._create_new_roi()
        assert new_roi.name == "roi2"
        assert new_roi.enabled is True

        # Test Unselect All ROIs
        step._unselect_all_rois()
        assert all(not r.enabled for r in step.rois)

        # Test Add ROI
        step.container = MagicMock()
        step._add_roi()
        assert len(step.rois) == 2

        # Test Remove ROI
        step._remove_roi()
        assert len(step.rois) == 1

        # Test Delete specific ROI
        row_elem = MagicMock()
        step._delete_roi(step.rois[0], row_elem)
        assert len(step.rois) == 0


def test_step_draw_digital_and_analog_rois():
    set_img = MagicMock()
    set_svg = MagicMock()
    show_temp = MagicMock()

    digital_step = DrawDigitalRoisStep(
        name="Digital ROIs",
        name_template="digit",
        set_image_callback=set_img,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
        digital_models_dir="/models",
    )

    analog_step = DrawAnalogRoisStep(
        name="Analog ROIs",
        name_template="analog",
        set_image_callback=set_img,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
        analog_models_dir="/models",
    )

    assert "<rect" in digital_step._draw_roi_func(10, 10, 20, 30, "blue", "digit1")
    assert "<line" in analog_step._draw_roi_func(10, 10, 20, 30, "green", "analog1")

    # Test load from config
    params = CNNParams(
        enabled=True,
        model="digital",
        model_file="dig.tflite",
        cut_images=[ImagePosition(name="digit1", x=1, y=2, w=3, h=4)],
    )
    digital_step.cnn_type = MagicMock()
    digital_step.cnn_file = MagicMock(options={"dig.tflite": "dig.tflite"})
    digital_step.load_from_config(params)
    assert len(digital_step.rois) == 1

    analog_params = CNNParams(
        enabled=True,
        model="analog",
        model_file="ana.tflite",
        cut_images=[ImagePosition(name="analog1", x=1, y=2, w=3, h=4)],
    )
    analog_step.cnn_type = MagicMock()
    analog_step.cnn_file = MagicMock(options={"ana.tflite": "ana.tflite"})
    analog_step.load_from_config(analog_params)
    assert len(analog_step.rois) == 1


def test_show_digits_and_analogs_execution():
    digital_step = DrawDigitalRoisStep(
        name="Digital ROIs",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        digital_models_dir="/models",
    )
    digital_step.cnn_file = MagicMock(value="model.tflite")
    digital_step.test_result_container = MagicMock()
    digital_step.time = MagicMock()

    with (
        patch.object(digital_step, "_cut_images", return_value=[]),
        patch("gui.step_draw_digital_rois.DigitizerProcessor") as MockProc,
        patch("gui.step_draw_digital_rois.ui") as mock_ui,
    ):
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.element.return_value.__enter__ = MagicMock()
        mock_ui.element.return_value.__exit__ = MagicMock()

        mock_instance = MockProc.return_value
        mock_instance.init_digital_model.return_value = mock_instance
        mock_instance.execute_digital_cnn.return_value = mock_instance
        mock_instance.evaluate_cnn_results.return_value = mock_instance
        mock_instance.cnn_digital_results = [
            ReadoutResult(name="digit1", value=5.0, model="dig", confidence=95.0)
        ]

        digital_step._show_digits()
        digital_step.test_result_container.clear.assert_called_once()
        assert "⏱" in digital_step.time.text

    # Test analog show
    analog_step = DrawAnalogRoisStep(
        name="Analog ROIs",
        name_template="analog",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        analog_models_dir="/models",
    )
    analog_step.cnn_file = MagicMock(value="ana_model.tflite")
    analog_step.test_result_container = MagicMock()
    analog_step.time = MagicMock()

    with (
        patch.object(analog_step, "_cut_images", return_value=[]),
        patch("gui.step_draw_analog_rois.DigitizerProcessor") as MockProcA,
        patch("gui.step_draw_analog_rois.ui") as mock_ui_a,
    ):
        mock_ui_a.row.return_value.__enter__ = MagicMock()
        mock_ui_a.row.return_value.__exit__ = MagicMock()
        mock_ui_a.element.return_value.__enter__ = MagicMock()
        mock_ui_a.element.return_value.__exit__ = MagicMock()

        mock_inst_a = MockProcA.return_value
        mock_inst_a.init_analog_model.return_value = mock_inst_a
        mock_inst_a.execute_analog_cnn.return_value = mock_inst_a
        mock_inst_a.evaluate_cnn_results.return_value = mock_inst_a
        mock_inst_a.cnn_analog_results = [
            ReadoutResult(name="analog1", value=3.2, model="ana", confidence=92.0)
        ]

        analog_step._show_analogs()
        analog_step.test_result_container.clear.assert_called_once()
        assert "⏱" in analog_step.time.text


def test_step_draw_refs_show():
    set_img = MagicMock()
    set_svg = MagicMock()
    show_temp = MagicMock()

    refs_step = DrawRefsStep(
        name="References",
        name_template="ref",
        set_image_callback=set_img,
        set_rois_to_svg_func=set_svg,
        show_temp_draw_in_svg_func=show_temp,
    )

    with (
        patch("gui.step_draw_refs.ui") as mock_ui,
        patch("gui.step_base.ui") as mock_base_ui,
    ):
        mock_ui.step.return_value.__enter__ = MagicMock()
        mock_ui.step.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_base_ui.expansion.return_value.__enter__ = MagicMock()
        mock_base_ui.expansion.return_value.__exit__ = MagicMock()
        mock_base_ui.column.return_value.__enter__ = MagicMock()
        mock_base_ui.column.return_value.__exit__ = MagicMock()

        stepper = MagicMock()
        asyncio.run(refs_step.show(stepper))
        assert refs_step.select_all is not None


def test_step_draw_digital_and_analog_show():
    digital_step = DrawDigitalRoisStep(
        name="Digital ROIs",
        name_template="digit",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        digital_models_dir="/models",
    )
    analog_step = DrawAnalogRoisStep(
        name="Analog ROIs",
        name_template="analog",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        analog_models_dir="/models",
    )

    with (
        patch("gui.step_draw_digital_rois.ui") as mock_ui_d,
        patch("gui.step_draw_analog_rois.ui") as mock_ui_a,
        patch("gui.step_base.ui") as mock_base_ui,
        patch.object(digital_step, "_get_cnn_models", return_value={"m1": "m1.tflite"}),
        patch.object(analog_step, "_get_cnn_models", return_value={"a1": "a1.tflite"}),
    ):
        mock_ui_d.step.return_value.__enter__ = MagicMock()
        mock_ui_d.step.return_value.__exit__ = MagicMock()
        mock_ui_d.card.return_value.__enter__ = MagicMock()
        mock_ui_d.card.return_value.__exit__ = MagicMock()
        mock_ui_d.row.return_value.__enter__ = MagicMock()
        mock_ui_d.row.return_value.__exit__ = MagicMock()
        mock_ui_d.column.return_value.__enter__ = MagicMock()
        mock_ui_d.column.return_value.__exit__ = MagicMock()

        mock_ui_a.step.return_value.__enter__ = MagicMock()
        mock_ui_a.step.return_value.__exit__ = MagicMock()
        mock_ui_a.card.return_value.__enter__ = MagicMock()
        mock_ui_a.card.return_value.__exit__ = MagicMock()
        mock_ui_a.row.return_value.__enter__ = MagicMock()
        mock_ui_a.row.return_value.__exit__ = MagicMock()
        mock_ui_a.column.return_value.__enter__ = MagicMock()
        mock_ui_a.column.return_value.__exit__ = MagicMock()

        mock_base_ui.expansion.return_value.__enter__ = MagicMock()
        mock_base_ui.expansion.return_value.__exit__ = MagicMock()
        mock_base_ui.column.return_value.__enter__ = MagicMock()
        mock_base_ui.column.return_value.__exit__ = MagicMock()

        stepper = MagicMock()
        asyncio.run(digital_step.show(stepper))
        asyncio.run(analog_step.show(stepper))
        assert digital_step.cnn_file is not None
        assert analog_step.cnn_file is not None
