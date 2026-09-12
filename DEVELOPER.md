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

## 📚 Deep Dive Documentation & Wiki

Explore detailed documentation in the project Wiki:

| Topic | Documentation Link |
| :--- | :--- |
| **System Architecture & Pipeline** | [Architecture & Pipeline](docs/wiki/Architecture-&-Pipeline.md) |
| **Neural Network & LiteRT Inference** | [Neural Network Models](docs/wiki/Neural-Network-Models.md) |
| **Predecessor Roll-Over Math** | [Digit Roll-Over & Extended Resolution](docs/wiki/Digit-Roll-Over-&-Extended-Resolution.md) |
| **Zero-Flow Leak Detection Engine** | [Zero-Flow Leak Detection](docs/wiki/Zero-Flow-Leak-Detection.md) |
| **Storage & Snapshot Retention** | [Storage & Snapshot Pruning](docs/wiki/Storage-&-Snapshot-Pruning.md) |
| **Smart Home Integrations (HA/openHAB)**| [Smart Home Integrations](docs/wiki/Smart-Home-Integrations.md) |
| **REST API Reference** | [REST API Reference](docs/wiki/REST-API-Reference.md) |
| **Mock Camera & Meter Generator** | [Mock Camera & Meter Generator](docs/wiki/Mock-Camera-&-Meter-Generator.md) |
| **Development & Test Guidelines** | [Development & Testing Guide](docs/wiki/Development-&-Testing.md) |
