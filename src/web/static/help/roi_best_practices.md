### Neural Network Model Types & ROI Best Practices

Select the optimal model and bounding box geometry for accurate digitization:

#### Model Classifications
- **`auto`**: Automatically selects between digital drum and analog dial classification based on step context.
- **`digital / digital100`**: Quantized CNN for mechanical drum odometer digits (0–9) and 100-class fractional transitions.
- **`analog`**: CNN interpreter predicting continuous needle angles (0.0–9.9) for circular dials.

#### ROI Geometry Guidelines
- **Digit Inner Box Rule (20% Border)**: For digit recognition models (`dig-class11`), the **inner thinner rectangle must fit exactly around the digit number** in the picture. The outer rectangle automatically provides the required 20% border on all sides for the CNN model.
- **Centered Needle Pivots**: Center analog dial ROIs precisely on the needle center pin to preserve circular symmetry.
- **Upstream Reference**: ROI drawing and neural network alignment follow the [AI-on-the-edge-device ROI Configuration Guide](https://jomjol.github.io/AI-on-the-edge-device-docs/ROI-Configuration/).


