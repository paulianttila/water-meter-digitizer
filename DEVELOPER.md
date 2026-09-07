# Developer Guide & Architecture

Welcome to the **Water Meter Digitizer** codebase. This document is a comprehensive guide for developers working on or extending the project.

---

## Table of Contents

1. [Architecture & Pipeline Overview](#architecture--pipeline-overview)
2. [Codebase Organization](#codebase-organization)
3. [Core Subsystems & Key Algorithms](#core-subsystems--key-algorithms)
   - [1. Image Acquisition & Pre-processing](#1-image-acquisition--pre-processing)
   - [2. Affine Alignment & Reference Matching](#2-affine-alignment--reference-matching)
   - [3. Neural Network Inference (TFLite)](#3-neural-network-inference-tflite)
   - [4. Digitizer Postprocessing & Predecessors](#4-digitizer-postprocessing--predecessors)
   - [5. Consistency Checking & Value Persistence](#5-consistency-checking--value-persistence)
   - [6. Web UI & Setup Wizard (NiceGUI)](#6-web-ui--setup-wizard-nicegui)
4. [Development Environment Setup](#development-environment-setup)
5. [Running the Application Locally](#running-the-application-locally)
6. [Testing Guide](#testing-guide)
7. [Code Quality & Style Guidelines](#code-quality--style-guidelines)

---

## Architecture & Pipeline Overview

The system processes camera captures into structured meter values via a multi-stage pipeline:

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
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                  ┌──────────────────────┐
   │   Digital Counter    │                  │    Analog Needle     │
   │      CNN Models      │                  │      CNN Models      │
   │ (digital/digital100) │                  │   (analog/analog100) │
   └──────────┬───────────┘                  └──────────┬───────────┘
              │                                         │
              └────────────────────┬────────────────────┘
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
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                  ┌──────────────────────┐
   │     REST API         │                  │       NiceGUI        │
   │   `/meter?format=`   │                  │  Live Meter & Wizard │
   └──────────────────────┘                  └──────────────────────┘
```

---

## Codebase Organization

```
water-meter-digitizer/
├── config/                      # Sample runtime config and reference images
├── src/                         # Main application source code
│   ├── main.py                  # Entrypoint: loads config, starts FastAPI & NiceGUI
│   ├── configuration.py         # INI configuration parser and dataclasses
│   ├── data_classes.py          # Domain data models (MeterConfig, HealthResponse, etc.)
│   ├── readout.py               # Readout orchestration and result aggregator
│   ├── callbacks.py             # Event/action hooks across GUI and backend
│   ├── previous_value.py        # Thread-safe persistence for last valid reading
│   │
│   ├── cnn/                     # Google LiteRT / TFLite neural network runners
│   │   ├── base.py              # Base CNN wrapper with async offloading
│   │   ├── pool.py              # Thread-safe InterpreterPool and metrics telemetry
│   │   ├── digital_counter_cnn.py # Digital odometer drum & LCD digit models
│   │   └── analog_needle_cnn.py   # Circular analog dial needle models
│   │
│   ├── processor/               # Image processing and digitizing logic
│   │   ├── image.py             # Pillow/OpenCV alignment, transformation, cropping
│   │   └── digitizer.py         # Post-processing, predecessor chains, evaluation
│   │
│   ├── storage/                 # Historical readings retention & database
│   │   ├── __init__.py          # Dual-mode persistence factory
│   │   ├── base.py              # BaseStorageBackend abstract interface
│   │   ├── sqlite.py            # SQLite/SQLAlchemy persistent storage
│   │   └── memory.py            # In-memory circular buffer fallback storage
│   │
│   ├── poller/                  # Background scheduling subsystem
│   │   └── scheduler.py         # Async scheduler for periodic automated readouts
│   │
│   ├── mqtt/                    # IoT & Home Assistant integration
│   │   └── client.py            # MQTT publisher with Home Assistant Auto-Discovery
│   │
│   ├── gui/                     # Web interface built with NiceGUI
│   │   ├── frontend.py          # Top-level page router and theme
│   │   ├── page_meter.py        # Live meter readout display page
│   │   ├── page_setup.py        # Interactive 9-step setup wizard
│   │   ├── step_base.py         # Base class for wizard steps (spinners, callbacks)
│   │   ├── step_download.py     # Wizard: Camera URL capture & offline placeholder
│   │   ├── step_initial_rotate.py # Wizard: Coarse 90° rotation
│   │   ├── step_draw_refs.py    # Wizard: Reference marker drawing
│   │   ├── step_adjust.py       # Wizard: Fine rotation, alignment, filter tuning
│   │   ├── step_draw_digital_rois.py # Wizard: Digital ROI bounding box placement
│   │   ├── step_draw_analog_rois.py  # Wizard: Analog ROI bounding box placement
│   │   ├── step_meters.py       # Wizard: Multi-meter definitions and formatting
│   │   ├── step_services.py     # Wizard: Poller, MQTT, and storage settings
│   │   └── step_final.py        # Wizard: Config saving & verification
│   │
│   ├── web/templates/           # Dashboard HTML/CSS templates
│   │   ├── index.html           # Main dashboard, API explorer, diagnostics modal
│   │   ├── reload.html          # Configuration reload status feedback page
│   │   └── roi.html             # Aligned ROI verification view
│   │
│   └── utils/                   # General utilities
│       ├── download.py          # Async HTTP client for camera frame fetching
│       ├── image.py             # Base64 conversions, drawing, dimensions, alignment
│       ├── security.py          # Path validation and LFI protection
│       ├── diagnostics.py       # Telemetry aggregator for /health endpoint
│       ├── math.py              # Zero-crossing & predecessor mathematical helpers
│       └── decorators.py        # Timing and logging decorators
│
├── tests/                       # Automated test suite
│   ├── unit/                    # Unit tests for algorithms, parser, processors, pool
│   └── integration/             # Tavern integration tests with live HTTP/MQTT requests
│
├── pyproject.toml               # Build metadata, ruff & bandit configuration
├── requirements.in              # Direct production dependencies
├── requirements.txt             # Pinned runtime dependencies
├── run_tests.sh                 # Unified test & QA execution script
└── Dockerfile                   # Production multi-arch container definition
```

---

## Core Subsystems & Key Algorithms

### 1. Image Acquisition & Pre-processing
- Handled by `utils/download.py` and `processor/image.py`.
- Supports direct HTTP camera streams, local files (`file://`), and byte size thresholds (`MinSize`) to reject corrupted frames.
- Optional pre-alignment crop and resize (`[Crop]`, `[Resize]`) reduce memory and processing overhead.

### 2. Affine Alignment & Reference Matching
- The system uses 3 reference marker sub-images (`RefImage`) placed on fixed visual landmarks of the meter dial.
- In `processor/image.py`, OpenCV template matching locates these 3 markers in the captured frame.
- An affine transformation matrix is computed (`cv2.getAffineTransform`) to warp and rotate the frame back to canonical coordinate space, compensating for camera vibrations or physical movement.

### 3. Neural Network Inference & Interpreter Pooling
The project supports four distinct model architectures:

| Model Type | Outputs | Architecture / Target |
|---|---|---|
| `analog` | 2 | Continuous `sin`/`cos` needle angle regression (0–10) |
| `analog100` | 100 | High-resolution classification across 100 angular bins (0–9.99) |
| `digital` | 11 | Classification for 0–9 digits plus an 11th class for half-transition/invalid |
| `digital100` | 100 | Continuous 0–99 classification for rolling odometer drums |

- **LiteRT Runtime**: Models are executed via `ai_edge_litert` (Google LiteRT, with `tflite_runtime` and `tensorflow.lite` fallbacks) in `src/cnn/`.
- **`InterpreterPool` (`src/cnn/pool.py`)**:
  - Model interpreters are pooled per model file using `queue.Queue` guarded by `threading.RLock`.
  - Dynamically scales instances up to `max_size` (defaulting to CPU core count) to eliminate tensor clobbering across concurrent worker threads.
  - Automatically records high-resolution inference timing, min/max/average latency, and pool utilization metrics exposed via `/health`.
  - Provides async interfaces (`readout_async`, `readout_with_confidence_async`, `process_async`) offloading CPU-bound inference to worker threads via `asyncio.to_thread`.

### 4. Digitizer Postprocessing & Predecessors
- Physical odometer drums transition gradually. When a lower digit is near 9 (e.g. `9.8`), the next higher digit may be halfway between numbers (e.g. between `3` and `4`).
- `processor/digitizer.py` implements **predecessor evaluation**:
  - Higher-significance digits inspect the value of the immediate lower-significance predecessor.
  - If the predecessor has not crossed the zero-boundary, the higher digit is rounded down.
  - If the predecessor has crossed zero, the higher digit is rounded up.
- For analog needles, multi-dial carry-down rules and return-to-9 logic resolve ambiguities across cascading multiplier dials (e.g. `x1000` $\rightarrow$ `x100` $\rightarrow$ `x10` $\rightarrow$ `x1`).

### 5. Consistency Checking & Value Persistence
- `processor/digitizer.py` checks rate limits against previous values:
  - Decreasing values can be rejected (`AllowNegativeRates = False`).
  - Sudden spikes exceeding `MaxRateValue` are flagged as invalid.
- Persisted previous values are managed by `previous_value.py` in an INI file with timestamp-based max age expiration (`PreValueFromFileMaxAge`).

### 6. Storage & Telemetry Architecture
- **Dual-Mode Persistence Factory**: `src/storage/__init__.py` dynamically provides `SQLAlchemyStorageBackend` (SQLite by default) or `MemoryStorageBackend` (in-memory circular buffer fallback if `/data` is on a read-only filesystem or SQLite initialization fails).
- **Auto-Pruning & Retention**: Automatically purges records older than `retention_days` and enforces memory caps (`max_memory_mb`) with background SQLite vacuuming.
- **Diagnostics Subsystem**: `src/utils/diagnostics.py` aggregates process RSS memory, uptime, camera reachability latency, and model inference statistics into `/health`.

### 7. Background Polling & MQTT Auto-Discovery
- **Scheduler**: Async background poller (`src/poller/scheduler.py`) periodically runs meter readouts at configured intervals without requiring external cron daemons.
- **Home Assistant MQTT Discovery**: `src/mqtt/client.py` publishes Home Assistant JSON configuration payloads under `homeassistant/sensor/<node_id>/<meter_id>/config` with `device_class: water` and `state_class: total_increasing`.
- **Granular Publication**: Sends meter values, sub-digit raw arrays, quality status (`good`, `warning`, `uncertain`), and model confidence percentages to configured MQTT topics.

### 8. Web UI & Setup Wizard (NiceGUI & FastAPI)
- Implemented with a hybrid architecture combining **FastAPI** (REST API, diagnostics, dashboard templates) and **NiceGUI** (Vue/Quasar interactive frontend).
- The setup page (`page_setup.py`) features an interactive canvas with real-time mouse coordinate tracking, SVG ROI drawing overlays, offline placeholder fallback on camera timeout, and live inference preview on cropped ROIs.
- The main landing dashboard (`src/web/templates/index.html`) is a glassmorphic single-page application with live diagnostics telemetry, interactive API console, and historical consumption visualizers.

---

## Development Environment Setup

### Prerequisites
- **Python 3.11** (Supported natively across macOS, Linux, and Windows).
- **uv** package manager ([astral.sh/uv](https://astral.sh/uv))
- **libGL / OpenCV dependencies** (standard system libraries)

### Setup Virtual Environment with `uv`

`uv` automatically manages Python 3.11 and all dependencies:

```bash
# Clone repository
git clone https://github.com/paulianttila/water-meter-digitizer.git
cd water-meter-digitizer

# Create virtual environment and synchronize all dependencies
uv sync

# (Optional) Activate the virtual environment in your shell
source .venv/bin/activate
```

---

## Running the Application Locally

### Running the Server

```bash
# Set configuration path
export CONFIG_FILE=$(pwd)/test_config/config.ini

# Start the application using uv
cd src
uv run python main.py
```

The web interface will be accessible at `http://localhost:3000`.

### Debugging with VS Code / debugpy

A VS Code launch configuration can be set up in `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Water Meter Digitizer",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "cwd": "${workspaceFolder}/src",
      "env": {
        "CONFIG_FILE": "${workspaceFolder}/test_config/config.ini"
      },
      "console": "integratedTerminal"
    }
  ]
}
```

---

## Testing Guide

### Running Unit Tests

Unit tests are written with `pytest` and verify mathematical helpers, configuration parsing, predecessor logic, CNN postprocessing, and GUI step handlers.

```bash
# Run all unit tests with uv
uv run pytest tests/unit -v

# Run a specific test module
uv run pytest tests/unit/test_predecessor.py -v
```

### Running Integration Tests (Tavern)

Integration tests spin up the application and execute REST API assertions:

```bash
export CONFIG_FILE=$(pwd)/test_config/config.ini
./run_tests.sh
```

### Running All QA Checks

The `./run_tests.sh` helper supports several flags:
- `./run_tests.sh -u`: Run unit tests only (`uv run pytest tests/unit`).
- `./run_tests.sh -s`: Run static analysis only (`ruff`, `black`, `bandit`).
- `./run_tests.sh -a`: Run full test app, Tavern integration tests, unit tests, and static analysis.

---

## Code Quality & Style Guidelines

### Formatting & Linting
- **Formatter**: `black` with an 88-character line length.
- **Linter**: `ruff` (configured under `[tool.ruff.lint]` in `pyproject.toml`).
- **Security**: `bandit` (configured in `pyproject.toml`).

```bash
# Auto-format code
uv run black .

# Check lint rules
uv run ruff check .

# Run security checks
uv run bandit -c pyproject.toml -r .
```

### Compatibility Guidelines
- **Python 3.11+ Standard**: Leverage modern Python 3.11 features, including native pipe union type syntax (`int | None`, `str | None`).
- **NiceGUI Scope**: Wrap dynamically created elements in explicit container context managers (`with self.container:`) to prevent widgets from leaking into the root page slot.
- **Error Handling & Thread Safety**: Protect shared state (configuration, storage, previous value files, interpreter pools) with appropriate locks (`threading.Lock` / `threading.RLock`) and gracefully recover from hardware/network timeouts without crashing background event loops.
