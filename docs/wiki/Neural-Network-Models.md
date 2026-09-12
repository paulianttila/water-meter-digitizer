# Neural Network Models & Inference Pooling

The **Water Meter Digitizer** uses specialized lightweight Convolutional Neural Networks (CNNs) in TensorFlow Lite (`.tflite`) format executed via Google LiteRT runtime.

---

## 🧠 Model Architectures

### 1. Digital Counter Models (Class 100)
- **Model Type**: Softmax Multi-Class Classification ($100$ output classes).
- **Resolution**: $20 \times 32$ pixels, 3 channels (RGB).
- **Classification Output**: Numbers from $0.0$ to $9.9$ in steps of $0.1$.
  - Example: A drum midway between $4$ and $5$ produces high probability at class $4.5$.
- **File Name**: `dig-class100_0168_s2_q.tflite` (Quantized INT8/FP32).

### 2. Analog Needle Models (Continuous / Class 100)
- **Model Type**: Circular needle angle regression or continuous classification.
- **Resolution**: $32 \times 32$ pixels, 3 channels (RGB).
- **Output**: Angle position mapped from $0.00$ to $9.99$.
- **File Name**: `ana-cont_1209_s2.tflite`.

---

## ⚡ Thread-Safe LiteRT Interpreter Pooling (`InterpreterPool`)

Standard TensorFlow Lite Python interpreters are not thread-safe. To support concurrent REST requests, background polling, and UI inspections without blocking, the digitizer implements an **`InterpreterPool`**:

- Maintains a configurable pool of independent `tflite.Interpreter` worker instances.
- Thread-safe `acquire()` / `release()` context managers eliminate lock contention.
- Tracks real-time inference latency metrics ($p50$, $p95$, average ms).
