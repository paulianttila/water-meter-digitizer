from CNN.CNNBase import CNNBase
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DigitalCounterCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        image_log_dir: str = None,
    ):
        super().__init__(
            modelfile,
            dx=dx,
            dy=dy,
            image_log_dir=image_log_dir,
        )
        super()._loadModel()

    def _readout_single_image(self, image: Image) -> int:
        output_data = super()._readout_single_image(image)
        return np.argmax(output_data)
