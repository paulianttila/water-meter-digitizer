from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pytest

from cnn.pool import (
    InterpreterPool,
    get_interpreter_pool,
    clear_interpreter_pools,
)
from cnn.digital_counter_cnn import DigitalCounterCNN
from cnn.analog_needle_cnn import AnalogNeedleCNN

DIGITAL_MODEL = "test_config/neuralnets/digital/dig-class100_0168_s2_q.tflite"
ANALOG_MODEL = "test_config/neuralnets/analog/ana-class100_0171_s2.tflite"


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

    pool.clear()


def test_get_interpreter_pool_registry():
    clear_interpreter_pools()
    pool1 = get_interpreter_pool(DIGITAL_MODEL, max_size=2)
    pool2 = get_interpreter_pool(DIGITAL_MODEL)
    assert pool1 is pool2

    clear_interpreter_pools()


def test_concurrent_digital_model_readout():
    model = DigitalCounterCNN(DIGITAL_MODEL, dx=20, dy=32, pool_size=4)
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


def test_concurrent_analog_model_readout():
    model = AnalogNeedleCNN(ANALOG_MODEL, dx=32, dy=32, pool_size=4)
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
