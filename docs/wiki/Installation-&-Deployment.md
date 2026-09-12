# Installation & Deployment Guide

This guide covers deploying the **Water Meter Digitizer** using Docker, Docker Compose, Raspberry Pi (ARM64), and local bare-metal Python environments.

---

## 🐳 Docker & Docker Compose (Recommended)

The easiest and most reliable way to run the digitizer is via Docker. Official multi-architecture images are published for `linux/amd64` and `linux/arm64`.

### `docker-compose.yml`

Create a `docker-compose.yml` file in your preferred deployment directory:

```yaml
services:
  watermeter-digitizer:
    container_name: water-meter-digitizer
    image: paulianttila/water-meter-digitizer:latest
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    environment:
      - TZ=Europe/Helsinki
      - METER_LOG_LEVEL=INFO
    volumes:
      - ./config:/config
      - ./data:/data
    ports:
      - 3000:3000
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:3000/healthcheck')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "2m"
        max-file: "2"
```

### Starting the Service

```bash
docker compose up -d
```

Access the interactive web dashboard at **`http://<host-ip>:3000`**.

---

## 🍓 Hardware & Edge Deployment (Raspberry Pi)

### Supported Hardware
- **Raspberry Pi 5 / 4 / 3B+**: ✅ Fully supported on 64-bit OS (`Raspberry Pi OS 64-bit` or `Ubuntu Server 64-bit`).
- **Raspberry Pi Zero 2 W**: ✅ Fully supported on 64-bit OS.
- **Legacy 32-bit Raspberry Pi 1/2**: ❌ Not supported (Upstream Google LiteRT requires 64-bit architecture).

### Performance Optimization on Edge Devices
- Set `PoolSize = 2` (or `PoolSize = 1` on Raspberry Pi Zero 2 W) in `config.ini` to limit concurrent TensorFlow Lite interpreter memory footprints.
- Enable WebP snapshot compression in `[Storage]` to minimize SD card write amplification and wear.

---

## 🐍 Bare-Metal Installation (Python 3.11 + `uv`)

For local development or running directly on a Linux/macOS system:

### 1. Install `uv` Package Manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone Repository & Install Dependencies
```bash
git clone https://github.com/paulianttila/water-meter-digitizer.git
cd water-meter-digitizer
uv sync
```

### 3. Run Application
```bash
export CONFIG_FILE=$(pwd)/config/config.ini
uv run python src/main.py
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CONFIG_FILE` | `/config/config.ini` (or `./config/config.ini`) | Absolute path to active INI configuration file. |
| `TZ` | `UTC` | Timezone for localized timestamps, logs, and consumption buckets (e.g. `Europe/Helsinki`, `America/New_York`). |
| `METER_LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `DIR_DATA` | `/data` | Root path for persistence databases, snapshot buffers, and logs. |
