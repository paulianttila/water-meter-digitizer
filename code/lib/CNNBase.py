import contextlib
import time
from PIL import Image
import numpy as np
import os
import logging
from importlib import util

with contextlib.suppress(ImportError):
    import tflite_runtime.interpreter as tflite

spam_spec = util.find_spec("tensorflow")
found_tensorflow = spam_spec is not None

spam_spec = util.find_spec("tflite_runtime")
found_tflite = spam_spec is not None

logger = logging.getLogger(__name__)


class CNNBase:
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        imageTmpFolder: str = "/image_tmp/",
        imageLogFolder: str = None,
        imageLogNames: list = [],
    ):
        self.modelFile = modelfile
        self.dx = dx
        self.dy = dy
        self.imageTmpFolder = imageTmpFolder
        self.imageLogFolder = imageLogFolder
        self.imageLogNames = imageLogNames

    def _loadModel(self):
        filename, file_extension = os.path.splitext(self.modelFile)
        if file_extension != ".tflite":
            logger.error(
                "Only TFLite-Model (*.tflite) are support since version "
                "7.0.0 and higher"
            )
            return

        try:
            self.interpreter = tflite.Interpreter(model_path=self.modelFile)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
        except Exception as e:
            logger.error(f"Error occured during model '{self.modelFile}' loading: {e}")
            
    def readout(self, pictureList):
        self.result = []
        for image in pictureList:
            value = self.readoutSingleImage(image)
            self.saveImageToLogFolder(image, value)
            self.result.append(value)
        return self.result

    def readoutSingleImage(self, image):
        testImage = image.resize((self.dx, self.dy), Image.NEAREST)
        testImage.save(f"{self.imageTmpFolder}/resize.jpg", "JPEG")
        testImage = np.array(testImage, dtype="float32")
        input_data = np.reshape(testImage, [1, self.dy, self.dx, 3])
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]["index"])

    def saveImageToLogFolder(self, image: str, value):
        if self.imageLogFolder is None or len(self.imageLogFolder) <= 0:
            return

        imageName = image[0]
        if imageName not in self.imageLogNames:
            return

        val = str(int(value)) if isinstance(value, float) else str(value)
        folder = f"{self.imageLogFolder}/{val}"

        self.createFolderIfNotExists(folder)
        t = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        filename = f"{folder}/{imageName}_{t}.jpg"
        logger.debug(f"Save image to {filename}")
        image[1].save(filename, "JPEG")

    def createFolderIfNotExists(self, folder: str):
        os.makedirs(folder, exist_ok=True)
