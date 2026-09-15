# 🧪 Development & Testing Guide

[🏠 Wiki Home](Home) • [◀ Previous: Architecture, Neural Networks & Pipeline Deep Dive](Architecture-&-Neural-Networks) • [Next: Troubleshooting & FAQ Guide ▶](Troubleshooting-&-FAQ)

---

This guide covers setting up a local development environment, running test suites, and contributing to the **Water Meter Digitizer**.

## 🛠️ Environment Setup

The repository uses [`uv`](https://docs.astral.sh/uv/) for fast Python dependency management.

```bash
# 1. Clone the repository
git clone https://github.com/paulianttila/water-meter-digitizer.git
cd water-meter-digitizer

# 2. Sync virtual environment dependencies
uv sync

# 3. Install Playwright browser dependencies (for UI tests)
uv run playwright install --with-deps chromium
```

---

## 🧪 Comprehensive Test Suites (`./run_tests.sh`)

The repository includes an all-in-one test runner script `./run_tests.sh`:

| Command | Suite | Purpose |
| :--- | :--- | :--- |
| **`./run_tests.sh -u`** | Unit Tests | Runs all 400+ fast isolated unit tests (`tests/unit/`). |
| **`./run_tests.sh -c`** | Code Coverage | Runs unit tests and reports line coverage (target: $\ge 80\%$). |
| **`./run_tests.sh --ui`** | Playwright UI Tests | Executes automated headless browser tests across all Web UI tabs. |
| **`./run_tests.sh -i`** | Integration Tests | Runs Tavern REST and live MQTT broker integration scenarios. |
| **`./run_tests.sh -s`** | Static Analysis | Runs Ruff linter, Black formatter check, Bandit security scan, and Mypy. |
| **`./run_tests.sh -a`** | Complete Suite | Runs all unit, UI, integration, and static analysis checks. |

---

## 🛡️ Code Quality Standards

Before opening a pull request, ensure all checks pass:

```bash
# Auto-format code
uv run black .
uv run ruff check --fix .

# Verify complete suite
./run_tests.sh -a
```

---

## 📸 Synthetic Meter Generator & Mock Camera

The project includes an autonomous procedural water meter generator and CLI (`meter-generator`) for local development and CI testing without physical cameras:

```bash
# Generate a static test image
uv run python -m src.testing.cli --value 00789.1234 --output test_meter.jpg

# Generate a continuous water flow sequence
uv run python -m src.testing.cli --mode flow --frames 15 --interval 0.5 --output-dir ./test_frames/

# Stress test image with glare, noise, and tilt
uv run python -m src.testing.cli --value 00452.9124 --glare --noise 5.0 --rotate 3.0 --output stress.jpg
```

---

## 🚀 End-to-End (E2E) Integration Tests

The test suite leverages the mock camera for true full-system end-to-end integration testing (`tests/integration/`):

| Test Suite | File | What is Tested |
| :--- | :--- | :--- |
| **Pipeline & ROI** | `test_e2e_mock_camera_pipeline.py` | Live `/meter` readout JSON generation, `/roi` rendering, and synthetic ROI extraction. |
| **Poller & History** | `test_e2e_mock_camera_poller.py` | Poller readout accumulation, SQLite history database, hourly consumption, and timeline snapshots. |
| **Leak & MQTT** | `test_e2e_mock_camera_leak_alert.py` | Zero-flow tracking, `/leak/status`, `/leak/reset`, and live MQTT telemetry publishing. |
| **Setup Wizard UI** | `ui/test_page_setup_mock_camera.py` | Playwright browser test completing the 9-step calibration wizard using mock camera frames. |

See the full [Dashboard, Features & Tools Guide](Dashboard-&-Features-Guide) for full REST parameters and Mock Camera details.

---

## 📦 Release Build & Publishing Workflow

Follow these steps to produce and verify a production release:

### 1. Version Bump
Update the version string in `pyproject.toml`:
```toml
[project]
version = "1.0.0"
```
*(The runtime `src/main.py:VERSION` dynamically loads this version).*

### 2. Comprehensive Quality Audit
Ensure the complete test suite, security audit, and static analysis checks pass:
```bash
./run_tests.sh -a
```

### 3. Local Docker Release Verification (optional)
Test the multi-stage production Docker build locally:
```bash
# 1. Build local container
docker build -t paulianttila/water-meter-digitizer:latest .

# 2. Run container in daemon mode
docker run -d --name watermeter-test \
  -p 3000:3000 \
  -v $(pwd)/config:/config \
  -v $(pwd)/data:/data \
  paulianttila/water-meter-digitizer:latest

# 3. Verify healthcheck endpoint
curl -f http://localhost:3000/healthcheck

# 4. Cleanup
docker stop watermeter-test && docker rm watermeter-test
```

### 4. Git Tag & Automated Multi-Arch Release
Tagging a release triggers GitHub Actions (`.github/workflows/docker-image.yml`):

```bash
# Commit changes
git commit -am "Release v1.0.0"
git push origin main

# Create and push annotated release tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build multi-arch container images (`linux/amd64`, `linux/arm64`) with QEMU and Buildx.
2. Push tagged release images (`v1.0.0`, `v1.0`, `latest`) to Docker Hub.
3. Synchronize markdown wiki pages (`docs/wiki/`) to the GitHub Wiki.

---

[🏠 Wiki Home](Home) • [◀ Previous: Architecture, Neural Networks & Pipeline Deep Dive](Architecture-&-Neural-Networks) • [Next: Troubleshooting & FAQ Guide ▶](Troubleshooting-&-FAQ)


