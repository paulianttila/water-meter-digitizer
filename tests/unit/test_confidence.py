import math
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image
import pytest

from cnn.base import CNNBase, ModelDetails
from cnn.digital_counter_cnn import DigitalCounterCNN
from cnn.analog_needle_cnn import AnalogNeedleCNN
from data_classes import MeterConfig
from configuration import Config
from processor.digitizer import (
    DigitizerProcessor,
    Meter,
    ReadoutResult,
    INVALID_DIGIT,
    MODEL_ANALOG,
    MODEL_DIGITAL,
)

# ======================================================================
# Digital Counter CNN Confidence Tests
# ======================================================================


def test_digital_counter_11class_high_confidence():
    with patch.object(CNNBase, "_loadModel"):
        cnn = DigitalCounterCNN("dummy.tflite", 20, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=20, ysize=32, channels=3, numer_output=11
            )
        )
        logits = np.array(
            [-10.0, -10.0, -10.0, -10.0, 10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0]
        )
        with patch.object(CNNBase, "_readout", return_value=[logits]):
            dummy_img = Image.new("RGB", (20, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert val == 4
            assert conf > 99.0


def test_digital_counter_already_normalized_probabilities():
    with patch.object(CNNBase, "_loadModel"):
        cnn = DigitalCounterCNN("dummy.tflite", 20, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=20, ysize=32, channels=3, numer_output=11
            )
        )
        # Model output is already a normalized softmax probability distribution
        probs = np.array([0.0, 0.0, 0.0, 0.99, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        with patch.object(CNNBase, "_readout", return_value=[probs]):
            dummy_img = Image.new("RGB", (20, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert val == 3
            assert conf == 99.0  # Must not be reduced to 21.4% by double softmax!


def test_digital_counter_11class_nan_class():
    with patch.object(CNNBase, "_loadModel"):
        cnn = DigitalCounterCNN("dummy.tflite", 20, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=20, ysize=32, channels=3, numer_output=11
            )
        )
        logits = np.array([-10.0] * 10 + [10.0])
        with patch.object(CNNBase, "_readout", return_value=[logits]):
            dummy_img = Image.new("RGB", (20, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert math.isnan(val)
            assert conf == 0.0


def test_digital_counter_100class_density_window():
    with patch.object(CNNBase, "_loadModel"):
        cnn = DigitalCounterCNN("dummy.tflite", 20, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=20, ysize=32, channels=3, numer_output=100
            )
        )
        logits = np.zeros(100)
        logits[44] = 8.0
        logits[45] = 10.0
        logits[46] = 8.0
        with patch.object(CNNBase, "_readout", return_value=[logits]):
            dummy_img = Image.new("RGB", (20, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert val == 4.5
            assert conf > 95.0


# ======================================================================
# Analog Needle CNN Confidence Tests
# ======================================================================


def test_analog_needle_2output_vector_magnitude():
    with patch.object(CNNBase, "_loadModel"):
        cnn = AnalogNeedleCNN("dummy.tflite", 32, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=32, ysize=32, channels=3, numer_output=2
            )
        )
        # Perfect unit circle point: sin(pi/2)=1, cos(pi/2)=0 -> reading 2.5
        with patch.object(CNNBase, "_readout", return_value=[[1.0, 0.0]]):
            dummy_img = Image.new("RGB", (32, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert pytest.approx(val, 0.01) == 2.5
            assert pytest.approx(conf, 0.1) == 100.0

        # Occluded / uncertain point with small vector magnitude (e.g. 0.3, 0.0)
        with patch.object(CNNBase, "_readout", return_value=[[0.3, 0.0]]):
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert pytest.approx(val, 0.01) == 2.5
            assert pytest.approx(conf, 0.1) == 30.0


def test_analog_needle_100class_density_window():
    with patch.object(CNNBase, "_loadModel"):
        cnn = AnalogNeedleCNN("dummy.tflite", 32, 32)
        cnn.getModelDetails = MagicMock(
            return_value=ModelDetails(
                name="dummy.tflite", xsize=32, ysize=32, channels=3, numer_output=100
            )
        )
        logits = np.zeros(100)
        logits[90] = 10.0
        with patch.object(CNNBase, "_readout", return_value=[logits]):
            dummy_img = Image.new("RGB", (32, 32))
            val, conf = cnn.readout_with_confidence(dummy_img)
            assert val == 9.0
            assert conf > 90.0


# ======================================================================
# DigitizerProcessor Confidence & Quality Rating Tests
# ======================================================================


def test_low_confidence_filtering_to_invalid_digit():
    processor = DigitizerProcessor()
    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=5, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(
            name="digit2", value=3, model=MODEL_DIGITAL, confidence=45.0
        ),  # < 60%
    ]
    processor.cnn_analog_results = []
    processor.evaluate_cnn_results()

    assert processor.available_values["digit1"] == 5
    assert processor.available_values["digit2"] == INVALID_DIGIT


def test_configurable_min_confidence_threshold():
    processor = DigitizerProcessor()
    processor.set_min_confidence_threshold(30.0)  # Lower threshold to 30%
    processor.cnn_digital_results = [
        ReadoutResult(
            name="digit1", value=3, model=MODEL_DIGITAL, confidence=45.0
        ),  # > 30% -> valid
        ReadoutResult(
            name="digit2", value=4, model=MODEL_DIGITAL, confidence=20.0
        ),  # < 30% -> invalid
    ]
    processor.cnn_analog_results = []
    processor.evaluate_cnn_results()

    assert processor.available_values["digit1"] == 3
    assert processor.available_values["digit2"] == INVALID_DIGIT


def test_config_min_confidence_threshold_parsing():
    ini_content = """[DEFAULT]
MinConfidenceThreshold = 25.5
"""
    cfg = Config().load_from_string(ini_content)
    assert cfg.min_confidence_threshold == 25.5

    saved = cfg.save_to_string()
    assert "minconfidencethreshold=25.5" in saved.lower()


def test_meter_result_quality_and_confidence_scores():
    processor = DigitizerProcessor()
    processor.digital_counter_reader = MagicMock(spec=DigitalCounterCNN)
    processor.analog_counter_reader = MagicMock(spec=AnalogNeedleCNN)

    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=1.0, model=MODEL_DIGITAL, confidence=95.0),
        ReadoutResult(name="digit2", value=2.0, model=MODEL_DIGITAL, confidence=90.0),
    ]
    processor.cnn_analog_results = [
        ReadoutResult(name="analog1", value=3.0, model=MODEL_ANALOG, confidence=70.0),
    ]

    meter_good = Meter(
        config=MeterConfig(
            name="m_good", format="{digit1}{digit2}", value_names=["digit1", "digit2"]
        ),
        name="m_good",
        value="12",
    )
    meter_warning = Meter(
        config=MeterConfig(
            name="m_warn", format="{digit1}{analog1}", value_names=["digit1", "analog1"]
        ),
        name="m_warn",
        value="13",
    )

    result = processor._gen_result([meter_good, meter_warning])

    assert result.confidence_scores == {
        "digit1": 95.0,
        "digit2": 90.0,
        "analog1": 70.0,
    }

    # m_good: min=90.0, avg=92.5 -> good
    assert result.meters[0].quality == "good"
    assert result.meters[0].confidence == 92.5

    # m_warn: min=70.0, avg=82.5 -> warning
    assert result.meters[1].quality == "warning"
    assert result.meters[1].confidence == 82.5


def test_meter_result_uncertain_quality():
    processor = DigitizerProcessor()
    processor.digital_counter_reader = MagicMock(spec=DigitalCounterCNN)

    processor.cnn_digital_results = [
        ReadoutResult(name="digit1", value=1.0, model=MODEL_DIGITAL, confidence=50.0),
        ReadoutResult(name="digit2", value=2.0, model=MODEL_DIGITAL, confidence=80.0),
    ]
    processor.cnn_analog_results = []

    meter_uncertain = Meter(
        config=MeterConfig(
            name="m_unc", format="{digit1}{digit2}", value_names=["digit1", "digit2"]
        ),
        name="m_unc",
        value="12",
    )

    result = processor._gen_result([meter_uncertain])

    assert result.meters[0].quality == "uncertain"
    assert result.meters[0].confidence == 65.0
