import lib.CNNBase as CNNBase
import numpy as np
import logging

logger = logging.getLogger(__name__)

class UseClassificationCNN(CNNBase):
    def __init__(self, in_Modelfile, in_dx, in_dy, in_numberclasses, in_LogImageLocation, in_LogNames):
        super().__init__(in_Modelfile, in_dx, in_dy, in_LogImageLocation, in_LogNames)

    def ReadoutSingleImage(self, image):
        output_data = super().ReadoutSingleImage(image)
        result = np.argmax(output_data)

        if result == 10:
            result = "NaN"

        logger.debug("Validity 06")
        return result
