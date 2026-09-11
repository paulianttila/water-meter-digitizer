from typing import Any, Protocol, runtime_checkable

from configuration import Config
from processor.digitizer import MeterResult


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

    def get_health_data(self) -> dict[str, Any]:
        """Get system health and diagnostics metrics"""
        ...

    def get_leak_status(self) -> dict[str, Any]:
        """Get zero-flow leak monitor status and history"""
        ...

    def reset_leak_status(self) -> dict[str, Any]:
        """Reset and acknowledge zero-flow leak state"""
        ...

    def get_poller_status(self) -> dict[str, Any]:
        """Get background poller status and schedule"""
        ...

    def trigger_poller(self) -> dict[str, Any]:
        """Trigger background poller readout immediately"""
        ...

    def get_mqtt_status(self) -> dict[str, Any]:
        """Get MQTT client and Home Assistant connection status"""
        ...

    def get_previous_values(self) -> dict[str, dict[str, str]]:
        """Get all stored baseline previous meter values"""
        ...

    def set_previous_value(self, name: str, value: str) -> dict[str, Any]:
        """Save a new baseline previous meter value"""
        ...

    def get_timeline(
        self,
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        frames_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get historical timeline frames and anomalies"""
        ...

    def get_frame_data_uri(self, reading_id: int) -> str | None:
        """Get base64 data URI for a snapshot frame"""
        ...

    def get_frame_diff(
        self, reading_id: int, compare_id: int | None = None
    ) -> dict[str, Any]:
        """Get visual diff metrics and heatmap for a specific timeline frame"""
        ...

    def get_frame_diff_data_uri(
        self, reading_id: int, compare_id: int | None = None
    ) -> str | None:
        """Get base64 data URI for visual diff heatmap image"""
        ...
