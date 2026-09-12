# Development & Testing Guide

This guide covers setting up a local development environment, running test suites, and contributing to the **Water Meter Digitizer**.

---

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

The project includes an autonomous procedural water meter generator and CLI (`meter-generator`) for local development without physical cameras:

```bash
# Generate a static test image
uv run python -m src.testing.cli --value 00789.1234 --output test_meter.jpg

# Generate a continuous water flow sequence
uv run python -m src.testing.cli --mode flow --frames 15 --interval 0.5 --output-dir ./test_frames/

# Stress test image with glare, noise, and tilt
uv run python -m src.testing.cli --value 00452.9124 --glare --noise 5.0 --rotate 3.0 --output stress.jpg
```

See the full [Mock Camera & Meter Generator Wiki](Mock-Camera-&-Meter-Generator.md) for full REST parameters and details.
