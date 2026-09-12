# Hardware & Camera Setup Guide

Accurate utility meter digitizing relies fundamentally on clear, well-illuminated, and stable camera captures. This guide covers hardware selection, camera placement, lighting, and reflection mitigation.

---

## 📷 Supported Camera Types

### 1. ESP32-CAM (OV2640 / OV5640)
The most common low-cost edge capture device:
- **Firmware Options**: AI-on-the-Edge firmware, Tasmota, ESPHome, or custom ESP32 HTTP snapshot servers.
- **Resolution**: Recommended `SVGA (800x600)` or `VGA (640x480)`.
- **Snapshot URL**: `http://<esp32-cam-ip>/capture` or `http://<esp32-cam-ip>/jpg`.

### 2. USB Webcams
- Connected directly to a Raspberry Pi or local server running `mjpg-streamer`, `v4l2-rtspserver`, or `motion`.
- Snapshot URL: `http://localhost:8080/?action=snapshot` or local file path `file:///data/latest.jpg`.

### 3. IP / Security Cameras (RTSP / HTTP)
- Security cameras providing an HTTP snapshot endpoint (e.g. Hikvision, Dahua, Reolink, Axis).
- Snapshot URL: `http://admin:password@<camera-ip>/ISAPI/Streaming/channels/101/picture`.

---

## 📐 Physical Mounting & Alignment

### Distance & Framing
- Position the camera **10 cm to 20 cm** directly above the meter face.
- Ensure the meter dial fills **70% to 90%** of the frame.
- Keep the camera sensor **strictly parallel** to the meter glass to minimize perspective distortion.

### 3D Printed Enclosures
- Use a shroud or cylinder tube mount over the meter face.
- A tight enclosure blocks external stray light, shadows from passing people, and room illumination changes.

---

## 💡 Lighting & Glare Suppression

Direct LED reflections on the meter glass can obscure dial digits or needle pointers.

```
       [ Camera ]
         /    \
        /      \   (Diffuse Side Lighting)
       ▼        ▼
    [LED]      [LED]
   ─────────────────
   [ Meter Glass ]
   ═════════════════
```

### Best Practices:
1. **Side / Ring Lighting**: Position LEDs at an oblique 45° angle or use a ring with a diffusion baffle rather than a single direct center LED.
2. **Polarizing Film**: Apply linear polarizing film over the camera lens and LED source oriented 90° apart to cancel optical reflections.
3. **Software Glare Suppression**:
   - Enable **CLAHE** (Contrast Limited Adaptive Histogram Equalization) or **Inpainting** in Step 4 of the Setup Wizard.
   - Set `GlareSuppression = True`, `GlareMode = clahe`, `GlareInpaintThreshold = 230` in `config.ini`.
