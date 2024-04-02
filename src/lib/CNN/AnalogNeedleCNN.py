from lib.CNN.CNNBase import CNNBase
from PIL import Image
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)


class AnalogNeedleCNN(CNNBase):
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

    def _readout_single_image(self, image: Image) -> float:
        output_data = super()._readout_single_image(image)
        out_sin = output_data[0][0]
        out_cos = output_data[0][1]
        result = np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1
        result = result * 10
        return result
