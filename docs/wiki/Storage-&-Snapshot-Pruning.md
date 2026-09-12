# Storage & Snapshot Pruning

The **Water Meter Digitizer** features a resilient dual storage backend architecture designed for low SD card write wear, long-term historical retention, and interactive visual frame playback.

---

## 💾 Dual Storage Backends

1. **SQLite Storage (`sqlite`)**:
   - Default persistence backend stored in `/data/meter_history.db`.
   - Uses Write-Ahead Logging (`WAL` mode) and connection pooling with concurrency locks for robust simultaneous read/write operations.
2. **In-Memory Storage (`memory`)**:
   - High-speed ephemeral storage for read-only filesystem containers or temporary testing environments.
   - Automatically selected as fallback if the database path is read-only.

---

## 📸 Snapshot Modes & WebP Compression

Historical image snapshots are compressed into **WebP** format (reducing storage footprint by 70–80% compared to raw JPEG) and stored in binary blobs within SQLite.

### Snapshot Recording Tiers:
- **`all`**: Persist a compressed visual snapshot on every readout interval.
- **`anomalies_only`** (Recommended): Persist frames only when flow anomalies, vision confidence drops, or leak alerts occur.
- **`disabled`**: Only record numerical meter readings without saving visual frames.

---

## 🧹 Automatic Disk Pruning Policies

Configure retention thresholds in `config.ini`:

```ini
[Storage]
Backend = sqlite
# Automatically prune readings older than 365 days
RetentionDays = 365
# Keep max 100,000 reading records (FIFO)
MaxRecords = 100000
# Cap snapshot image disk usage at 500 MB
MaxSnapshotDiskMb = 500
```
