import logging
import math

import numpy as np
from PIL.Image import Image

from cnn.base import CNNBase, density_confidence, stable_softmax

logger = logging.getLogger(__name__)


class AnalogNeedleCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        pool_size: int | None = None,
    ) -> None:
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            pool_size=pool_size,
        )

    def readout_with_confidence(self, image: Image) -> tuple[float, float]:
        """Run inference and return (predicted_value, confidence_percentage)."""
        output_data = self._readout(image)
        numer_output = self.get_model_details().numer_output

        if numer_output == 100:
            probs = stable_softmax(output_data[0])
            argmax = int(np.argmax(probs))
            result = float(argmax) / 10.0
            conf = density_confidence(probs, argmax, window=1)
            return result, conf
        else:
            out_sin = float(output_data[0][0])
            out_cos = float(output_data[0][1])
            result = float((np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1) * 10)
            # Vector magnitude on unit circle represents signal clarity
            magnitude = math.sqrt(out_sin**2 + out_cos**2)
            conf = min(100.0, magnitude * 100.0)
            return result, round(min(100.0, max(0.0, conf)), 1)

    def readout(self, image: Image) -> float:
        value, _ = self.readout_with_confidence(image)
        return value

    async def readout_with_confidence_async(self, image: Image) -> tuple[float, float]:
        """Asynchronously run inference and return (predicted_value, confidence)."""
        import asyncio

        return await asyncio.to_thread(self.readout_with_confidence, image)

    async def readout_async(self, image: Image) -> float:
        """Asynchronously run inference and return predicted value."""
        import asyncio

        return await asyncio.to_thread(self.readout, image)
