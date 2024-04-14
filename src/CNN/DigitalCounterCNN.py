import logging

from PIL import Image
import numpy as np

from CNN.CNNBase import CNNBase

logger = logging.getLogger(__name__)


class DigitalCounterCNN(CNNBase):
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

    def readout(self, image: Image) -> int:
        output_data = super().readout(image)
        return np.argmax(output_data)
