# Configuration Backups & Version Control

To ensure reliable, fail-safe operation, the **Water Meter Digitizer** includes a built-in configuration history and versioning subsystem.

---

## 🛡️ Key Features

1. **Automatic Safety Backups on Save**: Every time `config.ini` is modified via the Web GUI or API, the previous version is saved to `/config/backups/config_<YYYYMMDD_HHMMSS>_<tag>.ini`.
2. **1-Click Undo**: Instantly rollback recent configuration changes with one click.
3. **Named Checkpoint Snapshots**: Create milestone snapshots before major adjustments (e.g., `pre-recalibration`).
4. **Visual Color-Coded Diffs**: Inspect differences between your active configuration and any historical backup directly in the Web GUI.

---

## 💻 Managing Backups via Web GUI

In the **Config** tab (`/config`):
- Click **History / Backups** in the toolbar.
- View all timestamped backups with file sizes and tags.
- Click **Diff** to view color-coded line additions (`+`) and deletions (`-`).
- Click **Restore** to revert to any previous configuration state.
