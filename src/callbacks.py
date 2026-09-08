from typing import Any, Protocol, runtime_checkable

from processor.digitizer import MeterResult
from configuration import Config


@runtime_checkable
class Callbacks(Protocol):
    def get_meter_data(self, url: str = "", saveimages: bool = False) -> MeterResult:
        """Get meter data"""
        ...

    def get_image_as_base64_str(self, image_name: str) -> str:
        """Get image as base64 string"""
        ...

    def get_config(self) -> Config:
        """Get configuration"""
        ...

    def load_config_file(self) -> str:
        """Get configuration file in text format"""
        ...

    def save_config_file(self, data: str) -> None:
        """Set configuration file in text format"""
        ...

    def use_config(self) -> None:
        """Take configuration file in use"""
        ...

    def get_storage(self) -> Any:
        """Get history storage backend"""
        ...

    def list_config_backups(self) -> list[dict[str, Any]]:
        """List available configuration backups"""
        ...

    def restore_config_backup(self, backup_name: str) -> None:
        """Restore specified configuration backup"""
        ...

    def undo_last_config(self) -> str | None:
        """Revert to immediate prior configuration backup"""
        ...

    def create_config_snapshot(self, tag: str = "") -> str | None:
        """Create a manual checkpoint/snapshot of active configuration"""
        ...

    def delete_config_backup(self, backup_name: str) -> bool:
        """Delete specific configuration backup"""
        ...

    def diff_config_backup(self, backup_name: str) -> list[str]:
        """Get line-by-line diff between current config and a backup"""
        ...
