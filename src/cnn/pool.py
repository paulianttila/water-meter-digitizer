import logging
import os
import queue
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite  # type: ignore
    except ImportError:
        try:
            import tensorflow.lite as tflite  # type: ignore
        except ImportError:
            tflite = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ModelDetails:
    name: str
    xsize: int
    ysize: int
    channels: int
    numer_output: int


class InterpreterInstance:
    """Encapsulates a single pre-allocated TFLite/LiteRT interpreter instance."""

    def __init__(self, modelfile: str) -> None:
        if tflite is None:
            raise RuntimeError("No LiteRT or TFLite runtime found in environment")

        self.modelfile = modelfile
        self.interpreter = tflite.Interpreter(model_path=modelfile)  # type: ignore
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_index = self.input_details[0]["index"]
        self.output_index = self.output_details[0]["index"]

        self.input_shape = [int(dim) for dim in self.input_details[0]["shape"]]
        self.output_shape = [int(dim) for dim in self.output_details[0]["shape"]]

        dtype_str = str(self.input_details[0]["dtype"])
        self.quantized = "int8" in dtype_str or "uint8" in dtype_str

        xsize = self.input_details[0]["shape"][1]
        ysize = self.input_details[0]["shape"][2]
        channels = self.input_details[0]["shape"][3]
        numer_output = self.output_details[0]["shape"][1]

        self.model_details = ModelDetails(
            name=modelfile,
            xsize=xsize,
            ysize=ysize,
            channels=channels,
            numer_output=numer_output,
        )


class InterpreterPool:
    """Thread-safe pool of TFLite / LiteRT interpreters for a specific model."""

    def __init__(self, modelfile: str, max_size: int | None = None) -> None:
        self.modelfile = modelfile
        self.max_size = max_size or max(1, min(4, os.cpu_count() or 2))
        self._pool: queue.Queue[InterpreterInstance] = queue.Queue()
        self._created_count = 0
        self._active_inferences = 0
        self._lock = threading.RLock()
        self._model_details: ModelDetails | None = None
        self._input_shape: list[int] | None = None
        self._output_shape: list[int] | None = None
        self._quantized: bool = False

        # Metrics telemetry
        self._total_inferences = 0
        self._total_inference_time_ms = 0.0
        self._min_inference_ms: float | None = None
        self._max_inference_ms: float | None = None
        self._last_inference_ms: float | None = None
        self._last_inference_at: str | None = None

        # Pre-warm at least one instance to validate model file immediately
        self._prewarm()

    def _prewarm(self) -> None:
        if os.path.isfile(self.modelfile) and self.modelfile.endswith(".tflite"):
            try:
                inst = self._create_instance()
                self._pool.put(inst)
                self._model_details = inst.model_details
                self._input_shape = inst.input_shape
                self._output_shape = inst.output_shape
                self._quantized = inst.quantized
            except Exception as e:
                logger.error(
                    f"Failed to pre-warm LiteRT interpreter for '{self.modelfile}': {e}"
                )

    def _create_instance(self) -> InterpreterInstance:
        inst = InterpreterInstance(self.modelfile)
        with self._lock:
            self._created_count += 1
            if self._model_details is None:
                self._model_details = inst.model_details
                self._input_shape = inst.input_shape
                self._output_shape = inst.output_shape
                self._quantized = inst.quantized
        return inst

    @contextmanager
    def acquire(
        self, timeout: float = 30.0
    ) -> Generator[InterpreterInstance, None, None]:
        """Acquire an interpreter instance from the pool in a thread-safe context."""
        instance: InterpreterInstance | None = None
        try:
            instance = self._pool.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._created_count < self.max_size:
                    instance = self._create_instance()

            if instance is None:
                instance = self._pool.get(timeout=timeout)

        with self._lock:
            self._active_inferences += 1

        try:
            yield instance
        finally:
            with self._lock:
                self._active_inferences = max(0, self._active_inferences - 1)
            if instance is not None:
                self._pool.put(instance)

    def record_inference(self, duration_ms: float) -> None:
        """Record inference timing telemetry in a thread-safe manner."""
        with self._lock:
            self._total_inferences += 1
            self._total_inference_time_ms += duration_ms
            if self._min_inference_ms is None or duration_ms < self._min_inference_ms:
                self._min_inference_ms = round(duration_ms, 2)
            if self._max_inference_ms is None or duration_ms > self._max_inference_ms:
                self._max_inference_ms = round(duration_ms, 2)
            self._last_inference_ms = round(duration_ms, 2)
            self._last_inference_at = datetime.now(UTC).isoformat()

    def get_stats(self) -> dict[str, Any]:
        """Return runtime performance and pool metrics."""
        with self._lock:
            avg_ms = (
                round(self._total_inference_time_ms / self._total_inferences, 2)
                if self._total_inferences > 0
                else None
            )
            return {
                "inferences": self._total_inferences,
                "avg_inference_ms": avg_ms,
                "min_inference_ms": self._min_inference_ms,
                "max_inference_ms": self._max_inference_ms,
                "last_inference_ms": self._last_inference_ms,
                "last_inference_at": self._last_inference_at,
                "pool_size": self.max_size,
                "created_instances": self._created_count,
                "available_instances": self._pool.qsize(),
                "active_inferences": self._active_inferences,
                "input_shape": self._input_shape,
                "output_shape": self._output_shape,
                "quantized": self._quantized,
            }

    def reset_stats(self) -> None:
        """Reset runtime performance metrics counters."""
        with self._lock:
            self._total_inferences = 0
            self._total_inference_time_ms = 0.0
            self._min_inference_ms = None
            self._max_inference_ms = None
            self._last_inference_ms = None
            self._last_inference_at = None

    def get_model_details(self) -> ModelDetails:
        if self._model_details is not None:
            return self._model_details
        with self.acquire() as inst:
            return inst.model_details

    def clear(self) -> None:
        """Drain and clear the pool."""
        with self._lock:
            while not self._pool.empty():
                try:
                    self._pool.get_nowait()
                except queue.Empty:
                    break
            self._created_count = 0
            self._active_inferences = 0
            self._model_details = None
            self.reset_stats()


_POOLS: dict[str, InterpreterPool] = {}
_POOLS_LOCK = threading.Lock()


def get_interpreter_pool(
    modelfile: str, max_size: int | None = None
) -> InterpreterPool:
    """Retrieve or create a cached InterpreterPool for the given model file."""
    canonical = os.path.realpath(os.path.abspath(modelfile))
    with _POOLS_LOCK:
        if canonical not in _POOLS:
            _POOLS[canonical] = InterpreterPool(modelfile, max_size=max_size)
        return _POOLS[canonical]


def clear_interpreter_pools() -> None:
    """Clear and release all cached interpreter pools."""
    with _POOLS_LOCK:
        for pool in _POOLS.values():
            pool.clear()
        _POOLS.clear()
