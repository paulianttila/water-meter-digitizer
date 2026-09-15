# 🚀 Getting Started & Hardware Guide

[🏠 Wiki Home](Home.md) • [Next: Setup Wizard & Calibration Manual ▶](Setup-Wizard-&-Calibration.md)

---

This comprehensive guide covers everything needed to deploy the **Water Meter Digitizer**, set up camera hardware, optimize physical lighting, and configure the container runtime on edge devices (such as Raspberry Pi) and x86_64 servers.

## 🐳 Docker & Docker Compose (Recommended)

The easiest, most reliable, and production-ready way to run the digitizer is via Docker. Official multi-architecture images are published to Docker Hub for both `linux/amd64` and `linux/arm64`.

### `docker-compose.yml`

Create a `docker-compose.yml` file in your preferred project directory:

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
# Launch container in detached mode
docker compose up -d

# View real-time container startup logs
docker compose logs -f
```

Access the interactive web dashboard and calibration wizard at **`http://<host-ip>:3000`**.

---

## 🍓 Hardware & Edge Deployment (Raspberry Pi)

### Supported Hardware Architectures
- **Raspberry Pi 5 / 4 / 3B+**: ✅ Fully supported on 64-bit OS (`Raspberry Pi OS 64-bit` or `Ubuntu Server 64-bit`).
- **Raspberry Pi Zero 2 W**: ✅ Fully supported on 64-bit OS.
- **Legacy 32-bit Raspberry Pi 1/2**: ❌ Not supported (Upstream Google LiteRT neural runtime requires 64-bit ARM architecture).

### Performance Optimization on Edge Devices
1. **Inference Pool Sizing**:
   - Set `PoolSize = 2` (or `PoolSize = 1` on Raspberry Pi Zero 2 W) in `[NeuralNetworks]` to optimize RAM usage and prevent OOM spikes.
2. **WebP Image Compression**:
   - In `[Storage]`, enable WebP snapshot compression to reduce SD card write amplification and wear by over 75%.
3. **Log Rotation**:
   - Docker JSON log rotation options are included above to prevent SD card exhaustion.

---

## 🐍 Local & Bare-Metal Setup (Python 3.11 + `uv`)

For local development or running directly on Linux/macOS systems without containers:

```bash
# 1. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository & sync dependencies
git clone https://github.com/paulianttila/water-meter-digitizer.git
cd water-meter-digitizer
uv sync

# 3. Start local server
export CONFIG_FILE=$(pwd)/config/config.ini
uv run python src/main.py
```

---

## 📷 Camera Hardware & Physical Mounting

Accurate computer vision depends fundamentally on clear, well-illuminated, and stable camera captures.

### 1. Supported Camera Types

| Camera Type | Typical Resolution | Snapshot URL Example | Notes |
| :--- | :--- | :--- | :--- |
| **ESP32-CAM (OV2640 / OV5640)** | `800x600` (SVGA) or `640x480` | `http://<esp32-ip>/capture` | Low cost, low power, standard HTTP server. |
| **USB Webcams / V4L2** | `1280x720` or `1920x1080` | `http://localhost:8080/?action=snapshot` | Using `mjpg-streamer` or `v4l2-rtspserver`. |
| **IP / RTSP Security Cameras** | `1920x1080` | `http://user:pass@<cam-ip>/ISAPI/Streaming/channels/101/picture` | Security cams with HTTP snapshot capability. |
| **Local / Shared File Path** | Native resolution | `file:///data/snapshots/latest.jpg` | Useful for mounted network drives or scripts. |

### 2. Distance & Framing Guidelines

- **Distance**: Position the camera lens **10 cm to 20 cm** directly above the meter dial face.
- **Framing**: Ensure the meter dial and reference landmarks fill **70% to 90%** of the total captured image frame.
- **Sensor Parallelism**: Keep the camera sensor strictly parallel to the meter glass to minimize perspective distortion and trapezoidal skew.
- **3D Printed Enclosures**: Using a snug cylinder or shroud blocks ambient daylight swings, shadows from passing people, and room lighting changes.

---

## 💡 Lighting & Optical Glare Suppression

Direct flash or LED reflections on curved meter glass can obscure rolling number drums or analog needles.

```
       [ Camera ]
         /    \
        /      \   (Diffuse 45° Side Lighting)
       ▼        ▼
    [LED]      [LED]
   ─────────────────
   [ Meter Glass ]
   ═════════════════
```

### Best Practices:
1. **Oblique / Ring Diffuse Lighting**: Position illumination LEDs at 45° oblique angles or use a diffuser ring rather than a single centered flashlight.
2. **Polarizing Filters**: Apply linear polarizing film over the camera lens and LED source oriented at 90° cross-polarization to cancel direct specular reflection.
3. **Software Glare Suppression**:
   - In Step 4 of the Setup Wizard, enable **AutoContrast**, **Sharpness**, or **CLAHE**.
   - In `config.ini`, set `GlareSuppression = True`, `GlareMode = clahe`, `GlareInpaintThreshold = 230`.

---

## ⚙️ Core Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CONFIG_FILE` | `/config/config.ini` | Absolute path to the active INI configuration file. |
| `TZ` | `UTC` | Timezone for localized timestamps, logs, and hourly consumption buckets (e.g. `Europe/Helsinki`, `America/New_York`). |
| `METER_LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `DIR_DATA` | `/data` | Root path for persistence databases, snapshot buffers, and logs. |

---

[🏠 Wiki Home](Home.md) • [Next: Setup Wizard & Calibration Manual ▶](Setup-Wizard-&-Calibration.md)
