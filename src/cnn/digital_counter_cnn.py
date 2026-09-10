import logging

import numpy as np
from PIL.Image import Image

from cnn.base import CNNBase, density_confidence, stable_softmax

logger = logging.getLogger(__name__)


class DigitalCounterCNN(CNNBase):
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

    def readout_with_confidence(self, image: Image) -> tuple[float | int, float]:
        """Run inference and return (predicted_value, confidence_percentage)."""
        output_data = self._readout(image)
        probs = stable_softmax(output_data[0])
        argmax = int(np.argmax(probs))

        if self.get_model_details().numer_output == 100:
            value = float(argmax) / 10.0
            conf = density_confidence(probs, argmax, window=1)
            return value, conf
        else:
            if argmax == 10:
                # Class 10 represents NaN / unreadable digit
                return float("nan"), 0.0
            value = argmax
            conf = float(probs[argmax]) * 100.0
            return value, round(min(100.0, max(0.0, conf)), 1)

    def readout(self, image: Image) -> float | int:
        value, _ = self.readout_with_confidence(image)
        return value

    async def readout_with_confidence_async(
        self, image: Image
    ) -> tuple[float | int, float]:
        """Asynchronously run inference and return (predicted_value, confidence)."""
        import asyncio

        return await asyncio.to_thread(self.readout_with_confidence, image)

    async def readout_async(self, image: Image) -> float | int:
        """Asynchronously run inference and return predicted value."""
        import asyncio

        return await asyncio.to_thread(self.readout, image)
