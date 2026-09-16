# AGENTS.md – Water Meter Digitizer

## Project Overview

AI-powered edge vision system that reads LCD display, analog needle dials and mechanical odometer digits from water/gas/electricity meters. Uses ESP32-CAM or network cameras with lightweight CNN inference via Google LiteRT (TensorFlow Lite). Deployed as a Docker container exposing a NiceGUI web dashboard on port 3000 and a FastAPI REST API.

## Tech Stack

- **Python 3.11** (strict: `>=3.11, <3.12`)
- **FastAPI** + **Uvicorn** – REST API and app server
- **NiceGUI** – Reactive web UI (Tailwind CSS utility classes via Quasar/Vue)
- **Google LiteRT (ai-edge-litert)** – TFLite CNN inference for digit/needle recognition
- **OpenCV (headless)** + **Pillow** – Image processing pipeline
- **SQLAlchemy** + **SQLite (WAL mode)** – Historical readings and snapshot storage
- **Pydantic** + **pydantic-settings** – Configuration models and validation
- **paho-mqtt** – MQTT client with Home Assistant auto-discovery
- **uv** – Dependency management (replaces pip/poetry)

## Repository Layout

```
src/                    # Application source (Python path root in container)
├── main.py             # Entry point, FastAPI lifespan, service orchestration
├── configuration.py    # Pydantic config model, INI parsing, env overrides
├── callbacks.py        # Protocol interface decoupling GUI ↔ backend
├── data_classes.py     # Shared Pydantic models (health, metrics, positions)
├── version.py          # Dynamic version from pyproject.toml
├── api/                # FastAPI route modules (routes_*.py)
├── cnn/                # LiteRT inference: base class, pool, analog/digital CNNs
├── processor/          # 6-stage pipeline: image capture → digitizer post-processing
├── storage/            # Abstract base + SQLite and in-memory backends
├── gui/                # NiceGUI pages (page_*.py), setup wizard steps (step_*.py)
│   ├── components/     # Reusable UI cards (consumption, time_machine, leak, etc.)
│   └── theme.py        # Tailwind CSS class constants for consistent styling
├── mqtt/               # MQTT client service + Home Assistant discovery
├── leak/               # Zero-flow continuous leak detection engine
├── poller/             # Background polling scheduler
├── testing/            # Mock camera meter generator for synthetic test frames
├── utils/              # Shared helpers (image, cache, math, security, visual_diff)
├── decorators/         # Cross-cutting decorators (e.g. log_execution_time)
└── web/static/         # Static assets served by FastAPI
config/                 # Default INI config, reference marker images, neural net models
tests/
├── unit/               # ~500 pytest unit tests (run: ./run_tests.sh -u)
└── integration/        # Tavern REST + Playwright UI + end-to-end tests
docs/wiki/              # GitHub Wiki source (synced by CI to repo.wiki)
README.md               # User documentation, features, hardware & quick start
DEVELOPER.md            # Developer setup, testing, and release guide
```

## Build & Run

All Python commands and tooling must be executed via `uv` (e.g. `uv run <cmd>`):

```bash
uv sync                                    # Install dependencies
export CONFIG_FILE=$(pwd)/config/config.ini
uv run python src/main.py                  # Start on http://localhost:3000

docker build -t water-meter-digitizer .    # Multi-stage Docker build
```

## Testing & Quality Gates

All testing is orchestrated through `./run_tests.sh` (or individual test files can be run directly via `uv run pytest`):

```bash
uv run pytest tests/unit/test_example.py  # Run a specific or new test file directly

./run_tests.sh -u     # Unit tests (pytest)
./run_tests.sh -s     # Static analysis (Ruff, Black, Bandit, Mypy)
./run_tests.sh -c     # Unit tests + coverage report (target ≥80%)
./run_tests.sh -i     # Tavern REST + MQTT integration tests
./run_tests.sh --ui   # Playwright browser UI tests
./run_tests.sh -a     # Full suite (all of the above)
```

- **Full validation required**: Always run `./run_tests.sh -a` and `./run_tests.sh -s` before considering new features or tasks ready. All checks must pass with zero errors.
- **No auto-commits**: Never automatically create git commits, but propose git commit message.
- **Cleanup**: Revert `prevalue.ini` after running tests if needed.

## Code Style & Conventions

- **Formatter**: Black (line-length 88, target py311)
- **Linter**: Ruff (rules: E, F, I, B, UP, SIM, RUF; E501 ignored)
- **Type checker**: Mypy (check_untyped_defs=true, ignore_missing_imports=true)
- **Security**: Bandit (excludes tests/)
- Imports: use `isort`-compatible ordering via Ruff `I` rule
- All models use **Pydantic BaseModel** with type hints
- GUI styling uses Tailwind CSS class constants defined in `src/gui/theme.py` – reuse existing constants, don't inline ad-hoc classes
- The `Callbacks` **Protocol** in `src/callbacks.py` decouples the GUI from backend logic – add new backend operations there first
- Configuration is INI-based (`config/config.ini`) parsed via `configparser` into Pydantic models in `src/configuration.py`
- Storage backends implement the abstract base in `src/storage/base.py`

## Architecture Patterns

- **Decoupled via Protocol**: GUI pages call methods on the `Callbacks` protocol, never import backend modules directly
- **Thread-safe LiteRT pool**: `src/cnn/pool.py` manages a pool of TFLite interpreter instances for concurrent inference
- **6-stage pipeline**: Capture → Alignment → Adjustment → ROI Extraction → CNN Inference → Post-Processing (in `src/processor/`)
- **Storage abstraction**: `StorageBackend` ABC with SQLite (production) and in-memory (testing) implementations
- **Background poller**: `src/poller/scheduler.py` runs periodic meter reads on a configurable interval

## Test Conventions

- Unit tests live in `tests/unit/test_<module>.py` mirroring the source module
- New or individual test files can be executed directly via `uv run pytest tests/unit/test_<module>.py`
- Integration tests in `tests/integration/` use Tavern YAML for REST API and pytest for end-to-end flows
- Test resources go in `tests/unit/resource/`
- Use `unittest.mock.patch` for external dependencies; test configs use `test_config*/` directories
- `pythonpath` is set to `[".", "src"]` in pyproject.toml – import source modules directly by name

## Documentation

- `README.md` – User-facing overview, features, hardware requirements, and deployment instructions
- `DEVELOPER.md` – Developer quick start, test execution, and release build / publishing workflow
- Wiki source lives in `docs/wiki/` and is auto-synced to GitHub Wiki by `.github/workflows/wiki-sync.yml`
- Internal wiki links use **extensionless** relative paths (e.g. `[Home](Home)` not `Home.md`) for correct GitHub Wiki rendering
- Wiki `[[bracket links]]` also supported for sidebar navigation
- Images referenced from wiki pages go in `docs/images/` and use raw GitHub URLs in wiki context
- Preserve existing comments and docstrings when editing code
