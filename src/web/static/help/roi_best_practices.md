### Neural Network Model Types & ROI Best Practices

Select the optimal model and bounding box geometry for accurate digitization:

#### Model Classifications
- **`auto`**: Automatically selects between digital drum and analog dial classification based on step context.
- **`digital / digital100`**: Quantized CNN for mechanical drum odometer digits (0–9) and 100-class fractional transitions.
- **`analog`**: CNN interpreter predicting continuous needle angles (0.0–9.9) for circular dials.

#### ROI Geometry Guidelines
- **Tight Drum Digits**: Keep bounding boxes tight around the numeral window, excluding borders or outer bezels.
- **Centered Needle Pivots**: Center analog dial ROIs precisely on the needle center pin to preserve circular symmetry.
