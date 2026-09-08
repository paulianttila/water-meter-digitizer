import asyncio
from unittest.mock import MagicMock, patch
from gui.step_draw_digital_rois import DrawDigitalRoisStep
from gui.step_draw_analog_rois import DrawAnalogRoisStep
from gui.step_draw_rois_base import Roi
from processor.digitizer import ReadoutResult


def test_digital_rois_benchmark_dialog_no_image():
    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="Digital",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    step.image = ""
    with patch("nicegui.ui.notify") as mock_notify:
        asyncio.run(step._benchmark_models())
        mock_notify.assert_called_with(
            "Please load an image first to run benchmarks", type="warning"
        )


def test_digital_rois_benchmark_dialog_no_rois():
    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="Digital",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    step.image = "sample_base64"
    step.rois = []
    with patch("nicegui.ui.notify") as mock_notify:
        asyncio.run(step._benchmark_models())
        mock_notify.assert_called_with(
            "Please define at least one ROI to run benchmarks", type="warning"
        )


def test_digital_rois_benchmark_success_flow():
    step = DrawDigitalRoisStep(
        name="Digital",
        name_template="Digital",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        digital_models_dir="/dummy/models",
    )
    step.image = "sample_base64"
    step.rois = [Roi(enabled=True, name="digit1", x=10, y=10, w=20, h=30)]
    step.cnn_type = MagicMock(value="auto")
    step.cnn_file = MagicMock(value="")

    mock_models = {
        "/dummy/models/model_a.tflite": "model_a.tflite",
        "/dummy/models/model_b.tflite": "model_b.tflite",
    }

    mock_cut_1 = MagicMock()
    mock_cut_1.name = "digit1"
    mock_cuts = [mock_cut_1]

    with (
        patch.object(step, "_get_cnn_models", return_value=mock_models),
        patch.object(step, "_cut_images", return_value=mock_cuts),
        patch.object(step, "_get_base64_image_by_name", return_value="dummy_b64"),
        patch("gui.dialog_benchmark.DigitizerProcessor") as mock_dp_cls,
        patch("nicegui.ui.dialog") as mock_dialog,
        patch("nicegui.ui.card"),
        patch("nicegui.ui.row"),
        patch("nicegui.ui.column"),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.button"),
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.image"),
        patch("nicegui.ui.html"),
        patch("nicegui.ui.element"),
    ):
        mock_dp = MagicMock()
        mock_dp.init_digital_model.return_value = mock_dp
        mock_dp.execute_digital_cnn.return_value = mock_dp
        mock_dp.evaluate_cnn_results.return_value = mock_dp
        mock_dp.cnn_digital_results = [
            ReadoutResult(name="digit1", value=4.0, model="digital100", confidence=98.5)
        ]
        mock_dp_cls.return_value = mock_dp

        mock_instance = MagicMock()
        mock_dialog.return_value.__enter__.return_value = mock_instance

        asyncio.run(step._benchmark_models())

        mock_instance.open.assert_called_once()


def test_analog_rois_benchmark_success_flow():
    step = DrawAnalogRoisStep(
        name="Analog",
        name_template="Analog",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
        analog_models_dir="/dummy/analog_models",
    )
    step.image = "sample_base64"
    step.rois = [Roi(enabled=True, name="analog1", x=10, y=10, w=30, h=30)]
    step.cnn_type = MagicMock(value="auto")
    step.cnn_file = MagicMock(value="")

    mock_models = {
        "/dummy/analog_models/analog_a.tflite": "analog_a.tflite",
    }
    mock_cut_1 = MagicMock()
    mock_cut_1.name = "analog1"
    mock_cuts = [mock_cut_1]

    with (
        patch.object(step, "_get_cnn_models", return_value=mock_models),
        patch.object(step, "_cut_images", return_value=mock_cuts),
        patch.object(step, "_get_base64_image_by_name", return_value="dummy_b64"),
        patch("gui.dialog_benchmark.DigitizerProcessor") as mock_dp_cls,
        patch("nicegui.ui.dialog") as mock_dialog,
        patch("nicegui.ui.card"),
        patch("nicegui.ui.row"),
        patch("nicegui.ui.column"),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.button"),
        patch("nicegui.ui.icon"),
        patch("nicegui.ui.image"),
        patch("nicegui.ui.html"),
        patch("nicegui.ui.element"),
    ):
        mock_dp = MagicMock()
        mock_dp.init_analog_model.return_value = mock_dp
        mock_dp.execute_analog_cnn.return_value = mock_dp
        mock_dp.evaluate_cnn_results.return_value = mock_dp
        mock_dp.cnn_analog_results = [
            ReadoutResult(name="analog1", value=2.5, model="analog", confidence=99.1)
        ]
        mock_dp_cls.return_value = mock_dp

        mock_instance = MagicMock()
        mock_dialog.return_value.__enter__.return_value = mock_instance

        asyncio.run(step._benchmark_models())

        mock_instance.open.assert_called_once()
