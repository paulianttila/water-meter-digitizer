import math
import logging

from PIL.Image import Image
import numpy as np

from cnn.base import CNNBase

logger = logging.getLogger(__name__)


class AnalogNeedleCNN(CNNBase):
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

    def readout_with_confidence(self, image: Image) -> tuple[float, float]:
        """Run inference and return (predicted_value, confidence_percentage)."""
        output_data = self._readout(image)
        numer_output = self.getModelDetails().numer_output

        if numer_output == 100:
            z = np.array(output_data[0], dtype=float)
            if np.all(z >= 0) and np.isclose(np.sum(z), 1.0, atol=0.05):
                probs = z
            else:
                exp_z = np.exp(z - np.max(z))
                sum_exp = np.sum(exp_z)
                probs = exp_z / sum_exp if sum_exp > 0 else np.zeros_like(exp_z)
            argmax = int(np.argmax(probs))
            result = float(argmax) / 10.0
            low_idx = max(0, argmax - 1)
            high_idx = min(len(probs), argmax + 2)
            conf = float(np.sum(probs[low_idx:high_idx])) * 100.0
            return result, round(min(100.0, max(0.0, conf)), 1)
        else:
            out_sin = float(output_data[0][0])
            out_cos = float(output_data[0][1])
            result = float((np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1) * 10)
            # Vector magnitude on unit circle represents signal clarity
            magnitude = math.sqrt(out_sin**2 + out_cos**2)
            conf = min(100.0, magnitude * 100.0)
            return result, round(min(100.0, max(0.0, conf)), 1)

    def readout(self, image: Image) -> float:
        value, _ = self.readout_with_confidence(image)
        return value
