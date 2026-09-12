# Welcome to the Water Meter Digitizer Wiki

The **Water Meter Digitizer** is an edge-optimized AI vision system that reads analog needle dials and mechanical odometer digits from water, gas, or electricity meters using low-cost camera sensors (e.g. ESP32-CAM or network cams) and lightweight neural network inference via Google LiteRT (TensorFlow Lite).

---

## 🗺️ Documentation Sitemap

### 🚀 Getting Started
- **[[Installation-&-Deployment]]**: Deploy via Docker, Docker Compose, Raspberry Pi, or bare metal with `uv`.
- **[[Hardware-&-Camera-Setup]]**: Best practices for camera placement, ESP32-CAM configuration, lighting, and glare suppression.

### 🛠️ User Guide & Setup
- **[[Web-Dashboard-Tour]]**: Exploring the glassmorphic web UI, live metrics, consumption charts, and Time Machine frame scrubber.
- **[[Setup-Wizard-Guide]]**: Step-by-step visual calibration wizard (9 steps from image capture to live deployment).
- **[[Zero-Flow-Leak-Detection]]**: Continuous zero-flow tracking, leak alert thresholds, and Home Assistant binary sensor notifications.

### 🏡 Integrations & Connectivity
- **[[Smart-Home-Integrations]]**: Native Home Assistant MQTT Discovery, openHAB MQTT Binding, Node-RED, and REST/Webhook connectivity.
- **[[MQTT-Topic-&-Payload-Reference]]**: MQTT topic hierarchy, JSON readouts, retained topics, and state broadcasting.
- **[[REST-API-Reference]]**: Comprehensive REST API reference with curl examples and OpenAPI schemas.

### ⚙️ Configuration & Storage
- **[[Configuration-Reference]]**: Detailed parameter-by-parameter `config.ini` documentation.
- **[[Config-Backups-&-Version-Control]]**: Automated safety backups, 1-click Undo, named checkpoints, and line-by-line diff inspection.
- **[[Storage-&-Snapshot-Pruning]]**: Dual storage architecture (SQLite + In-Memory), retention policies, and WebP frame compression.

### 🔬 Developer Architecture & Algorithms
- **[[Architecture-&-Pipeline]]**: High-level component architecture and end-to-end dataflow pipeline.
- **[[Neural-Network-Models]]**: CNN model types, LiteRT inference pooling (`InterpreterPool`), and benchmarks.
- **[[Digit-Roll-Over-&-Extended-Resolution]]**: Predecessor consistency math, roll-over boundary correction, and fractional sub-digit calculation.
- **[[Development-&-Testing]]**: Setting up local development with `uv`, executing unit, Playwright UI, and Tavern integration test suites.

### ❓ Troubleshooting & Support
- **[[Troubleshooting-&-FAQ]]**: Comprehensive diagnostics matrix, error codes, and frequently asked questions.

---

## ⚡ Quick Architecture Overview

```
                      ┌─────────────────────────┐
                      │    Camera / File URL    │
                      └────────────┬────────────┘
                                   │ HTTP / File Download
                                   ▼
                      ┌─────────────────────────┐
                      │     ImageProcessor      │
                      │  - Initial Rotation     │
                      │  - Affine Alignment     │
                      │  - Contrast/Brightness  │
                      │  - Cut ROI Sub-images   │
                      └────────────┬────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
    ┌──────────────────────┐                ┌──────────────────────┐
    │   Digital Counter    │                │    Analog Needle     │
    │      CNN Models      │                │      CNN Models      │
    │ (digital/digital100) │                │   (analog/analog100) │
    └──────────┬───────────┘                └──────────┬───────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   │ Raw CNN Predictions
                                   ▼
                      ┌─────────────────────────┐
                      │    DigitizerProcessor   │
                      │  - Predecessor Roll-fix │
                      │  - Extended Resolution  │
                      │  - Rate Consistency Chk │
                      │  - Previous Value File  │
                      └────────────┬────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
    ┌──────────────────────┐                ┌──────────────────────┐
    │     REST API & MQTT  │                │   Interactive Web UI │
    │   `/meter` & Broker  │                │  Dashboard & Wizard  │
    └──────────────────────┘                └──────────────────────┘
```
