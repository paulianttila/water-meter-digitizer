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
