import asyncio
import logging
import os
import time
from importlib import util

import numpy as np
from PIL.Image import Image, Resampling

from cnn.pool import (
    InterpreterPool,
    ModelDetails,
    get_interpreter_pool,
)

spam_spec = util.find_spec("tensorflow")
found_tensorflow = spam_spec is not None

spam_spec = util.find_spec("ai_edge_litert") or util.find_spec("tflite_runtime")
found_tflite = spam_spec is not None

logger = logging.getLogger(__name__)


class CNNBase:
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        pool_size: int | None = None,
    ) -> None:
        self.modelfile = modelfile
        self.dx = dx
        self.dy = dy
        self.pool_size = pool_size
        self.pool: InterpreterPool | None = None
        self._load_model()

    def _load_model(self) -> None:
        _filename, file_extension = os.path.splitext(self.modelfile)
        if file_extension != ".tflite":
            logger.error(
                "Only TFLite-Model (*.tflite) are supported since "
                "version 7.0.0 and higher"
            )
            return

        try:
            self.pool = get_interpreter_pool(self.modelfile, max_size=self.pool_size)
            self.get_model_details()
        except Exception as e:
            logger.error(f"Error occurred during model '{self.modelfile}' loading: {e}")

    @property
    def interpreter(self):
        """Backward-compatible access to an interpreter instance."""
        if self.pool is not None:
            with self.pool.acquire() as inst:
                return inst.interpreter
            return None
        return None

    @property
    def input_details(self):
        """Backward-compatible access to input details."""
        if self.pool is not None:
            with self.pool.acquire() as inst:
                return inst.input_details
        return []

    @property
    def output_details(self):
        """Backward-compatible access to output details."""
        if self.pool is not None:
            with self.pool.acquire() as inst:
                return inst.output_details
        return []

    def get_model_details(self) -> ModelDetails:
        if self.pool is not None:
            details = self.pool.get_model_details()
            logger.debug(
                f"Model '{self.modelfile}' details: "
                f"{details.xsize}x{details.ysize}x{details.channels}, "
                f"Output: {details.numer_output}"
            )
            return details
        return ModelDetails(self.modelfile, self.dx, self.dy, 3, 0)

    def _readout(self, image: Image) -> np.ndarray:
        if self.pool is None:
            raise RuntimeError(f"Model '{self.modelfile}' is not loaded")

        test_image = image.resize((self.dx, self.dy), Resampling.NEAREST)
        img_array = np.array(test_image, dtype="float32")
        input_data = np.reshape(img_array, [1, self.dy, self.dx, 3])

        start_time = time.perf_counter()
        with self.pool.acquire() as inst:
            inst.interpreter.set_tensor(inst.input_index, input_data)
            inst.interpreter.invoke()
            output_data = inst.interpreter.get_tensor(inst.output_index)
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.pool.record_inference(duration_ms)

        return output_data

    async def _readout_async(self, image: Image) -> np.ndarray:
        """Asynchronously execute inference in a worker thread."""
        return await asyncio.to_thread(self._readout, image)
