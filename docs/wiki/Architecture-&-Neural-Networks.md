# 🔬 Architecture, Neural Networks & Pipeline Deep Dive

[🏠 Wiki Home](Home.md) • [◀ Previous: Configuration & Storage Manual](Configuration-&-Storage-Manual.md) • [Next: Development & Testing Guide ▶](Development-&-Testing.md)

---

This document details the internal system architecture, decoupled module design, 6-stage runtime execution pipeline, neural network model specifications, thread-safe LiteRT pooling, SQLite WAL concurrency, and predecessor roll-over mathematics.

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

### 2. Thread-Safe `InterpreterPool` & Resource Sizing
Standard TensorFlow Lite interpreters are not thread-safe. The digitizer implements an `InterpreterPool` to manage concurrent inference without lock contention:

| Host Environment | `PoolSize` | Approx. RAM Usage | Concurrency Behavior |
| :--- | :---: | :---: | :--- |
| **Raspberry Pi Zero 2 W** (512 MB RAM) | `1` | ~20 MB | Sequential inference; lowest memory footprint. |
| **Raspberry Pi 4 / 5** (1 GB–8 GB RAM) | `2` | ~40 MB | Concurrent REST `/readout` + background Poller. |
| **x86_64 Server / Docker** | `4` | ~80 MB | High-throughput concurrent multi-meter processing. |

- Worker instances utilize thread-safe `acquire()` / `release()` context managers.
- Telemetry monitors real-time $p50$, $p95$, and average inference latency.

---

## 💾 SQLite Concurrency & WAL Locking Model

The persistent storage engine (`SQLiteStorage`) is optimized for embedded edge storage:

- **Write-Ahead Logging (`WAL` Mode)**: Readers never block writers, and writers never block readers. Concurrent UI reads and REST queries proceed simultaneously with ongoing poller writes.
- **Write Serialization Mutex**: Database write transactions are serialized using an internal threading mutex (`StorageBackend.lock`) to prevent `SQLITE_BUSY` contention during bursts.
- **Memory Fallback**: If the storage path is mounted read-only (e.g. read-only container root), the system automatically degrades to `MemoryStorage` with warning telemetry.

---

## 🌐 Network Resilience & Outage Handling

- **Exponential Retry Backoff**: When the camera source or MQTT broker becomes temporarily unreachable, background workers apply exponential backoff (up to `RetryIntervalSeconds`) without crashing the application shell.
- **Baseline Reading Fallback (`prevalue.ini`)**: If a camera frame capture fails or OCR confidence drops below threshold, the consistency engine preserves the last known valid state from disk, preventing false zero readings or corrupted consumption spikes.

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

[🏠 Wiki Home](Home.md) • [◀ Previous: Configuration & Storage Manual](Configuration-&-Storage-Manual.md) • [Next: Development & Testing Guide ▶](Development-&-Testing.md)
