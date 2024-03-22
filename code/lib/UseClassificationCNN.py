from lib.CNNBase import CNNBase
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class UseClassificationCNN(CNNBase):
    def __init__(self, in_Modelfile, in_dx, in_dy, in_numberclasses, in_LogImageLocation, in_LogNames):
        super().__init__(in_Modelfile, in_dx, in_dy, in_LogImageLocation)

        if in_LogImageLocation:
            if (os.path.exists(self.log_Image)):
                for i in range(in_numberclasses):
                    pfad = f'{self.log_Image}/{str(i)}'
                    if not os.path.exists(pfad):
                        os.makedirs(pfad)

            if in_LogNames:
                zw_LogNames = in_LogNames.split(',')
                self.LogNames = []
                self.LogNames.extend(nm.strip() for nm in zw_LogNames)
            else:
                self.LogNames = ''
        else:
            self.log_Image = ''

        super()._LoadModel()

    def ReadoutSingleImage(self, image):
        output_data = super().ReadoutSingleImage(image)
        result = np.argmax(output_data)

        if result == 10:
            result = "NaN"

        logger.debug("Validity 06")
        return result
