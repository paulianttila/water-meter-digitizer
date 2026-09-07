from typing import Any

from .base import (
    ConsumptionRecord,
    MeterReading,
    ReadingRecord,
    StorageBackend,
    StorageSummary,
)
from .memory import MemoryStorageBackend


def get_storage_backend(config: Any) -> StorageBackend:
    """Factory function to instantiate the configured storage backend."""
    history_cfg = getattr(config, "history", None)
    if history_cfg is None or not getattr(history_cfg, "enabled", True):
        return MemoryStorageBackend(max_memory_mb=20.0, max_records=50000)

    backend_type = (getattr(history_cfg, "backend", "memory") or "memory").lower()
    max_mem = getattr(history_cfg, "max_memory_mb", 20.0)
    max_rec = getattr(history_cfg, "max_records", 50000)

    if backend_type == "memory":
        return MemoryStorageBackend(max_memory_mb=max_mem, max_records=max_rec)

    # Fallback to memory for other types in phase 1
    return MemoryStorageBackend(max_memory_mb=max_mem, max_records=max_rec)


__all__ = [
    "ConsumptionRecord",
    "MeterReading",
    "ReadingRecord",
    "StorageBackend",
    "StorageSummary",
    "MemoryStorageBackend",
    "get_storage_backend",
]
