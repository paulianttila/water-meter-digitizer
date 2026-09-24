"""Service managing configuration file reading, atomic persistence, and backup history."""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from config.history_manager import ConfigHistoryManager
from configuration import Config

logger = logging.getLogger(__name__)


class ConfigFileService:
    """Encapsulates configuration file operations with thread safety, atomic write, and backups."""

    def __init__(
        self,
        config_file: str | Callable[[], str],
        lock: threading.RLock | None = None,
    ) -> None:
        self._config_file = config_file
        self._lock = lock or threading.RLock()

    @property
    def config_file(self) -> str:
        """Resolve current configuration file path."""
        if callable(self._config_file):
            return self._config_file()
        return self._config_file

    def load(self) -> str:
        """Read configuration file contents within the config lock."""
        with self._lock, open(self.config_file, encoding="utf-8") as f:
            return f.read()

    def save(self, data: str) -> None:
        """Validate syntax, create backup, and atomically persist configuration to disk."""
        target_path = Path(self.config_file).resolve()
        with self._lock:
            # 1. Validate syntax prior to any modification
            try:
                Config().load_from_string(data)
            except Exception as e:
                logger.error(
                    "Failed to parse configuration before saving to %s: %s",
                    target_path,
                    e,
                )
                raise

            # 2. Create timestamped backup if existing file exists
            if target_path.exists():
                ConfigHistoryManager.create_backup(str(target_path))

            # 3. Atomically write using temporary file in same directory and os.replace
            target_dir = target_path.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            tmp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=str(target_dir),
                    prefix=f"{target_path.stem}_",
                    suffix=".tmp",
                    delete=False,
                ) as tmp_file:
                    tmp_path = Path(tmp_file.name)
                    tmp_file.write(data)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_path, target_path)
            except Exception:
                if tmp_path is not None and tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise

    def list_backups(self) -> list[dict[str, Any]]:
        """List available configuration backups as serialized dictionaries."""
        with self._lock:
            return [
                b.model_dump()
                for b in ConfigHistoryManager.list_backups(self.config_file)
            ]

    def restore_backup(self, backup_name: str) -> None:
        """Restore configuration from an existing backup entry."""
        with self._lock:
            ConfigHistoryManager.restore_backup(self.config_file, backup_name)

    def undo_last(self) -> str | None:
        """Revert configuration to the most recent backup."""
        with self._lock:
            return ConfigHistoryManager.undo_last(self.config_file)

    def create_snapshot(self, tag: str = "") -> str | None:
        """Create a tagged snapshot backup."""
        with self._lock:
            return ConfigHistoryManager.create_backup(self.config_file, tag=tag)

    def delete_backup(self, backup_name: str) -> bool:
        """Delete a specified backup entry."""
        with self._lock:
            return ConfigHistoryManager.delete_backup(self.config_file, backup_name)

    def diff_backup(self, backup_name: str) -> list[str]:
        """Compute visual diff between current configuration and a backup."""
        with self._lock:
            return ConfigHistoryManager.get_diff(
                self.load(), backup_name, config_file=self.config_file
            )

    def load_backup(self, backup_name: str) -> str:
        """Load raw contents of a specific backup file."""
        with self._lock:
            return ConfigHistoryManager.get_backup_content(
                backup_name, config_file=self.config_file
            )
