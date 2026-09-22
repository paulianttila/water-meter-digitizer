"""Unit tests for DigitizerProcessor and post-processing evaluation."""

from unittest.mock import MagicMock, patch

import pytest

from src.cnn.base import ModelDetails
from src.cnn.digital_counter_cnn import DigitalCounterCNN
from src.processor.digitizer import (
    MODEL_ANALOG,
    MODEL_ANALOG100,
    MODEL_DIGITAL,
    MODEL_DIGITAL100,
    DigitizerProcessor,
    FormatParser,
    Meter,
    MeterConfig,
    ReadoutResult,
)


def test_solve_model_analog() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=32, ysize=32, channels=3, num_outputs=2
    )
    assert DigitizerProcessor()._solve_model("auto", details) == MODEL_ANALOG


def test_solve_model_digital() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=32, ysize=32, channels=3, num_outputs=11
    )
    assert DigitizerProcessor()._solve_model("auto", details) == MODEL_DIGITAL


def test_solve_model_analog100() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=32, ysize=32, channels=3, num_outputs=100
    )
    assert DigitizerProcessor()._solve_model("auto", details) == MODEL_ANALOG100


def test_solve_model_digital100() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=20, ysize=20, channels=3, num_outputs=100
    )
    assert DigitizerProcessor()._solve_model("auto", details) == MODEL_DIGITAL100


def test_solve_model_empty() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=20, ysize=20, channels=3, num_outputs=0
    )
    with pytest.raises(ValueError):
        DigitizerProcessor()._solve_model("auto", details)


def test_solve_model_non_auto() -> None:
    details = ModelDetails(
        name="test.tflite", xsize=32, ysize=32, channels=3, num_outputs=0
    )
    assert (
        DigitizerProcessor()._solve_model(MODEL_ANALOG100, details) == MODEL_ANALOG100
    )


@pytest.mark.parametrize("model", [MODEL_ANALOG, MODEL_ANALOG100])
def test_evaluate_cnn_results_analog_models(model: str) -> None:
    processor = DigitizerProcessor()
    processor.cnn_analog_results = [
        ReadoutResult(name="analog1", value=1.45342, model=model),
        ReadoutResult(name="analog2", value=2.23533, model=model),
        ReadoutResult(name="analog3", value=3.83533, model=model),
        ReadoutResult(name="analog4", value=4.99533, model=model),
        ReadoutResult(name="analog5", value=5.23455, model=model),
        ReadoutResult(name="analog6", value=6.99533, model=model),
        ReadoutResult(name="analog7", value=7.99533, model=model),
        ReadoutResult(name="analog8", value=8.69533, model=model),
        ReadoutResult(name="analog9", value=9.29533, model=model),
    ]
    processor.evaluate_cnn_results()

    assert processor.available_values == {
        "analog1": 1,
        "analog2": 2,
        "analog3": 4,
        "analog4": 5,
        "analog5": 5,
        "analog6": 7,
        "analog7": 8,
        "analog8": 9,
        "analog9": 9,
    }


def test_evaluate_cnn_results_digital() -> None:
    processor = DigitizerProcessor()
    processor.cnn_digital_results = [
        ReadoutResult(name="digital1", value=1, model=MODEL_DIGITAL),
        ReadoutResult(name="digital2", value=2, model=MODEL_DIGITAL),
        ReadoutResult(name="digital3", value=3, model=MODEL_DIGITAL),
        ReadoutResult(name="digital4", value=4, model=MODEL_DIGITAL),
        ReadoutResult(name="digital5", value=5, model=MODEL_DIGITAL),
        ReadoutResult(name="digital6", value=6, model=MODEL_DIGITAL),
        ReadoutResult(name="digital7", value=7, model=MODEL_DIGITAL),
        ReadoutResult(name="digital8", value=8, model=MODEL_DIGITAL),
        ReadoutResult(name="digital9", value=9, model=MODEL_DIGITAL),
    ]
    processor.evaluate_cnn_results()

    assert processor.available_values == {
        "digital1": 1,
        "digital2": 2,
        "digital3": 3,
        "digital4": 4,
        "digital5": 5,
        "digital6": 6,
        "digital7": 7,
        "digital8": 8,
        "digital9": 9,
    }


def test_evaluate_cnn_results_digital100() -> None:
    processor = DigitizerProcessor()
    processor.cnn_digital_results = [
        ReadoutResult(name="digital1", value=1.4, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital2", value=2.5, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital3", value=3.2, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital4", value=4.4, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital5", value=5.2, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital6", value=6.3, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital7", value=7.2, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital8", value=8.1, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital9", value=9.0, model=MODEL_DIGITAL100),
    ]
    processor.evaluate_cnn_results()

    assert processor.available_values == {
        "digital1": 1,
        "digital2": 2,
        "digital3": 3,
        "digital4": 4,
        "digital5": 5,
        "digital6": 6,
        "digital7": 7,
        "digital8": 8,
        "digital9": 9,
    }


def test_evaluate_cnn_results_digital100_up() -> None:
    processor = DigitizerProcessor()
    processor.cnn_digital_results = [
        ReadoutResult(name="digital1", value=1.6, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital2", value=2.6, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital3", value=3.7, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital4", value=4.8, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital5", value=5.9, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital6", value=6.6, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital7", value=7.6, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital8", value=8.7, model=MODEL_DIGITAL100),
        ReadoutResult(name="digital9", value=9.8, model=MODEL_DIGITAL100),
    ]
    processor.evaluate_cnn_results()

    assert processor.available_values == {
        "digital1": 1,
        "digital2": 2,
        "digital3": 3,
        "digital4": 4,
        "digital5": 5,
        "digital6": 6,
        "digital7": 7,
        "digital8": 8,
        "digital9": 9,
    }


def test_evaluate_counters1() -> None:
    processor = DigitizerProcessor()
    values = [
        ReadoutResult(name="analog1", value=0.45, model=MODEL_ANALOG),
        ReadoutResult(name="analog2", value=4.45, model=MODEL_ANALOG),
        ReadoutResult(name="analog3", value=5.03, model=MODEL_ANALOG),
        ReadoutResult(name="analog4", value=2.06, model=MODEL_ANALOG),
    ]

    expected_results = {
        "analog1": "0",
        "analog2": "4",
        "analog3": "5",
        "analog4": "2",
    }
    assert processor._evaluate_counters(values) == expected_results


def get_default_meter() -> Meter:
    return Meter(
        config=MeterConfig(
            name="meter1",
            format="{digit1}{digit2}{digit3}.{analog1}{analog2}{analog3}",
            unit="m3",
            consistency_enabled=True,
            use_extended_resolution=False,
            use_previous_value=True,
            pre_value_from_file_max_age=30,
            allow_negative_rates=False,
            max_rate_value=0.2,
        ),
        name="meter1",
        value="",
        unprocessed_value="",
    )


def get_default_cnn_results() -> dict[str, ReadoutResult]:
    return {
        "digit1": ReadoutResult(name="digit1", value=1, model=MODEL_DIGITAL),
        "digit2": ReadoutResult(name="digit2", value=2, model=MODEL_DIGITAL),
        "digit3": ReadoutResult(name="digit3", value=3, model=MODEL_DIGITAL),
        "analog1": ReadoutResult(name="analog1", value=5.1, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=6.2, model=MODEL_ANALOG),
        "analog3": ReadoutResult(name="analog3", value=7.3, model=MODEL_ANALOG),
    }


def get_default_processor() -> DigitizerProcessor:
    processor = DigitizerProcessor()
    processor.previous_value_file = "test-file.ini"
    return processor


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.450")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_bigger_value(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.567"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.567")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_same_value(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.567"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.366")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_rate_too_high(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    meter.config.max_rate_value = 0.200
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.warning == "Rate too high (0.201)"
    assert meter.valid is False
    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_not_called()


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.564")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_rate_too_high_2l(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    meter.config.max_rate_value = 0.002
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.warning == "Rate too high (0.003)"
    assert meter.valid is False
    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_not_called()


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.568")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_negative_rate(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    meter.config.allow_negative_rates = False
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.warning == "Negative rate (-0.001)"
    assert meter.valid is False
    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_not_called()


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.568")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_allow_negative_rate(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    meter.config.allow_negative_rates = True
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.567"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", side_effect=ValueError)
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_aged_previous_value(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.567"
    assert meter.previous_value == ""
    assert meter.valid is True
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.567"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.451")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_extended_resolution(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    meter.config.use_extended_resolution = True
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.5673"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.5673"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.451")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_prev_val_filling(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    processor = get_default_processor()
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())

    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini", "meter1", "123.567"
    )


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.456")
@patch("src.processor.digitizer.save_previous_value_to_file", return_value=None)
def test_postprocessing_with_prev_val_filling_negative_rate(
    mock_save_previous_value_to_file, mock_load_previous_value_from_file
) -> None:

    meter = get_default_meter()
    processor = get_default_processor()
    cnn_results = {
        "digit1": ReadoutResult(name="digit1", value=10, model=MODEL_DIGITAL),
        "digit2": ReadoutResult(name="digit2", value=10, model=MODEL_DIGITAL),
        "digit3": ReadoutResult(name="digit3", value=2, model=MODEL_DIGITAL),
        "analog1": ReadoutResult(name="analog1", value=5.1, model=MODEL_ANALOG),
        "analog2": ReadoutResult(name="analog2", value=6.2, model=MODEL_ANALOG),
        "analog3": ReadoutResult(name="analog3", value=7.3, model=MODEL_ANALOG),
    }

    processor._postprocess_meter_value(meter, {}, cnn_results)

    assert meter.warning == "Negative rate (-0.889)"
    assert meter.valid is False
    assert meter.value == "122.567"
    mock_load_previous_value_from_file.assert_called_with("test-file.ini", "meter1", 30)
    mock_save_previous_value_to_file.assert_not_called()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.00, "0"),
        (0.49, "0"),
        (0.50, "1"),
        (1.49, "1"),
        (1.50, "2"),
        (2.49, "2"),
        (2.50, "3"),
        (3.49, "3"),
        (3.50, "4"),
        (4.49, "4"),
        (4.50, "5"),
        (5.49, "5"),
        (5.50, "6"),
        (6.49, "6"),
        (6.50, "7"),
        (7.49, "7"),
        (7.50, "8"),
        (8.49, "8"),
        (8.50, "9"),
        (9.49, "9"),
        (9.50, "0"),
    ],
)
def test_evaluate_counters_rounding(value: float, expected: str) -> None:
    processor = DigitizerProcessor()

    values = [
        ReadoutResult(
            name="analog1",
            value=value,
            model=MODEL_ANALOG,
        )
    ]

    assert processor._evaluate_counters(values) == {
        "analog1": expected,
    }


def test_evaluate_counters_analog_values_near_nine() -> None:
    processor = DigitizerProcessor()

    values = [
        ReadoutResult(name="analog1", value=9.48, model=MODEL_ANALOG),
        ReadoutResult(name="analog2", value=9.49, model=MODEL_ANALOG),
        ReadoutResult(name="analog3", value=9.51, model=MODEL_ANALOG),
        ReadoutResult(name="analog4", value=9.99, model=MODEL_ANALOG),
    ]

    result = processor._evaluate_counters(values)

    assert result == {
        "analog1": "9",
        "analog2": "9",
        "analog3": "0",
        "analog4": "0",
    }


@patch("src.processor.digitizer.load_previous_value_from_file")
@patch("src.processor.digitizer.save_previous_value_to_file")
def test_postprocessing_without_previous_value(
    mock_save_previous_value_to_file,
    mock_load_previous_value_from_file,
) -> None:
    meter = get_default_meter()
    meter.config.use_previous_value = False

    processor = get_default_processor()
    processor._postprocess_meter_value(
        meter,
        {},
        get_default_cnn_results(),
    )

    assert meter.value == "123.567"
    mock_load_previous_value_from_file.assert_not_called()
    mock_save_previous_value_to_file.assert_not_called()


@patch(
    "src.processor.digitizer.load_previous_value_from_file",
    return_value="123.366",
)
@patch("src.processor.digitizer.save_previous_value_to_file")
def test_postprocessing_consistency_disabled(
    mock_save_previous_value_to_file,
    mock_load_previous_value_from_file,
) -> None:
    meter = get_default_meter()
    meter.config.consistency_enabled = False
    meter.config.max_rate_value = 0.2

    processor = get_default_processor()

    processor._postprocess_meter_value(
        meter,
        {},
        get_default_cnn_results(),
    )

    assert meter.value == "123.567"

    mock_load_previous_value_from_file.assert_called_once_with(
        "test-file.ini",
        "meter1",
        30,
    )
    mock_save_previous_value_to_file.assert_called_once_with(
        "test-file.ini",
        "meter1",
        "123.567",
    )


@patch(
    "src.processor.digitizer.load_previous_value_from_file",
    return_value="123.367",
)
@patch(
    "src.processor.digitizer.save_previous_value_to_file",
    return_value=None,
)
def test_postprocessing_rate_at_maximum(
    mock_save_previous_value_to_file,
    mock_load_previous_value_from_file,
) -> None:
    meter = get_default_meter()
    meter.config.max_rate_value = 0.2

    processor = get_default_processor()
    processor._postprocess_meter_value(
        meter,
        {},
        get_default_cnn_results(),
    )

    assert meter.value == "123.567"

    mock_load_previous_value_from_file.assert_called_with(
        "test-file.ini",
        "meter1",
        30,
    )
    mock_save_previous_value_to_file.assert_called_with(
        "test-file.ini",
        "meter1",
        "123.567",
    )


@patch(
    "src.processor.digitizer.load_previous_value_from_file",
    return_value="123.567",
)
@patch(
    "src.processor.digitizer.save_previous_value_to_file",
    return_value=None,
)
def test_postprocessing_zero_rate(
    mock_save_previous_value_to_file,
    mock_load_previous_value_from_file,
) -> None:
    meter = get_default_meter()

    processor = get_default_processor()
    processor._postprocess_meter_value(
        meter,
        {},
        get_default_cnn_results(),
    )

    assert meter.value == "123.567"

    mock_save_previous_value_to_file.assert_called_once_with(
        "test-file.ini",
        "meter1",
        "123.567",
    )


def test_evaluate_cnn_results_empty() -> None:
    processor = DigitizerProcessor()
    processor.analog_model = MODEL_ANALOG
    processor.cnn_analog_results = []

    processor.evaluate_cnn_results()

    assert processor.available_values == {}


def test_evaluate_cnn_results_missing_digit() -> None:
    processor = DigitizerProcessor()
    processor.digital_model = MODEL_DIGITAL
    processor.digital_counter_reader = MagicMock(spec=DigitalCounterCNN)

    processor.cnn_digital_results = [
        ReadoutResult(name="digital1", value=1, model=MODEL_DIGITAL),
        ReadoutResult(name="digital3", value=3, model=MODEL_DIGITAL),
    ]

    processor.evaluate_cnn_results()

    assert processor.available_values == {
        "digital1": 1,
        "digital3": 3,
    }


def test_process_async():
    import asyncio

    processor = DigitizerProcessor()
    with patch.object(processor, "process") as mock_proc:
        mock_proc.return_value = MagicMock()
        res = asyncio.run(processor.process_async([], [], []))
        assert res is not None
        mock_proc.assert_called_once_with([], [], [], None, None)


def test_process_uninitialized():
    processor = DigitizerProcessor()
    with pytest.raises(ValueError, match="No CNN reader initialized"):
        processor.process([], [], [])


def test_concurrent_digitizer_process():
    from concurrent.futures import ThreadPoolExecutor

    from PIL import Image

    from data_classes import CutImage

    processor = DigitizerProcessor()
    mock_digital = MagicMock(spec=DigitalCounterCNN)
    mock_digital.get_model_details.return_value = ModelDetails(
        name="test.tflite", xsize=20, ysize=32, channels=3, num_outputs=11
    )
    # Return different values based on image size or name
    mock_digital.readout_with_confidence.side_effect = lambda img: (5.0, 95.0)

    processor.digital_counter_reader = mock_digital
    processor.digital_model = MODEL_DIGITAL

    meter_cfg = MeterConfig(
        name="main",
        format="{digit1}",
        value_names=["digit1"],
        use_previous_value=False,
    )
    test_img = CutImage(name="digit1", image=Image.new("RGB", (20, 32)))

    def worker(idx: int):
        return processor.process([], [test_img], [meter_cfg])

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        results = [f.result() for f in futures]

    assert len(results) == 20
    for r in results:
        assert len(r.meters) == 1
        assert r.meters[0].value == "5"


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="100.0")
@patch("src.processor.digitizer.save_previous_value_to_file")
def test_get_meter_values_with_rate_too_high(mock_save, mock_load) -> None:
    processor = DigitizerProcessor()
    processor.use_previous_value_file("test-prev.ini")
    processor.available_values = {"digit1": 1, "digit2": 5, "digit3": 0}
    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=1, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit2", value=5, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit3", value=0, model=MODEL_DIGITAL, confidence=95.0),
    ]

    meter_cfg = MeterConfig(
        name="total",
        format="{digit1}{digit2}{digit3}",
        value_names=["digit1", "digit2", "digit3"],
        use_previous_value=True,
        consistency_enabled=True,
        max_rate_value=10.0,
    )

    # 150.0 - 100.0 = 50.0 > max_rate_value (10.0)
    result = processor.get_meter_values([meter_cfg])

    assert len(result.meters) == 1
    m = result.meters[0]
    assert m.value == "150"
    assert m.quality == "warning"
    assert m.warning == "Rate too high (50.000)"
    assert m.valid is False
    assert result.valid is False
    assert result.warning == "Rate too high (50.000)"
    assert result.error == ""
    mock_save.assert_not_called()


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="100.0")
@patch("src.processor.digitizer.save_previous_value_to_file")
def test_get_meter_values_valid_success(mock_save, mock_load) -> None:
    processor = DigitizerProcessor()
    processor.use_previous_value_file("test-prev.ini")
    processor.available_values = {"digit1": 1, "digit2": 0, "digit3": 5}
    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=1, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit2", value=0, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit3", value=5, model=MODEL_DIGITAL, confidence=95.0),
    ]

    meter_cfg = MeterConfig(
        name="total",
        format="{digit1}{digit2}{digit3}",
        value_names=["digit1", "digit2", "digit3"],
        use_previous_value=True,
        consistency_enabled=True,
        max_rate_value=10.0,
    )

    # 105.0 - 100.0 = 5.0 <= max_rate_value (10.0)
    result = processor.get_meter_values([meter_cfg])

    assert len(result.meters) == 1
    m = result.meters[0]
    assert m.value == "105"
    assert m.quality == "good"
    assert m.warning == ""
    assert m.valid is True
    assert result.valid is True
    assert result.warning == ""
    mock_save.assert_called_once_with("test-prev.ini", "total", "105")


@patch("src.processor.digitizer.load_previous_value_from_file", return_value="123.500")
@patch(
    "src.processor.digitizer.save_previous_value_to_file",
    side_effect=OSError("Disk full / permission denied"),
)
def test_postprocessing_save_previous_value_failure_handled_gracefully(
    mock_save, mock_load
) -> None:
    """Verify that a disk write error during save_previous_value does not crash postprocessing."""
    meter = get_default_meter()
    meter.config.max_rate_value = 1.0
    processor = get_default_processor()
    # Should not raise OSError, but log warning and continue
    processor._postprocess_meter_value(meter, {}, get_default_cnn_results())
    assert meter.value == "123.567"
    assert meter.valid is True
    assert meter.warning == ""
    mock_save.assert_called_once()


def test_postprocessing_missing_previous_value_file_raises_value_error() -> None:
    """Verify that attempting to use previous value without a configured file raises ValueError."""
    meter = get_default_meter()
    meter.config.use_previous_value = True
    processor = DigitizerProcessor()
    processor.previous_value_file = None

    with pytest.raises(
        ValueError,
        match="Previous value file must be configured when use_previous_value is enabled",
    ):
        processor._postprocess_meter_value(meter, {}, get_default_cnn_results())


def test_get_meter_values_with_unresolved_question_mark_digit() -> None:
    """Verify that an unresolved digit ('?') results in valid=False and quality='uncertain'."""
    processor = DigitizerProcessor()
    processor.available_values = {"digit1": 1, "digit2": "?", "digit3": 5}
    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=1, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit2", value="?", model=MODEL_DIGITAL, confidence=20.0),
        ReadoutResult(name="digit3", value=5, model=MODEL_DIGITAL, confidence=95.0),
    ]

    meter_cfg = MeterConfig(
        name="main",
        format="{digit1}{digit2}{digit3}",
        value_names=["digit1", "digit2", "digit3"],
        use_previous_value=False,
    )

    result = processor.get_meter_values([meter_cfg])
    assert len(result.meters) == 1
    m = result.meters[0]
    assert m.value == "1?5"
    assert m.valid is False
    assert m.quality == "uncertain"
    assert result.valid is False


def test_format_parser_graceful_missing_slot_fallback() -> None:
    """Verify that format_template falls back to template string when a slot is missing from values."""
    res = FormatParser.format_template("{digit1}.{missing_slot}", {"digit1": "123"})
    assert res == "{digit1}.{missing_slot}"
