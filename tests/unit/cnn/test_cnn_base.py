"""Unit tests for CNNBase model loading, error handling, and ModelLoadError."""

import pytest

from cnn.analog_needle_cnn import AnalogNeedleCNN
from cnn.digital_counter_cnn import DigitalCounterCNN
from exceptions import ModelLoadError, PipelineError, WaterMeterError


def test_model_load_error_hierarchy():
    """Verify ModelLoadError inherits from PipelineError, WaterMeterError, and RuntimeError."""
    err = ModelLoadError("Test error", details={"path": "test.tflite"})
    assert isinstance(err, PipelineError)
    assert isinstance(err, WaterMeterError)
    assert isinstance(err, RuntimeError)
    assert err.message == "Test error"
    assert err.details == {"path": "test.tflite"}
    assert "Test error" in str(err)


def test_load_model_nonexistent_file_raises_model_load_error():
    """Verify initializing a CNN with a missing .tflite file raises ModelLoadError."""
    with pytest.raises(ModelLoadError) as exc_info:
        DigitalCounterCNN("nonexistent_model_file.tflite", dx=20, dy=32)

    assert "Failed to load model" in str(exc_info.value)
    assert "nonexistent_model_file.tflite" in str(exc_info.value)


def test_load_model_corrupt_file_raises_model_load_error(tmp_path):
    """Verify initializing a CNN with corrupt .tflite data raises ModelLoadError."""
    corrupt_file = tmp_path / "corrupt.tflite"
    corrupt_file.write_bytes(b"INVALID_CORRUPTED_TFLITE_BYTES_1234567890")

    with pytest.raises(ModelLoadError) as exc_info:
        AnalogNeedleCNN(str(corrupt_file), dx=32, dy=32)

    assert "Failed to load model" in str(exc_info.value)
    assert "corrupt.tflite" in str(exc_info.value)


def test_load_model_unsupported_extension_raises_model_load_error():
    """Verify initializing a CNN with a non-.tflite extension raises ModelLoadError immediately."""
    with pytest.raises(ModelLoadError) as exc_info:
        DigitalCounterCNN("model.onnx", dx=20, dy=32)

    assert "Unsupported model file" in str(exc_info.value)
    assert ".onnx" in str(exc_info.value)
