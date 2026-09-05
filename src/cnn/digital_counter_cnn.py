import logging

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

    def readout_with_confidence(self, image: Image) -> tuple[float | int, float]:
        """Run inference and return (predicted_value, confidence_percentage)."""
        output_data = self._readout(image)
        z = np.array(output_data[0], dtype=float)

        # If already normalized probabilities, use directly;
        # otherwise apply stable softmax
        if np.all(z >= 0) and np.isclose(np.sum(z), 1.0, atol=0.05):
            probs = z
        else:
            exp_z = np.exp(z - np.max(z))
            sum_exp = np.sum(exp_z)
            probs = exp_z / sum_exp if sum_exp > 0 else np.zeros_like(exp_z)
        argmax = int(np.argmax(probs))

        if self.getModelDetails().numer_output == 100:
            value = float(argmax) / 10.0
            # 3-bin probability density around the continuous peak
            low_idx = max(0, argmax - 1)
            high_idx = min(len(probs), argmax + 2)
            conf = float(np.sum(probs[low_idx:high_idx])) * 100.0
            return value, round(min(100.0, max(0.0, conf)), 1)
        else:
            if argmax == 10:
                # Class 10 represents NaN / unreadable digit
                return float("nan"), 0.0
            value = argmax
            conf = float(probs[argmax]) * 100.0
            return value, round(min(100.0, max(0.0, conf)), 1)

    def readout(self, image: Image) -> float | int:
        value, _ = self.readout_with_confidence(image)
        return value
