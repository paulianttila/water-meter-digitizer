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
        numberclasses: int,
        imageTmpFolder: str = "/image_tmp/",
        imageLogFolder: str = None,
        imageLogNames: list = [],
    ):
        self.numberclasses = numberclasses
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            imageTmpFolder=imageTmpFolder,
            imageLogFolder=imageLogFolder,
            imageLogNames=imageLogNames,
        )
        super()._loadModel()
        self.createLogFolders()

    def readoutSingleImage(self, image):
        output_data = super().readoutSingleImage(image)
        result = np.argmax(output_data)

        if result == 10:
            result = "NaN"

        return result

    def createLogFolders(self):
        if self.imageLogFolder and os.path.exists(self.imageLogFolder):
            for i in range(self.numberclasses):
                folder = f"{self.imageLogFolder}/{str(i)}"
                if not os.path.exists(folder):
                    os.makedirs(folder)
