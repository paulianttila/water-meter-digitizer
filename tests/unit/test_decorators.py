"""Unit tests for decorators in src/decorators/decorators.py."""

import asyncio

from decorators.decorators import log_execution_time


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
