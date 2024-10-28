import contextlib
from dataclasses import dataclass
import os
import logging
from importlib import util

from PIL.Image import Image, NEAREST
import numpy as np


with contextlib.suppress(ImportError):
    import tflite_runtime.interpreter as tflite

spam_spec = util.find_spec("tensorflow")
found_tensorflow = spam_spec is not None

spam_spec = util.find_spec("tflite_runtime")
found_tflite = spam_spec is not None

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.modelfile = modelfile
        self.dx = dx
        self.dy = dy

    def _loadModel(self) -> None:
        filename, file_extension = os.path.splitext(self.modelfile)
        if file_extension != ".tflite":
            logger.error(
                "Only TFLite-Model (*.tflite) are support since version "
                "7.0.0 and higher"
            )
            return

        try:
            self.interpreter = tflite.Interpreter(model_path=self.modelfile)  # type: ignore
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
        logger.debug(
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

    def _readout(self, image: Image) -> np.ndarray:
        test_image = image.resize((self.dx, self.dy), NEAREST)
        test_image = np.array(test_image, dtype="float32")
        input_data = np.reshape(test_image, [1, self.dy, self.dx, 3])
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]["index"])
