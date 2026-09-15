# Welcome to the Water Meter Digitizer Wiki

The **Water Meter Digitizer** is an edge-optimized AI vision system that reads analog needle dials and mechanical odometer digits from water, gas, or electricity meters using low-cost camera sensors (e.g. ESP32-CAM or network cams) and lightweight neural network inference via Google LiteRT (TensorFlow Lite).

---

## 🗺️ Documentation Sitemap

### 🚀 Getting Started & Calibration
- **[[Getting-Started-&-Hardware]]**: Deploy via Docker, Docker Compose, Raspberry Pi (ARM64), hardware mounting, camera selection, and lighting/glare mitigation.
- **[[Setup-Wizard-&-Calibration]]**: Step-by-step 9-step visual calibration wizard, marker alignment rules, canvas shortcuts, and ROI setup.
- **[[Dashboard-&-Features-Guide]]**: Live monitoring dashboard, Time Machine historical frame scrubber, Zero-Flow continuous leak detection, and Mock Camera Studio.

### 🏡 Integrations & Automation
- **[[Integrations-&-API-Reference]]**: Native Home Assistant MQTT Auto-Discovery, openHAB, complete MQTT topic schemas, and REST API reference.

### ⚙️ Configuration & Storage
- **[[Configuration-&-Storage-Manual]]**: Complete `config.ini` manual, environment variables, automated configuration backups, Undo, and SQLite/WebP retention policies.

### 🔬 Architecture & Deep Dives
- **[[Architecture-&-Neural-Networks]]**: 6-Stage runtime pipeline, LiteRT neural models (`InterpreterPool`), and predecessor rollover consistency mathematics.

### 🧪 Development & Testing
- **[[Development-&-Testing]]**: Setting up local development with `uv`, executing unit, Playwright UI, and Tavern integration test suites, and release build workflows.

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

---

## 👏 Kudos & Acknowledgments

Special thanks to **[jomjol](https://github.com/jomjol)** for providing the pre-trained neural network `.tflite` models used in this project:
- **[neural-network-analog-needle-readout](https://github.com/jomjol/neural-network-analog-needle-readout)** (Analog needle angle estimation models)
- **[neural-network-digital-counter-readout](https://github.com/jomjol/neural-network-digital-counter-readout)** (Digital drum digit counter classification models)
