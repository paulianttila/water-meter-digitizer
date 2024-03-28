from lib.CNNBase import CNNBase
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
        imageLogNames: list = None,
    ):
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            imageLogFolder=imageLogFolder,
            imageLogNames=imageLogNames,
        )
        super()._loadModel()

    def readoutSingleImage(self, image):
        output_data = super().readoutSingleImage(image)
        result = np.argmax(output_data)

        if result == 10:
            result = "NaN"

        return result
