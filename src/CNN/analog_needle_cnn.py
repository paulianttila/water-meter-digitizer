import math
import logging

from PIL import Image
import numpy as np

from cnn.base import CNNBase

logger = logging.getLogger(__name__)


class AnalogNeedleCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
    ):
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
        )
        super()._loadModel()

    def readout(self, image: Image) -> float:
        output_data = super().readout(image)
        out_sin = output_data[0][0]
        out_cos = output_data[0][1]
        result = np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1
        result = result * 10
        return result
