import datetime
import difflib
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BackupEntry(BaseModel):
    name: str
    path: str
    timestamp: str
    formatted_time: str
    size_bytes: int
    tag: str = "Auto Backup"
    is_auto: bool = True

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(**kwargs)


class ConfigHistoryManager:
    @staticmethod
    def get_backup_dir(config_file: str) -> Path:
        """Get backups subfolder next to the target configuration file."""
        cfg_path = Path(config_file).resolve()
        backup_dir = cfg_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @classmethod
    def create_backup(cls, config_file: str, tag: str = "") -> Optional[str]:
        """Create a timestamped backup in the backups subfolder."""
        if not os.path.exists(config_file) or not os.path.isfile(config_file):
            return None

        try:
            backup_dir = cls.get_backup_dir(config_file)
            cfg_path = Path(config_file)
            now = datetime.datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")

            clean_tag = ""
            if tag:
                clean_tag = "_" + re.sub(r"[^\w\-]", "_", tag.strip())[:30]

            backup_filename = f"{cfg_path.name}_{timestamp_str}{clean_tag}.bak"
            backup_path = backup_dir / backup_filename

            shutil.copyfile(config_file, backup_path)
            logger.info(f"Created config backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create config backup for {config_file}: {e}")
            return None

    @classmethod
    def list_backups(cls, config_file: str) -> list[BackupEntry]:
        """List all available backups sorted by newest first."""
        cfg_path = Path(config_file).resolve()
        backup_dir = cfg_path.parent / "backups"

        backup_files: list[Path] = []
        if backup_dir.exists():
            backup_files.extend(backup_dir.glob("*.bak"))

        # Also discover any legacy backup files in the parent directory
        if cfg_path.parent.exists():
            for p in cfg_path.parent.glob(f"{cfg_path.name}_*.bak"):
                if p.is_file() and p not in backup_files:
                    backup_files.append(p)

        entries: list[BackupEntry] = []
        for file_path in backup_files:
            try:
                stat = file_path.stat()
                mtime_dt = datetime.datetime.fromtimestamp(stat.st_mtime)

                # Parse filename timestamp and tag if available
                # Format: config.ini_YYYYMMDD_HHMMSS_optionalTag.bak
                pattern = re.compile(
                    rf"^{re.escape(cfg_path.name)}_(\d{{8}}_\d{{6}})(?:_(.+))?\.bak$"
                )
                match = pattern.match(file_path.name)

                tag = "Auto Backup"
                is_auto = True
                if match:
                    ts_part = match.group(1)
                    raw_tag = match.group(2)
                    try:
                        dt = datetime.datetime.strptime(ts_part, "%Y%m%d_%H%M%S")
                        timestamp_str = dt.isoformat()
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        timestamp_str = mtime_dt.isoformat()
                        formatted_time = mtime_dt.strftime("%Y-%m-%d %H:%M:%S")

                    if raw_tag:
                        tag = raw_tag.replace("_", " ")
                        is_auto = False
                else:
                    timestamp_str = mtime_dt.isoformat()
                    formatted_time = mtime_dt.strftime("%Y-%m-%d %H:%M:%S")

                entries.append(
                    BackupEntry(
                        name=file_path.name,
                        path=str(file_path),
                        timestamp=timestamp_str,
                        formatted_time=formatted_time,
                        size_bytes=stat.st_size,
                        tag=tag,
                        is_auto=is_auto,
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Could not read backup file metadata for {file_path}: {e}"
                )

        # Sort newest first based on timestamp
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries

    @classmethod
    def restore_backup(cls, config_file: str, backup_name_or_path: str) -> None:
        """Restore a backup file over config_file, taking a safety snapshot first."""
        target_path = Path(backup_name_or_path)
        if not target_path.is_absolute():
            # Check in backups subfolder first, then parent directory
            backup_dir = cls.get_backup_dir(config_file)
            candidate = backup_dir / backup_name_or_path
            if candidate.exists():
                target_path = candidate
            else:
                candidate = Path(config_file).parent / backup_name_or_path
                if candidate.exists():
                    target_path = candidate
                else:
                    raise FileNotFoundError(
                        f"Backup file '{backup_name_or_path}' not found"
                    )

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Backup file '{target_path}' not found")

        # Take safety snapshot before restoring
        cls.create_backup(config_file, tag="before_restore")

        shutil.copyfile(target_path, config_file)
        logger.info(f"Restored backup '{target_path.name}' to '{config_file}'")

    @classmethod
    def undo_last(cls, config_file: str) -> Optional[str]:
        """Undo last configuration change by reverting to the most recent backup."""
        backups = cls.list_backups(config_file)
        if not backups:
            return None

        # Pick the most recent backup
        target_backup = backups[0]
        cls.restore_backup(config_file, target_backup.path)
        return target_backup.name

    @classmethod
    def delete_backup(cls, config_file: str, backup_name_or_path: str) -> bool:
        """Delete a backup file safely."""
        target_path = Path(backup_name_or_path)
        if not target_path.is_absolute():
            backup_dir = cls.get_backup_dir(config_file)
            candidate = backup_dir / backup_name_or_path
            if candidate.exists():
                target_path = candidate
            else:
                candidate = Path(config_file).parent / backup_name_or_path
                if candidate.exists():
                    target_path = candidate
                else:
                    return False

        if (
            target_path.exists()
            and target_path.is_file()
            and target_path.suffix == ".bak"
        ):
            target_path.unlink()
            logger.info(f"Deleted backup: {target_path}")
            return True
        return False

    @classmethod
    def get_diff(
        cls,
        current_content: str,
        backup_name_or_path: str,
        config_file: str = "",
    ) -> list[str]:
        """Generate a unified diff between current content and the backup."""
        target_path = Path(backup_name_or_path)
        if not target_path.is_absolute() and config_file:
            backup_dir = cls.get_backup_dir(config_file)
            candidate = backup_dir / backup_name_or_path
            if candidate.exists():
                target_path = candidate
            else:
                candidate = Path(config_file).parent / backup_name_or_path
                if candidate.exists():
                    target_path = candidate

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Backup file '{backup_name_or_path}' not found")

        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            backup_content = f.read()

        current_lines = current_content.splitlines(keepends=True)
        backup_lines = backup_content.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                backup_lines,
                current_lines,
                fromfile=f"Backup ({target_path.name})",
                tofile="Current Config",
            )
        )
        return diff
