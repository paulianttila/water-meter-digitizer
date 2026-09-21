"""Unit tests for decorators in src/utils/decorators.py."""

import asyncio

from utils.decorators import log_execution_time


def test_log_execution_time_sync(caplog):
    @log_execution_time
    def sample_sync(a, b):
        return a + b

    with caplog.at_level("DEBUG"):
        res = sample_sync(2, 3)
        assert res == 5
        assert "sample_sync" in caplog.text
        assert "Took" in caplog.text


def test_log_execution_time_async(caplog):
    @log_execution_time
    async def sample_async(x, y):
        await asyncio.sleep(0.01)
        return x * y

    with caplog.at_level("DEBUG"):
        res = asyncio.run(sample_async(4, 5))
        assert res == 20
        assert "sample_async" in caplog.text
        assert "Took" in caplog.text


def test_log_execution_time_sync_exception_propagates():
    @log_execution_time
    def faulty_sync():
        raise ValueError("sync test error")

    import pytest

    with pytest.raises(ValueError, match="sync test error"):
        faulty_sync()


def test_log_execution_time_async_exception_propagates():
    @log_execution_time
    async def faulty_async():
        await asyncio.sleep(0.001)
        raise RuntimeError("async test error")

    import pytest

    with pytest.raises(RuntimeError, match="async test error"):
        asyncio.run(faulty_async())


def test_log_execution_time_bound_method(caplog):
    class Calculator:
        @log_execution_time
        def multiply(self, a, b):
            return a * b

        @log_execution_time
        async def async_divide(self, a, b):
            await asyncio.sleep(0.001)
            return a / b

    calc = Calculator()
    with caplog.at_level("DEBUG"):
        assert calc.multiply(6, 7) == 42
        assert "multiply" in caplog.text

        assert asyncio.run(calc.async_divide(10, 2)) == 5.0
        assert "async_divide" in caplog.text
