import logging
from typing import Union

from PIL.Image import Image
import numpy as np

from cnn.base import CNNBase

logger = logging.getLogger(__name__)


class DigitalCounterCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
    ) -> None:
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
        )
        super()._loadModel()

    def readout(self, image: Image) -> Union[float, int]:
        output_data = super()._readout(image)
        if super().getModelDetails().numer_output == 100:
            return float(np.argmax(output_data)) / 10
        else:
            return int(np.argmax(output_data))
