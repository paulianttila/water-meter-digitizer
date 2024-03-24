from lib.CNNBase import CNNBase
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)


class UseClassificationCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        imageTmpFolder: str = "/image_tmp/",
        imageLogFolder: str = None,
        imageLogNames: list = [],
    ):
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            imageTmpFolder=imageTmpFolder,
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
