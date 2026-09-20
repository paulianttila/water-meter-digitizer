### End-to-End Runtime Pipeline Architecture

The digitization engine processes images through 6 autonomous stages:

1. **Capture**: Retrieve live image via HTTP/RTSP snapshot or local file.
2. **Alignment**: Align image using affine transformation with 3 reference markers.
3. **Adjustment**: Apply contrast, brightness, sharpness, and AutoContrast filtering.
4. **Inference**: Run lightweight LiteRT CNN models for digital and analog ROI readouts.
5. **Consistency**: Rollover logic deduction and maximum flow rate validation.
6. **Export**: Publish readings via MQTT, Home Assistant discovery, and SQLite storage.
