# Architecture & Pipeline Deep Dive

This document details the internal architecture, module decoupling, and end-to-end execution pipeline of the **Water Meter Digitizer**.

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

## 🔄 End-to-End Processing Pipeline

1. **Image Download**: `ImageProcessor.download_image` retrieves raw bytes from camera source URL.
2. **Pre-processing & Enhancement**:
   - Initial rotation applied (`ImageProcessor.rotate_image`).
   - 3-point affine transformation matches visual reference markers (`ref0`, `ref1`, `ref2`).
   - Glare suppression (CLAHE, Telea Inpainting, illumination normalization).
   - Histogram AutoContrast full-frame stretching.
   - LUT-accelerated non-linear Gamma tone curve and Tonal adjustments (contrast, brightness, saturation).
   - CIELAB Luminance Unsharp Masking with noise threshold coring.
3. **ROI Segmentation & Pre-Inference Enhancements**:
   - Crops bounding boxes for individual digital counters and analog dials.
   - Optionally applies individual ROI luminance unsharp masking and autocontrast.
4. **Neural Inference & Negative Sign Detection**:
   - Submits normalized ROI tensor batches to `InterpreterPool` worker threads running Google LiteRT runtime.
   - If enabled (`DetectNegativeSign`), morphological and aspect-ratio analysis detects minus signs (`-`) on digital ROIs displaying negative flow.
5. **Post-processing & Predecessor Correction**:
   - `DigitizerProcessor` resolves ambiguous half-turned digits using adjacent lower-order dials.
   - Calculates fractional extended resolution.
6. **Data Integrity & Persistence**:
   - Rate consistency check validates flow magnitude against previous baseline.
   - Saves record and WebP compressed frame to `StorageBackend`.
   - Dispatches live values to MQTT broker topics.
