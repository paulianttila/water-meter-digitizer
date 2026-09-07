from typing import Any

from .base import (
    ConsumptionRecord,
    MeterReading,
    ReadingRecord,
    StorageBackend,
    StorageSummary,
)
from .memory import MemoryStorageBackend
from .sql import SQLAlchemyStorageBackend


def get_storage_backend(config: Any) -> StorageBackend:
    """Factory function to instantiate the configured storage backend."""
    history_cfg = getattr(config, "history", None)
    if history_cfg is None or not getattr(history_cfg, "enabled", True):
        return MemoryStorageBackend(max_records=50000)

    backend_type = (getattr(history_cfg, "backend", "sqlite") or "sqlite").lower()
    db_url = getattr(history_cfg, "db_url", "")
    retention_days = getattr(history_cfg, "retention_days", 30)
    max_records = getattr(history_cfg, "max_records", 50000)
    max_memory_mb = getattr(history_cfg, "max_memory_mb", 20.0)
    auto_vacuum = getattr(history_cfg, "auto_vacuum", True)
    prune_interval = getattr(history_cfg, "prune_interval", 50)

    if backend_type == "memory" or db_url == "sqlite:///:memory:":
        return MemoryStorageBackend(
            max_memory_mb=max_memory_mb,
            retention_days=retention_days,
            max_records=max_records,
            auto_vacuum=auto_vacuum,
            prune_interval=prune_interval,
        )

    if not db_url:
        data_dir = getattr(config, "data_dir", "/data")
        db_url = f"sqlite:///{data_dir}/history.db"

    return SQLAlchemyStorageBackend(
        db_url=db_url,
        max_memory_mb=max_memory_mb,
        retention_days=retention_days,
        max_records=max_records,
        auto_vacuum=auto_vacuum,
        prune_interval=prune_interval,
    )


__all__ = [
    "ConsumptionRecord",
    "MeterReading",
    "ReadingRecord",
    "StorageBackend",
    "StorageSummary",
    "SQLAlchemyStorageBackend",
    "MemoryStorageBackend",
    "get_storage_backend",
]
