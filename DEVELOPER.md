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
   - [6. Storage & Telemetry Architecture](#6-storage--telemetry-architecture)
   - [7. Background Polling & MQTT Auto-Discovery](#7-background-polling--mqtt-auto-discovery)
   - [8. Zero-Flow Tracking & Continuous Leak Detection](#8-zero-flow-tracking--continuous-leak-detection)
   - [9. Web UI & Setup Wizard (NiceGUI & FastAPI)](#9-web-ui--setup-wizard-nicegui--fastapi)
   - [10. Configuration History & Backups](#10-configuration-history--backups)
   - [11. Single Source of Truth (SSoT) Versioning](#11-single-source-of-truth-ssot-versioning)
   - [12. Historical Snapshots & Time Machine Archival](#12-historical-snapshots--time-machine-archival)
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
│   ├── main.py                  # Entrypoint: orchestrator, startup lifecycle, and service wiring
│   ├── version.py               # Single Source of Truth (SSoT) application versioning module
│   ├── configuration.py         # INI configuration parser and dataclasses
│   ├── data_classes.py          # Domain data models (MeterConfig, HealthResponse, etc.)
│   ├── callbacks.py             # Event/action hooks protocol across GUI and backend
│   ├── previous_value.py        # Thread-safe persistence for last valid reading
│   ├── config_history.py        # Backup management, unified diffs, and snapshots
│   │
│   ├── api/                     # Modular FastAPI REST APIRouters
│   │   ├── routes_meter.py      # /meter, /image/*, /roi, /set_previous_value, /get_previous_values
│   │   ├── routes_health.py     # /health, /healthcheck, asset directory validation
│   │   ├── routes_services.py   # /poller/*, /mqtt/*, /leak/*
│   │   ├── routes_history.py    # /history/consumption, /history/readings, /history/stats
│   │   └── routes_system.py     # /gui redirect, /version, /reload
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
│   │   ├── sql.py               # SQLAlchemy / SQLite persistent storage backend
│   │   ├── memory.py            # In-memory circular buffer fallback storage
│   │   └── seed.py              # Synthetic readings generator for historical test data
│   │
│   ├── poller/                  # Background scheduling subsystem
│   │   └── scheduler.py         # Async scheduler for periodic automated readouts
│   │
│   ├── leak/                    # Zero-flow tracking & continuous leak detection
│   │   ├── __init__.py          # Package exports (ZeroFlowTracker, LeakState, LeakEvent)
│   │   ├── models.py            # LeakState, LeakEvent, and ZeroFlowStatus models
│   │   └── tracker.py           # Noise-resilient tracking, debounced resolution, history
│   │
│   ├── mqtt/                    # IoT & Home Assistant integration
│   │   ├── client.py            # MQTT publisher client
│   │   └── discovery.py         # Home Assistant MQTT discovery payload generator
│   │
│   ├── gui/                     # Web interface built with NiceGUI
│   │   ├── frontend.py          # Top-level page router and theme
│   │   ├── callbacks_impl.py    # Callbacks implementation connecting GUI to backend
│   │   ├── dialog_benchmark.py  # Model benchmark evaluation modal dialog
│   │   ├── theme.py             # Reusable design tokens and CSS class constants
│   │   ├── page_meter.py        # Live meter readout display page
│   │   ├── page_config.py       # Configuration editor with backup history & 1-click undo
│   │   ├── page_setup.py        # Interactive 9-step setup wizard
│   │   ├── page_services.py     # Background services & telemetry dashboard
│   │   ├── page_previous_values.py # Calibration & baseline previous values page
│   │   ├── page_api_console.py  # Interactive REST API explorer and console
│   │   ├── page_about.py        # System diagnostic & version info
│   │   ├── page_help.py         # In-app setup & configuration documentation
│   │   ├── components/          # Reusable dashboard and telemetry cards
│   │   ├── step_base.py         # Base class for wizard steps (spinners, callbacks)
│   │   ├── step_download.py     # Wizard: Camera URL capture & offline placeholder
│   │   ├── step_initial_rotate.py # Wizard: Coarse 90° rotation
│   │   ├── step_draw_refs.py    # Wizard: Reference marker drawing
│   │   ├── step_adjust.py       # Wizard: Fine rotation, alignment, filter tuning
│   │   ├── step_draw_rois_base.py # Base class for interactive ROI drawing & SVG canvas
│   │   ├── step_draw_digital_rois.py # Wizard: Digital ROI bounding box placement
│   │   ├── step_draw_analog_rois.py  # Wizard: Analog ROI bounding box placement
│   │   ├── step_meters.py       # Wizard: Multi-meter definitions and formatting
│   │   ├── step_services.py     # Wizard: Poller, MQTT, and storage settings
│   │   └── step_final.py        # Wizard: Config saving & verification
│   │
│   ├── web/static/              # Static assets (favicons, touch icons, branding)
│   │
│   └── utils/                   # General utilities
│       ├── download.py          # Async HTTP client for camera frame fetching
│       ├── image.py             # Base64 conversions, drawing, dimensions, alignment
│       ├── security.py          # Path validation and LFI protection
│       ├── diagnostics.py       # Telemetry aggregator for /health endpoint
│       ├── math.py              # Zero-crossing & predecessor mathematical helpers
│       ├── cache.py             # In-memory LRU / TTL image caching
│       └── file.py              # File loading utilities
│
├── tests/                       # Automated test suite
│   ├── unit/                    # Unit tests for algorithms, parser, processors, pool, version
│   └── integration/             # Tavern API & Playwright Web UI integration tests
│       └── ui/                  # Playwright browser integration tests for Web UI & wizard
│
├── pyproject.toml               # Project metadata, dependencies, and tool configurations
├── uv.lock                      # Deterministic cross-platform dependency lockfile
├── run_tests.sh                 # Unified test & QA execution script
└── Dockerfile                   # Production multi-arch container definition
```

---

## Core Subsystems & Key Algorithms

### 1. Image Acquisition & Pre-processing
- Handled by `utils/download.py` and `processor/image.py`.
- Supports direct HTTP camera streams, local files (`file://`), and byte size thresholds (`MinSize`) to reject corrupted frames.
- Optional pre-alignment crop and resize (`[Crop]`, `[Resize]`) reduce memory and processing overhead.
- **Image Adjustments & Glare Suppression**:
  - Color, brightness, contrast, sharpness, and autocontrast histogram stretching.
  - **Specular Reflection & Glare Suppression**: Four computer vision filters (`clahe`, `inpaint`, `illumination_normalize`, `combined`) to suppress saturated flash hotspots and glass reflections across the full frame or on individual digit/dial pointer crops.


### 2. Affine Alignment & Reference Matching
- The system uses 3 reference marker sub-images (`RefImage`) placed on fixed visual landmarks of the meter dial.
- In `processor/image.py`, OpenCV template matching locates these 3 markers in the captured frame.
- An affine transformation matrix is computed (`cv2.getAffineTransform`) to warp and rotate the frame back to canonical coordinate space, compensating for camera vibrations or physical movement.

### 3. Neural Network Inference & Interpreter Pooling
The project supports four distinct model architectures, organized in categorized subdirectories under `/config/neuralnets/`:

```
config/neuralnets/
├── digital/
│   ├── class100/           # 100-class fractional digit classifiers (e.g. dig-class100_0168_s2_q.tflite)
│   ├── class11/            # 11-class discrete digit classifiers (0-9 + NaN)
│   ├── continuous/         # Continuous regression models
│   └── legacy/             # Monolithic v6.2.0 models
└── analog/
    ├── class100/           # Discrete needle angle classifier
    ├── continuous/         # Continuous needle angle regression
    └── legacy/             # Monolithic v6.2.0 models
```

| Model Type | Outputs | Directory | Architecture / Target |
|---|---|---|---|
| `analog` | 2 | `analog/continuous/` | Continuous `sin`/`cos` needle angle regression (0–10) |
| `analog100` | 100 | `analog/class100/` | High-resolution classification across 100 angular bins (0–9.99) |
| `digital` | 11 | `digital/class11/` | Classification for 0–9 digits plus an 11th class for half-transition/invalid |
| `digital100` | 100 | `digital/class100/` | Continuous 0–99 classification for rolling odometer drums |

- **Quantized Models (`_q.tflite` / `⚡ Int8`)**: Models with `_q` suffix use 8-bit integer quantization, offering 3x–4x smaller disk/RAM footprints and significantly faster inference on edge CPUs (such as Raspberry Pi).
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

### 8. Zero-Flow Tracking & Continuous Leak Detection
- **Subsystem (`src/leak/`)**: Implements dual-condition zero-flow tracking to detect non-zero continuous water flow over sustained intervals (e.g. running toilets or open fixtures).
- **Dual-Condition Leak Triggering**: Flow must remain continuous for at least `ContinuousFlowHours` (default: 2.0h) **AND** accumulate volume $\ge$ `MinLeakVolume` (default: 0.010 m³ / 10 L), eliminating false alarms from drum/pointer optical jitter ($\pm 0.0001\text{ m}^3$).
- **Debounced Auto-Resolution**: When flow stops, requires $K$ consecutive zero-flow readings (`DebounceCount`, default: 2) before resetting state to `NORMAL` and archiving a `LeakEvent` with start/end timestamps, duration, and total lost volume.
- **Optical CNN Noise Mitigation**: Rejects negative deltas, skips low-confidence/uncertain reads, clamps spurious reading spikes exceeding `MaxRateValue`, and watchdog-resets continuous timers during long camera/network outages (> 2h).
- **Home Assistant & REST Integration**: Auto-discovers binary leak sensors, continuous flow duration sensors, and state sensors via MQTT, plus exposes `/leak/status` and `/leak/reset` REST endpoints.

### 9. Web UI & Setup Wizard (NiceGUI & FastAPI)
- Implemented with a unified architecture combining **FastAPI** (providing the pure REST API layer: `/meter`, `/health`, `/poller`, `/mqtt`, `/history`, etc.) and **NiceGUI** (serving the complete modern web application directly at the root `/`).
- The Web Dashboard provides complete operational control: live meter telemetry, consumption charts, neural network model inspector, zero-flow leak tracking, baseline values manager, raw API console, visual and raw INI configuration editor with safety backups, and the 9-step interactive setup wizard (`page_setup.py`).
- A backward-compatible redirect on `/gui` redirects to `/` for seamless navigation.

### 10. Configuration History & Backups
- **Subsystem (`src/config_history.py`)**: `ConfigHistoryManager` automates versioned configuration backups, manual snapshots, and change tracking.
- **Dedicated Storage**: Backups are preserved in `/config/backups/` subfolder using timestamped conventions (`config.ini_YYYYMMDD_HHMMSS[_Tag].bak`).
- **Safety Snapshots**: Every restore or save operation captures an automatic safety snapshot before modifying active files on disk.
- **Visual Diff Engine**: Computes unified line-by-line diffs (`difflib.unified_diff`) between active `config.ini` and any historical backup.
- **Thread Safety**: All configuration file reads, writes, snapshots, and diff operations are guarded by a reentrant lock (`_config_lock = threading.RLock()` in `src/main.py`) to prevent deadlocks and race conditions.

### 11. Single Source of Truth (SSoT) Versioning
- **Central Authority (`pyproject.toml`)**: The project version is canonically defined once in `pyproject.toml` (`[project] version = "1.0.0"`).
- **Runtime Resolution (`src/version.py`)**: The `__version__` variable dynamically reads `pyproject.toml` using `tomllib` (Python 3.11 standard library), with fallbacks to `importlib.metadata.version("water-meter-digitizer")` when running from an installed package, and a static `FALLBACK_VERSION` if uninstalled in standalone mode.
- **Unified Propagation**: All components consume `src.version.__version__` directly:
  - **FastAPI Application**: Injected into the root application instance (`app.version`), `/version` endpoint, and `/health` diagnostics.
  - **MQTT & Home Assistant Discovery**: Published in device software version telemetry (`sw_version`) in discovery payloads and status topics.
  - **Web Dashboard & UI**: Rendered in the header banner, footer, and sidebar.

### 12. Historical Snapshots & Time Machine Archival
- **Subsystem Architecture (`src/gui/components/time_machine_card.py`, `src/storage/`)**: Provides visual historical inspection, anomaly debugging, and before/after optical validation.
- **Storage Strategies & Smart Tiering**:
  - `smart_tiered`: Stores uncompressed or high-quality full camera frames (`frame_{id}_{ts}.webp`) for recent readings (e.g. 2 days), and down-tiers older frames into compact horizontal ROI composite strips (`strip_{id}_{ts}.webp`) spanning the full ROI array to preserve optical digits while using < 5 KB per frame.
  - `change_only`: Only archives frames when flow is detected or when readings change.
  - `full_frames` / `roi_strips_only`: Forces fixed storage format across the retention lifecycle.
  - `always_save_on_anomaly`: Always captures high-resolution full frames whenever recognition errors or low confidence scores are encountered.
- **Resilient Multi-Stage Lookup (`src/storage/sql.py`)**:
  - Fast-path in-memory ring buffer lookup (`self._snapshot_ring_buffer`).
  - Database row lookup (`frame_path`, `frame_type`, `has_blob`).
  - Canonical and relative path resolution with fallback glob matching across candidate directories (`/data/snapshots`, `/config/data/snapshots`, current working directory).
- **Frontend NiceGUI Architecture**:
  - Chronological scrubber slider (`0` = Oldest past, `N-1` = Latest live) with endpoint timestamp indicators.
  - Decoupled static controls container to eliminate UI destruction or focus loss during scrubbing and time-lapse playback.
  - Standardized `360px` image viewport height ensuring timestamps under Historical and Live frames remain horizontally aligned regardless of aspect ratio or ROI strip display.
  - Real-time 100ms countdown timer badge (`⏱️ Next: X.Xs`) with configurable playback speeds (0.5s to 10s).
  - Integrated detection cards for Digital Drums and Analog Dials linking individual digit/pointer confidence percentages directly to the active Historical Frame.

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
# Set configuration path (optional when using ./config/config.ini)
export CONFIG_FILE=$(pwd)/config/config.ini

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
        "CONFIG_FILE": "${workspaceFolder}/config/config.ini"
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
uv run python -m pytest tests/unit -v

# Run a specific test module
uv run python -m pytest tests/unit/test_predecessor.py -v
```

### Running Integration Tests (Tavern REST API)

Integration tests spin up the application, MQTT broker, and execute REST API assertions with Tavern:

```bash
./run_tests.sh -i
```

### Running Web UI Integration Tests (Playwright)

Browser-level UI integration tests are written with `pytest-playwright` and test NiceGUI components, top-level navigation, 9-step calibration wizard workflows, comparison modals, and the configuration editor:

```bash
# Install Chromium browser binary (one-time setup)
uv run playwright install chromium

# Run all Web UI tests headless
uv run python -m pytest tests/integration/ui/ -v

# Run with headed browser for live visual observation
uv run python -m pytest tests/integration/ui/ --headed

# Run via test runner script
./run_tests.sh -w
```

### Running All QA Checks

The `./run_tests.sh` helper supports several flags:
- `./run_tests.sh` (no args): Run unit tests, Web UI tests, and Tavern integration tests.
- `./run_tests.sh -u, --unit`: Run unit tests only (`tests/unit`).
- `./run_tests.sh -w, --ui, --web-ui`: Run Web UI Playwright tests only (`tests/integration/ui`).
- `./run_tests.sh -i, --integration`: Run Tavern REST API integration tests only.
- `./run_tests.sh -s, --static`: Run static analysis only (`ruff`, `black`, `bandit`, `mypy`).
- `./run_tests.sh -c, --coverage`: Run unit tests with code coverage report.
- `./run_tests.sh -a, --all`: Run full test suite (unit tests, Web UI tests, Tavern integration tests, and static analysis).
- `./run_tests.sh -h, --help`: Show help and usage.

---

## Code Quality & Style Guidelines

### Formatting & Linting
- **Formatter**: `black` with an 88-character line length.
- **Linter**: `ruff` with rules `["E", "F", "I", "B", "UP", "SIM", "RUF"]` (configured under `[tool.ruff.lint]` in `pyproject.toml`).
- **Static Typing**: `mypy` (configured under `[tool.mypy]` in `pyproject.toml`).
- **Security**: `bandit` (configured in `pyproject.toml`).

```bash
# Auto-format code
uv run black .

# Check lint rules and import sorting
uv run ruff check .

# Run static type checking
uv run mypy src

# Run security checks
uv run bandit -c pyproject.toml -r .
```

### Compatibility Guidelines
- **Python 3.11+ Standard**: Leverage modern Python 3.11 features, including native pipe union type syntax (`int | None`, `str | None`).
- **NiceGUI Scope**: Wrap dynamically created elements in explicit container context managers (`with self.container:`) to prevent widgets from leaking into the root page slot.
- **Error Handling & Thread Safety**: Protect shared state (configuration, storage, previous value files, interpreter pools) with appropriate locks (`threading.Lock` / `threading.RLock`) and gracefully recover from hardware/network timeouts without crashing background event loops.
