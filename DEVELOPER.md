# Developer Quick Start

Welcome to the **Water Meter Digitizer** developer guide. For comprehensive architectural deep dives, algorithm mathematics, and API specifications, visit the **[Project Wiki](docs/wiki/Home.md)**.

---

## ⚡ Quick Start with `uv`

The project uses [`uv`](https://docs.astral.sh/uv/) for high-performance Python dependency management.

```bash
# 1. Clone the repository
git clone https://github.com/paulianttila/water-meter-digitizer.git
cd water-meter-digitizer

# 2. Sync dependencies into virtual environment
uv sync

# 3. Install Playwright browser dependencies (for UI tests)
uv run playwright install --with-deps chromium

# 4. Run application locally
export CONFIG_FILE=$(pwd)/config/config.ini
uv run python src/main.py
```

The web dashboard and setup wizard will be available at **`http://localhost:3000`**.

---

## 📁 Repository Structure

```
├── src/                    # Application source (Python path root in container)
│   ├── main.py             # Entry point, FastAPI lifespan, service orchestration
│   ├── configuration.py    # Pydantic config model, INI parsing, env overrides
│   ├── callbacks.py        # Protocol interface decoupling GUI ↔ backend
│   ├── data_classes.py     # Shared Pydantic models (health, metrics, positions)
│   ├── version.py          # Dynamic version from pyproject.toml
│   ├── api/                # FastAPI route modules (routes_*.py)
│   ├── cnn/                # LiteRT inference: base class, pool, analog/digital CNNs
│   ├── processor/          # 6-stage pipeline: image capture → digitizer post-processing
│   ├── storage/            # Abstract base + SQLite and in-memory backends
│   ├── gui/                # NiceGUI web UI: pages/, wizard/ (steps/, adjust/), dialogs/, components/
│   │   ├── components/     # Reusable UI cards (consumption, time_machine, leak, etc.)
│   │   ├── pages/          # Full page views (meter, config, services, setup, etc.)
│   │   ├── wizard/         # 9-step calibration wizard (steps/, adjust/)
│   │   ├── dialogs/        # Modal dialogs (benchmark)
│   │   └── theme.py        # Tailwind CSS class constants for consistent styling
│   ├── services/           # Background & integration services (mqtt, leak, poller, simulator)
│   │   ├── mqtt/           # MQTT client service + Home Assistant discovery
│   │   ├── leak/           # Zero-flow continuous leak detection engine
│   │   ├── poller/         # Background polling scheduler
│   │   └── simulator/      # Mock camera meter generator for synthetic frames & simulation
│   ├── utils/              # Shared helpers (image, cache, math, security, decorators, visual_diff)
│   └── web/static/         # Static assets served by FastAPI
├── config/                 # Default INI config, reference marker images, neural net models
├── tests/
│   ├── unit/               # ~590+ pytest unit tests mirroring src/ hierarchy
│   └── integration/        # Tavern REST + Playwright UI + end-to-end tests
├── docs/wiki/              # GitHub Wiki source (synced by CI to repo.wiki)
├── README.md               # User documentation, features, hardware & quick start
├── DEVELOPER.md            # Developer setup, testing, and release guide
├── Dockerfile              # Multi-stage Docker container build definition
└── pyproject.toml          # Project configuration, dependencies, and tooling
```

---

## 🧪 Testing & Quality Assurance

Run the unified test runner script `./run_tests.sh`:

```bash
# Run unit tests
./run_tests.sh -u

# Run unit tests with code coverage report (target: >= 80%)
./run_tests.sh -c

# Run Playwright Web UI automated browser tests
./run_tests.sh --ui

# Run Tavern REST and live MQTT integration tests
./run_tests.sh -i

# Run static analysis (Ruff, Black, Bandit security scan, Mypy)
./run_tests.sh -s

# Run complete test & static analysis suite
./run_tests.sh -a
```

---

## 📦 Release Build & Publishing

Follow these steps to produce and verify a production release build:

### 1. Update Application Version
Update the `version` field in [`pyproject.toml`](pyproject.toml):
```toml
[project]
version = "1.0.0"
```
*(The runtime `src/main.py:VERSION` dynamically loads this version).*

### 2. Run Full Quality Verification
Ensure the complete test suite, security audit, and static analysis checks pass with zero errors:
```bash
# Run unit tests, Tavern integration, Playwright UI, Ruff, Black, Bandit, and Mypy
./run_tests.sh -a
```

### 3. Build & Test Production Docker Image Locally (optional)
Test the multi-stage Docker build locally to verify stripped layers, non-root user execution, and healthcheck:
```bash
# Build local release container
docker build -t paulianttila/water-meter-digitizer:latest .

# Run container in daemon mode with local configuration and data mounts
docker run -d --name watermeter-release-test \
  -p 3000:3000 \
  -v $(pwd)/config:/config \
  -v $(pwd)/data:/data \
  paulianttila/water-meter-digitizer:latest

# Verify healthcheck endpoint
curl -f http://localhost:3000/healthcheck

# Clean up test container
docker stop watermeter-release-test && docker rm watermeter-release-test
```

### 4. Tag & Trigger Automated Release Workflow
The repository utilizes GitHub Actions to build multi-arch (`linux/amd64`, `linux/arm64`) images and publish to Docker Hub automatically upon pushing a semantic version tag:

```bash
# Commit version bump
git commit -am "Release v1.0.0"
git push origin main

# Create annotated semantic version tag and push
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

GitHub Actions will automatically:
- Build multi-arch container images (`linux/amd64`, `linux/arm64`) with QEMU and Buildx.
- Push tagged releases (`v1.0.0`, `v1.0`, `latest`) to Docker Hub.
- Synchronize markdown documentation from `docs/wiki/` to GitHub Wiki.

---

## 📚 Deep Dive Documentation & Wiki

Explore detailed documentation in the project Wiki:

| Topic | Documentation Link |
| :--- | :--- |
| **Getting Started & Hardware** | [Getting Started & Hardware Guide](docs/wiki/Getting-Started-&-Hardware.md) |
| **Setup Wizard & Calibration** | [Setup Wizard & Calibration Manual](docs/wiki/Setup-Wizard-&-Calibration.md) |
| **Dashboard & Features** | [Dashboard, Features & Tools Guide](docs/wiki/Dashboard-&-Features-Guide.md) |
| **Smart Home & REST APIs** | [Integrations & API Reference](docs/wiki/Integrations-&-API-Reference.md) |
| **Configuration & Storage Retention** | [Configuration & Storage Manual](docs/wiki/Configuration-&-Storage-Manual.md) |
| **System Architecture & Neural Models**| [Architecture, Neural Networks & Pipeline](docs/wiki/Architecture-&-Neural-Networks.md) |
| **Development & Test Guidelines** | [Development & Testing Guide](docs/wiki/Development-&-Testing.md) |
| **Troubleshooting & FAQ** | [Troubleshooting & FAQ Guide](docs/wiki/Troubleshooting-&-FAQ.md) |

