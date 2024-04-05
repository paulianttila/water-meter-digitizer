import contextlib
from dataclasses import dataclass
import time
from typing import List
from PIL import Image
import numpy as np
import os
import logging
from importlib import util

from ImageProcessor import CutImage

with contextlib.suppress(ImportError):
    import tflite_runtime.interpreter as tflite

spam_spec = util.find_spec("tensorflow")
found_tensorflow = spam_spec is not None

spam_spec = util.find_spec("tflite_runtime")
found_tflite = spam_spec is not None

logger = logging.getLogger(__name__)


@dataclass
class ReadoutResult:
    name: str
    value: float


@dataclass
class ModelDetails:
    name: str
    xsize: int
    ysize: int
    channels: int
    numer_output: int


class CNNBase:
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        image_log_dir: str = None,
    ):
        self.modelfile = modelfile
        self.dx = dx
        self.dy = dy
        self.image_log_dir = image_log_dir

    def _loadModel(self):
        filename, file_extension = os.path.splitext(self.modelfile)
        if file_extension != ".tflite":
            logger.error(
                "Only TFLite-Model (*.tflite) are support since version "
                "7.0.0 and higher"
            )
            return

        try:
            self.interpreter = tflite.Interpreter(model_path=self.modelfile)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.getModelDetails()
        except Exception as e:
            logger.error(f"Error occured during model '{self.modelfile}' loading: {e}")

    def getModelDetails(self) -> ModelDetails:
        xsize = self.input_details[0]["shape"][1]
        ysize = self.input_details[0]["shape"][2]
        channels = self.input_details[0]["shape"][3]
        numeroutput = self.output_details[0]["shape"][1]
        logger.info(
            f"Model '{self.modelfile}' loaded. "
            f"ModelSize: {xsize}x{ysize}x{channels}. "
            f"Output: {numeroutput}"
        )

        return ModelDetails(
            self.modelfile,
            xsize,
            ysize,
            channels,
            numeroutput,
        )

    def readout(self, pictureList: List[CutImage]) -> List[ReadoutResult]:
        """
        Performs Convolutional Neural Network readout on a list of images.

        Args:
            pictureList (List[CutImage]): A list of CutImage objects containing
            the images to perform readout on.

        Returns:
            List[ReadoutResult]: A list of ReadoutResult objects containing
            the readout results for each image.
        """
        self.result = []
        for item in pictureList:
            value = self._readout_single_image(item.image)
            self._save_image_to_log_dir(item.name, item.image, value)
            self.result.append(ReadoutResult(item.name, value))
        return self.result

    def _readout_single_image(self, image: Image):
        test_image = image.resize((self.dx, self.dy), Image.NEAREST)
        test_image = np.array(test_image, dtype="float32")
        input_data = np.reshape(test_image, [1, self.dy, self.dx, 3])
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]["index"])

    def _save_image_to_log_dir(self, name: str, image: Image, value):
        if self.image_log_dir is None or len(self.image_log_dir) <= 0:
            return

        val = str(int(value)) if isinstance(value, float) else str(value)
        folder = f"{self.image_log_dir}/{val}"

        self._create_dir_if_not_exists(folder)
        t = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        filename = f"{folder}/{name}_{t}.jpg"
        logger.debug(f"Save image to {filename}")
        image.save(filename, "JPEG")

    def _create_dir_if_not_exists(self, folder: str):
        os.makedirs(folder, exist_ok=True)
