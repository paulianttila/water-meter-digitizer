"""Implementation of Callbacks protocol bridging NiceGUI frontend to backend."""

from collections.abc import Callable
from typing import Any

from callbacks import Callbacks
from configuration import Config
from processor.digitizer import MeterResult


class CallbacksImpl(Callbacks):
    """Concrete Callbacks implementation connecting frontend to backend services."""

    def __init__(
        self,
        get_meter_data_fn: Callable[..., MeterResult],
        get_image_base64_fn: Callable[[str], str],
        get_config_fn: Callable[[], Config],
        load_config_file_fn: Callable[[], str],
        save_config_file_fn: Callable[[str], None],
        use_config_fn: Callable[[], None],
        get_storage_fn: Callable[[], Any],
        list_backups_fn: Callable[[], list[dict[str, Any]]],
        restore_backup_fn: Callable[[str], None],
        undo_backup_fn: Callable[[], str | None],
        create_snapshot_fn: Callable[[str], str | None],
        delete_backup_fn: Callable[[str], bool],
        diff_backup_fn: Callable[[str], list[str]],
        get_health_data_fn: Callable[[], dict[str, Any]] | None = None,
        get_leak_status_fn: Callable[[], dict[str, Any]] | None = None,
        reset_leak_status_fn: Callable[[], dict[str, Any]] | None = None,
        get_poller_status_fn: Callable[[], dict[str, Any]] | None = None,
        trigger_poller_fn: Callable[[], dict[str, Any]] | None = None,
        get_mqtt_status_fn: Callable[[], dict[str, Any]] | None = None,
        get_previous_values_fn: Callable[[], dict[str, dict[str, str]]] | None = None,
        set_previous_value_fn: Callable[[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self._get_meter_data = get_meter_data_fn
        self._get_image_base64 = get_image_base64_fn
        self._get_config = get_config_fn
        self._load_config_file = load_config_file_fn
        self._save_config_file = save_config_file_fn
        self._use_config = use_config_fn
        self._get_storage = get_storage_fn
        self._list_backups = list_backups_fn
        self._restore_backup = restore_backup_fn
        self._undo_backup = undo_backup_fn
        self._create_snapshot = create_snapshot_fn
        self._delete_backup = delete_backup_fn
        self._diff_backup = diff_backup_fn
        self._get_health_data = get_health_data_fn
        self._get_leak_status = get_leak_status_fn
        self._reset_leak_status = reset_leak_status_fn
        self._get_poller_status = get_poller_status_fn
        self._trigger_poller = trigger_poller_fn
        self._get_mqtt_status = get_mqtt_status_fn
        self._get_previous_values = get_previous_values_fn
        self._set_previous_value = set_previous_value_fn

    def get_meter_data(self, url: str = "", saveimages: bool = False) -> MeterResult:
        if not url:
            cfg = self.get_config()
            if cfg and getattr(cfg, "image_source", None):
                url = cfg.image_source.url
        return self._get_meter_data(url=url, saveimages=saveimages)

    def get_image_as_base64_str(self, image_name: str) -> str:
        return self._get_image_base64(image_name)

    def get_config(self) -> Config:
        return self._get_config()

    def load_config_file(self) -> str:
        return self._load_config_file()

    def save_config_file(self, data: str) -> None:
        return self._save_config_file(data)

    def use_config(self) -> None:
        return self._use_config()

    def get_storage(self) -> Any:
        return self._get_storage()

    def list_config_backups(self) -> list[dict[str, Any]]:
        return self._list_backups()

    def restore_config_backup(self, backup_name: str) -> None:
        return self._restore_backup(backup_name)

    def undo_last_config(self) -> str | None:
        return self._undo_backup()

    def create_config_snapshot(self, tag: str = "") -> str | None:
        return self._create_snapshot(tag)

    def delete_config_backup(self, backup_name: str) -> bool:
        return self._delete_backup(backup_name)

    def diff_config_backup(self, backup_name: str) -> list[str]:
        return self._diff_backup(backup_name)

    def get_health_data(self) -> dict[str, Any]:
        if self._get_health_data is not None:
            return self._get_health_data()
        return {"status": "unknown"}

    def get_leak_status(self) -> dict[str, Any]:
        if self._get_leak_status is not None:
            return self._get_leak_status()
        return {"enabled": False, "state": "OK"}

    def reset_leak_status(self) -> dict[str, Any]:
        if self._reset_leak_status is not None:
            return self._reset_leak_status()
        return {"enabled": False, "state": "OK"}

    def get_poller_status(self) -> dict[str, Any]:
        if self._get_poller_status is not None:
            return self._get_poller_status()
        return {"enabled": False, "running": False}

    def trigger_poller(self) -> dict[str, Any]:
        if self._trigger_poller is not None:
            return self._trigger_poller()
        return {"status": "error", "message": "Poller trigger not configured"}

    def get_mqtt_status(self) -> dict[str, Any]:
        if self._get_mqtt_status is not None:
            return self._get_mqtt_status()
        return {"enabled": False, "connected": False}

    def get_previous_values(self) -> dict[str, dict[str, str]]:
        if self._get_previous_values is not None:
            return self._get_previous_values()
        return {}

    def set_previous_value(self, name: str, value: str) -> dict[str, Any]:
        if self._set_previous_value is not None:
            return self._set_previous_value(name, value)
        return {"status": "error", "message": "Previous value setter not configured"}
