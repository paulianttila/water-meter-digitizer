from lib.CNN.CNNBase import CNNBase
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DigitalCounterCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        imageLogFolder: str = None,
    ):
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            imageLogFolder=imageLogFolder,
        )
        super()._loadModel()

    def readoutSingleImage(self, image):
        output_data = super().readoutSingleImage(image)
        return np.argmax(output_data)
