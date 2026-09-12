# Troubleshooting & Frequently Asked Questions (FAQ)

---

## 🔍 Troubleshooting Matrix

| Symptom / Error | Likely Cause | Solution |
| :--- | :--- | :--- |
| **`Image download failed / timeout`** | Camera URL is unreachable or network timeout is too low. | Verify camera IP in browser. Increase `Timeout = 15` in `[TakeImage]`. |
| **`Alignment failed / Low alignment match score`** | Reference marker templates are obstructed, moved, or reflect LED light. | Redefine reference markers in Step 3 of Setup Wizard on static, high-contrast, non-moving landmarks. |
| **`Reading rate exceeds max rate / Rejected`** | Physical rate limit tripped due to single-frame digit misclassification. | Verify digit bounding boxes. Enable `UsePreviousValue = True` so system falls back to cached baseline. |
| **`Digits misread as adjacent numbers (e.g. 4 read as 5)`** | Rolling odometer digit is halfway between positions. | Verify that predecessor ordering is configured properly from left (MSD) to right (LSD) and analog dials are linked. |
| **`MQTT Disconnected / Reconnecting`** | Broker credentials, port, or firewall blocking connection. | Check `/mqtt/status` endpoint for error logs. Verify MQTT host and authentication in `[MQTT]` section. |
| **`Database locked / disk I/O slow`** | SD card write latency on edge device. | Ensure SQLite is running in `WAL` mode (default). Set `SnapshotMode = anomalies_only` to reduce disk writes. |

---

## ❓ Frequently Asked Questions (FAQ)

### Can I run this offline without internet access?
**Yes.** The digitizer runs 100% locally on your local network/server. Neural network models run on-device via LiteRT with zero cloud dependencies.

### How do I backup my calibration before making changes?
Open the **Config** tab ➔ click **History / Backups** ➔ click **Create Snapshot** and assign a tag (e.g. `pre-experiment`). You can rollback with 1-click anytime.

### Does this work with gas or electricity meters?
**Yes.** Any utility meter featuring mechanical rolling number drums or rotating needle dials can be digitized using the same workflow.
