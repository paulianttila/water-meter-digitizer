# 🔬 Architecture, Neural Networks & Pipeline Deep Dive

This document details the internal system architecture, decoupled module design, 6-stage runtime execution pipeline, neural network model specifications, thread-safe LiteRT pooling, and predecessor roll-over mathematics.

---

## 🏛️ System Architecture

```
                  ┌────────────────────────────────────────┐
                  │          FastAPI App (main.py)         │
                  │   REST Endpoints, Lifespan, Routing    │
                  └───────────────────┬────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  NiceGUI (Web)   │        │ MQTT Client Svc  │        │ BackgroundPoller │
│  Frontend Layout │        │ Discovery & Pub  │        │ Async Scheduler  │
└────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │      Callbacks (callbacks.py)   │
                    │ Bridging & Decoupled Execution  │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│       Processor Pipeline        │             │        Storage Subsystem        │
│ - ImageProcessor (OpenCV/PIL)   │             │ - SQLiteStorage (WAL mode)      │
│ - InterpreterPool (LiteRT)      │             │ - MemoryStorage                 │
│ - DigitizerProcessor (Math/SSoT)│             │ - ZeroFlowTracker (Leak Engine) │
└─────────────────────────────────┘             └─────────────────────────────────┘
```

---

## 🔄 6-Stage Runtime Processing Pipeline

```
[1. Capture] ──▶ [2. Alignment] ──▶ [3. Adjustment] ──▶ [4. ROI Extraction] ──▶ [5. LiteRT CNN] ──▶ [6. Post-Processing & Validation]
```

1. **Capture**: `ImageProcessor.download_image` acquires frame bytes via HTTP/RTSP or local file with byte-size threshold validation.
2. **Alignment**: 3-Point affine transformation locks onto reference marker centroids (`ref0`, `ref1`, `ref2`) to correct camera vibration or angle shifts.
3. **Adjustment**: Spatial luminance unsharp masking in CIELAB space, LUT non-linear gamma curves, histogram contrast stretching, and CLAHE glare suppression.
4. **ROI Extraction**: Cuts precise bounding boxes for digital number wheels and analog needle dials.
5. **LiteRT Neural Inference**: Normalizes tensors and executes CNN inference via worker threads in `InterpreterPool`. Detects minus signs (`-`) when enabled.
6. **Post-Processing & Validation**: Predecessor consistency engine resolves mid-roll digit transitions, calculates fractional decimal resolution, validates flow rates, records to SQLite, and broadcasts MQTT telemetry.

---

## 🧠 Neural Network Models & LiteRT Pooling

### 1. Model Architectures
- **Digital Counter Models (Class 100)**:
  - Multi-class classification (100 discrete output bins from `0.0` to `9.9` in steps of `0.1`).
  - Resolution: $20 \times 32$ px (RGB).
  - File: `dig-class100_0168_s2_q.tflite` (Quantized INT8/FP32).
- **Analog Needle Models (Continuous)**:
  - Continuous angle regression from `0.00` to `9.99`.
  - Resolution: $32 \times 32$ px (RGB).
  - File: `ana-cont_1209_s2.tflite`.

### 2. Thread-Safe `InterpreterPool`
Standard TensorFlow Lite interpreters are not thread-safe. The digitizer implements an `InterpreterPool`:
- Configurable worker pool (`PoolSize = 2` by default).
- Thread-safe `acquire()` / `release()` context managers eliminate lock contention during concurrent API calls and background polling.
- Tracks real-time $p50$ and $p95$ inference latency.

---

## 🧮 Predecessor Consistency & Rollover Mathematics

Mechanical odometer drums rotate gradually. During a transition (e.g., $4 \rightarrow 5$), a digit may physically sit at `4.6`:
- If the lower-order predecessor is at `9.8` (almost completed its rotation), the tens digit has not yet crossed into the next decade. The engine floors it to `4`.
- If the lower-order predecessor is at `0.1` (just passed zero), the rollover has completed. The engine rounds to `5`.
- **Extended Resolution**: Appends the continuous fractional position from the lowest-order dial to report ultra-high-precision readings (e.g. `00452.91241 m³`).

---

## 👏 Kudos & Acknowledgments

Special thanks to **[jomjol](https://github.com/jomjol)** for pioneering edge meter digitization and creating the pre-trained neural network models:
- **[neural-network-analog-needle-readout](https://github.com/jomjol/neural-network-analog-needle-readout)**
- **[neural-network-digital-counter-readout](https://github.com/jomjol/neural-network-digital-counter-readout)**

---

## ⏭️ Next Step

Check the **[Troubleshooting & FAQ Guide](Troubleshooting-&-FAQ.md)** for error codes, edge cases, and diagnostics reporting.
