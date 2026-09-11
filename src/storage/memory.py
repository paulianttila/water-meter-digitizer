from .sql import SQLAlchemyStorageBackend


class MemoryStorageBackend(SQLAlchemyStorageBackend):
    """In-memory SQLite storage backed by SQLAlchemy."""

    def __init__(
        self,
        max_memory_mb: float = 20.0,
        max_records: int = 50000,
        retention_days: int = 30,
        auto_vacuum: bool = True,
        prune_interval: int = 50,
        snapshot_mode: str = "smart_tiered",
    ) -> None:
        super().__init__(
            db_url="sqlite:///:memory:",
            max_memory_mb=max_memory_mb,
            retention_days=retention_days,
            max_records=max_records,
            auto_vacuum=auto_vacuum,
            prune_interval=prune_interval,
            snapshots_dir=None,
            snapshot_mode=snapshot_mode,
        )


__all__ = ["MemoryStorageBackend"]
