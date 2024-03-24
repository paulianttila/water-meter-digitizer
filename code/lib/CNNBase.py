import contextlib
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
        imageLogFolder: str = None,
        imageLogNames: list = [],
    ):
        self.modelFile = modelfile
        self.dx = dx
        self.dy = dy
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
            logger.error(f"Error loading model: {e}")
            
    def readout(self, pictureList, logtime):
        self.result = []
        for image in pictureList:
            value = self.readoutSingleImage(image[1])
            self.saveImageToLogFolder(image, value, logtime)
            self.result.append(value)
        return self.result

    def saveImageToLogFolder(self, image, value, logtime):
        if len(self.imageLogFolder) > 0:
            if (len(self.imageLogNames) > 0) and (image[0] not in self.imageLogNames):
                return
            filename = f"{value:.1f}_{image[0]}_{logtime}.jpg"
            filename = f"{self.imageLogFolder}/{filename}"
            image[1].save(filename, "JPEG")

    def readoutSingleImage(self, image):
        test_image = image.resize((self.dx, self.dy), Image.NEAREST)
        test_image.save("./image_tmp/resize.jpg", "JPEG")
        test_image = np.array(test_image, dtype="float32")
        input_data = np.reshape(test_image, [1, self.dy, self.dx, 3])
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]["index"])
