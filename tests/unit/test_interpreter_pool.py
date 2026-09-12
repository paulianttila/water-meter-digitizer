import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from cnn.analog_needle_cnn import AnalogNeedleCNN
from cnn.digital_counter_cnn import DigitalCounterCNN
from cnn.pool import (
    InterpreterPool,
    clear_interpreter_pools,
    get_interpreter_pool,
)


def _find_model(rel_path: str) -> str:
    candidates = [
        os.path.join("config", rel_path),
        os.path.join("/config", rel_path),
        os.path.join("test_config", rel_path),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return os.path.join("config", rel_path)


DIGITAL_MODEL = _find_model("neuralnets/digital/class100/dig-class100_0168_s2_q.tflite")
ANALOG_MODEL = _find_model("neuralnets/analog/continuous/ana-cont_1209_s2.tflite")


def test_interpreter_pool_lifecycle():
    pool = InterpreterPool(DIGITAL_MODEL, max_size=3)
    details = pool.get_model_details()
    assert details.xsize == 32
    assert details.ysize == 20
    assert details.numer_output == 100

    # Acquire and release
    with pool.acquire() as inst1:
        assert inst1.input_index is not None
        with pool.acquire() as inst2:
            assert inst2.input_index is not None

    stats = pool.get_stats()
    assert stats["pool_size"] == 3
    assert stats["created_instances"] >= 1
    assert stats["input_shape"] == [1, 32, 20, 3]
    assert stats["output_shape"] == [1, 100]

    pool.clear()


def test_interpreter_pool_metrics():
    pool = InterpreterPool(DIGITAL_MODEL, max_size=2)
    pool.reset_stats()

    stats_initial = pool.get_stats()
    assert stats_initial["inferences"] == 0
    assert stats_initial["avg_inference_ms"] is None
    assert stats_initial["min_inference_ms"] is None
    assert stats_initial["max_inference_ms"] is None

    pool.record_inference(10.0)
    pool.record_inference(20.0)
    pool.record_inference(30.0)

    stats = pool.get_stats()
    assert stats["inferences"] == 3
    assert stats["avg_inference_ms"] == 20.0
    assert stats["min_inference_ms"] == 10.0
    assert stats["max_inference_ms"] == 30.0
    assert stats["last_inference_ms"] == 30.0
    assert stats["last_inference_at"] is not None

    pool.reset_stats()
    stats_after_reset = pool.get_stats()
    assert stats_after_reset["inferences"] == 0
    assert stats_after_reset["avg_inference_ms"] is None

    pool.clear()


def test_get_interpreter_pool_registry():
    clear_interpreter_pools()
    pool1 = get_interpreter_pool(DIGITAL_MODEL, max_size=2)
    pool2 = get_interpreter_pool(DIGITAL_MODEL)
    assert pool1 is pool2

    clear_interpreter_pools()


def test_concurrent_digital_model_readout():
    model = DigitalCounterCNN(DIGITAL_MODEL, dx=20, dy=32, pool_size=4)
    model.pool.reset_stats()
    test_img = Image.new("RGB", (20, 32), color=(128, 128, 128))

    def worker(idx: int):
        val, conf = model.readout_with_confidence(test_img)
        return val, conf

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(24)]
        results = [f.result() for f in futures]

    assert len(results) == 24
    for val, conf in results:
        assert isinstance(val, (int, float))
        assert 0.0 <= conf <= 100.0

    stats = model.pool.get_stats()
    assert stats["inferences"] == 24
    assert stats["avg_inference_ms"] is not None
    assert stats["avg_inference_ms"] > 0
    assert stats["min_inference_ms"] is not None
    assert stats["max_inference_ms"] >= stats["min_inference_ms"]


def test_concurrent_analog_model_readout():
    model = AnalogNeedleCNN(ANALOG_MODEL, dx=32, dy=32, pool_size=4)
    model.pool.reset_stats()
    test_img = Image.new("RGB", (32, 32), color=(100, 150, 200))

    def worker(idx: int):
        val, conf = model.readout_with_confidence(test_img)
        return val, conf

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(24)]
        results = [f.result() for f in futures]

    assert len(results) == 24
    for val, conf in results:
        assert isinstance(val, (int, float))
        assert 0.0 <= conf <= 100.0

    stats = model.pool.get_stats()
    assert stats["inferences"] == 24
    assert stats["avg_inference_ms"] is not None


@pytest.mark.anyio
async def test_async_model_readouts():
    dig_model = DigitalCounterCNN(DIGITAL_MODEL, dx=20, dy=32)
    ana_model = AnalogNeedleCNN(ANALOG_MODEL, dx=32, dy=32)

    test_dig = Image.new("RGB", (20, 32), color=(200, 200, 200))
    test_ana = Image.new("RGB", (32, 32), color=(50, 50, 50))

    val_dig, conf_dig = await dig_model.readout_with_confidence_async(test_dig)
    val_ana, conf_ana = await ana_model.readout_with_confidence_async(test_ana)

    assert isinstance(val_dig, (int, float))
    assert isinstance(val_ana, (int, float))
    assert 0.0 <= conf_dig <= 100.0
    assert 0.0 <= conf_ana <= 100.0


def test_cnn_base_properties_and_fallbacks():
    from cnn.base import CNNBase

    # Non-tflite model error
    base_invalid = CNNBase("invalid_model.h5", dx=20, dy=20)
    assert base_invalid.pool is None
    assert base_invalid.interpreter is None
    assert base_invalid.input_details == []
    assert base_invalid.output_details == []
    assert base_invalid.get_model_details().xsize == 20

    # Valid model properties
    base_valid = CNNBase(DIGITAL_MODEL, dx=32, dy=20)
    assert base_valid.interpreter is not None
    assert len(base_valid.input_details) > 0
    assert len(base_valid.output_details) > 0

    # Readout without loaded pool raises RuntimeError
    base_invalid.pool = None
    with pytest.raises(RuntimeError, match="not loaded"):
        base_invalid._readout(Image.new("RGB", (20, 20)))
