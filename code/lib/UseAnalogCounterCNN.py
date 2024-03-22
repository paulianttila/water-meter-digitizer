from lib.CNNBase import CNNBase
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)


class UseAnalogCounterCNN(CNNBase):
    def __init__(self, in_Modelfile, in_dx, in_dy, in_LogImageLocation, in_LogNames):
        super().__init__(in_Modelfile, in_dx, in_dy, in_LogImageLocation)

        if in_LogImageLocation and in_LogNames:
            zw_LogNames = in_LogNames.split(",")
            self.LogNames = []
            self.LogNames.extend(nm.strip() for nm in zw_LogNames)

        super()._LoadModel()

    def ReadoutSingleImage(self, image):
        output_data = super().ReadoutSingleImage(image)

        out_sin = output_data[0][0]
        out_cos = output_data[0][1]
        result = np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1
        result = result * 10

        logger.debug("Validity 06")
        return result
