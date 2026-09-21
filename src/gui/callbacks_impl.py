from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from callbacks import Callbacks
from configuration import Config
from data_classes import (
    ConfigBackupInfo,
    HealthResponse,
    MQTTStatus,
    PollerStatus,
    TimelineFrame,
    VisualDiffMetrics,
)
from processor.digitizer import MeterResult
from services.leak.models import LeakState, ZeroFlowStatus
from storage.base import StorageBackend
from storage.frame_service import FrameService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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
        get_storage_fn: Callable[[], StorageBackend | None],
        list_backups_fn: Callable[[], list[ConfigBackupInfo] | list[dict[str, Any]]],
        restore_backup_fn: Callable[[str], None],
        undo_backup_fn: Callable[[], str | None],
        create_snapshot_fn: Callable[[str], str | None],
        delete_backup_fn: Callable[[str], bool],
        diff_backup_fn: Callable[[str], list[str]],
        load_backup_fn: Callable[[str], str] | None = None,
        get_health_data_fn: Callable[[], HealthResponse | dict[str, Any]] | None = None,
        get_leak_status_fn: Callable[[], ZeroFlowStatus | dict[str, Any]] | None = None,
        reset_leak_status_fn: (
            Callable[[], ZeroFlowStatus | dict[str, Any]] | None
        ) = None,
        get_poller_status_fn: Callable[[], PollerStatus | dict[str, Any]] | None = None,
        trigger_poller_fn: Callable[[], dict[str, Any]] | None = None,
        get_mqtt_status_fn: Callable[[], MQTTStatus | dict[str, Any]] | None = None,
        get_previous_values_fn: Callable[[], dict[str, dict[str, str]]] | None = None,
        set_previous_value_fn: Callable[[str, str], dict[str, Any]] | None = None,
        get_config_version_fn: Callable[[], int] | None = None,
        frame_service: FrameService | None = None,
    ) -> None:
        self._get_meter_data = get_meter_data_fn
        self._get_image_base64 = get_image_base64_fn
        self._get_config = get_config_fn
        self._load_config_file = load_config_file_fn
        self._save_config_file = save_config_file_fn
        self._use_config = use_config_fn
        self._get_config_version = get_config_version_fn
        self._get_storage = get_storage_fn
        self._list_backups = list_backups_fn
        self._restore_backup = restore_backup_fn
        self._undo_backup = undo_backup_fn
        self._create_snapshot = create_snapshot_fn
        self._delete_backup = delete_backup_fn
        self._diff_backup = diff_backup_fn
        self._load_backup = load_backup_fn
        self._get_health_data = get_health_data_fn
        self._get_leak_status = get_leak_status_fn
        self._reset_leak_status = reset_leak_status_fn
        self._get_poller_status = get_poller_status_fn
        self._trigger_poller = trigger_poller_fn
        self._get_mqtt_status = get_mqtt_status_fn
        self._get_previous_values = get_previous_values_fn
        self._set_previous_value = set_previous_value_fn
        self._frame_service = frame_service or FrameService(storage=self.get_storage)

    def get_meter_data(
        self,
        url: str = "",
        saveimages: bool = False,
        config: Config | None = None,
    ) -> MeterResult:
        if not url:
            cfg = config or self.get_config()
            if cfg and getattr(cfg, "image_source", None):
                url = cfg.image_source.url
        try:
            return self._get_meter_data(url=url, saveimages=saveimages, config=config)
        except TypeError:
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

    def get_config_version(self) -> int:
        if self._get_config_version is not None:
            return self._get_config_version()
        return 1

    def get_storage(self) -> StorageBackend | None:
        return self._get_storage()

    def list_config_backups(self) -> list[ConfigBackupInfo]:
        raw = self._list_backups()
        if not raw:
            return []
        res: list[ConfigBackupInfo] = []
        for item in raw:
            if isinstance(item, ConfigBackupInfo):
                res.append(item)
            elif isinstance(item, dict):
                res.append(ConfigBackupInfo.model_validate(item))
        return res

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

    def load_config_backup(self, backup_name: str) -> str:
        if self._load_backup is not None:
            return self._load_backup(backup_name)
        return ""

    def get_health_data(self) -> HealthResponse:
        if self._get_health_data is not None:
            raw = self._get_health_data()
            if isinstance(raw, HealthResponse):
                return raw
            if isinstance(raw, dict):
                return HealthResponse.model_validate(raw)
        return HealthResponse(status="unknown")

    def get_leak_status(self) -> ZeroFlowStatus:
        if self._get_leak_status is not None:
            raw = self._get_leak_status()
            if isinstance(raw, ZeroFlowStatus):
                return raw
            if isinstance(raw, dict):
                return ZeroFlowStatus.model_validate(raw)
        return ZeroFlowStatus(enabled=False, state=LeakState.OK)

    def reset_leak_status(self) -> ZeroFlowStatus:
        if self._reset_leak_status is not None:
            raw = self._reset_leak_status()
            if isinstance(raw, ZeroFlowStatus):
                return raw
            if isinstance(raw, dict):
                return ZeroFlowStatus.model_validate(raw)
        return ZeroFlowStatus(enabled=False, state=LeakState.OK)

    def get_poller_status(self) -> PollerStatus:
        if self._get_poller_status is not None:
            raw = self._get_poller_status()
            if isinstance(raw, PollerStatus):
                return raw
            if isinstance(raw, dict):
                return PollerStatus.model_validate(raw)
        return PollerStatus(enabled=False, running=False)

    def trigger_poller(self) -> dict[str, Any]:
        if self._trigger_poller is not None:
            return self._trigger_poller()
        return {"status": "error", "message": "Poller trigger not configured"}

    def get_mqtt_status(self) -> MQTTStatus:
        if self._get_mqtt_status is not None:
            raw = self._get_mqtt_status()
            if isinstance(raw, MQTTStatus):
                return raw
            if isinstance(raw, dict):
                return MQTTStatus.model_validate(raw)
        return MQTTStatus(enabled=False, connected=False)

    def get_previous_values(self) -> dict[str, dict[str, str]]:
        if self._get_previous_values is not None:
            return self._get_previous_values()
        return {}

    def set_previous_value(self, name: str, value: str) -> dict[str, Any]:
        if self._set_previous_value is not None:
            return self._set_previous_value(name, value)
        return {"status": "error", "message": "Previous value setter not configured"}

    def get_timeline(
        self,
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        frames_only: bool = False,
    ) -> list[TimelineFrame]:
        return self._frame_service.get_timeline(
            limit=limit,
            offset=offset,
            anomalies_only=anomalies_only,
            frames_only=frames_only,
        )

    def get_frame_data_uri(self, reading_id: int) -> str | None:
        return self._frame_service.get_frame_data_uri(reading_id)

    def get_frame_diff(
        self, reading_id: int, compare_id: int | None = None
    ) -> VisualDiffMetrics:
        return self._frame_service.get_frame_diff(reading_id, compare_id)

    def get_frame_diff_data_uri(
        self, reading_id: int, compare_id: int | None = None
    ) -> str | None:
        return self._frame_service.get_frame_diff_data_uri(reading_id, compare_id)
