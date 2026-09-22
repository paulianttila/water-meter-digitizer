from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image
from PIL.Image import Resampling

from cnn.analog_needle_cnn import AnalogNeedleCNN
from cnn.base import CNNBase
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


def test_cnn_base_readout_resampling_configurable():
    """Verify _readout respects configurable resampling mode (BILINEAR, NEAREST)."""
    cnn = CNNBase.__new__(CNNBase)
    cnn.modelfile = "dummy.tflite"
    cnn.dx = 20
    cnn.dy = 32
    cnn.resampling = Resampling.BILINEAR

    mock_inst = MagicMock()
    mock_inst.input_index = 0
    mock_inst.output_index = 1
    mock_inst.interpreter.get_tensor.return_value = np.zeros((1, 10), dtype=np.float32)

    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__enter__.return_value = mock_inst
    cnn.pool = mock_pool

    img = Image.new("RGB", (64, 64), color="blue")
    with patch.object(img, "resize", wraps=img.resize) as spy_resize:
        output = cnn._readout(img)

        spy_resize.assert_called_once_with((20, 32), Resampling.BILINEAR)
        assert output.shape == (1, 10)

        # Verify tensor passed to interpreter has shape [1, dy, dx, 3]
        mock_inst.interpreter.set_tensor.assert_called_once()
        tensor_arg = mock_inst.interpreter.set_tensor.call_args[0][1]
        assert tensor_arg.shape == (1, 32, 20, 3)

    # Verify default mode is NEAREST
    cnn_default = CNNBase.__new__(CNNBase)
    cnn_default.modelfile = "dummy.tflite"
    cnn_default.dx = 20
    cnn_default.dy = 32
    cnn_default.resampling = Resampling.NEAREST
    cnn_default.pool = mock_pool
    with patch.object(img, "resize", wraps=img.resize) as spy_resize_default:
        cnn_default._readout(img)
        spy_resize_default.assert_called_once_with((20, 32), Resampling.NEAREST)
