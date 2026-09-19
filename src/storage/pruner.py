"""Database retention enforcement, record pruning, and SQLite maintenance."""

import logging
import os
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, text

from .models import ReadingModel
from .snapshots import prune_disk_snapshots

logger = logging.getLogger(__name__)


def prune_database(
    session: Any,
    retention_days: int,
    max_records: int,
    is_sqlite: bool,
    is_memory: bool,
    auto_vacuum: bool,
    snapshots_dir: str | None = None,
    max_disk_mb: float = 500.0,
    memory_frames: OrderedDict[int, tuple[bytes, str]] | None = None,
) -> None:
    """Enforce time-based retention, max records limits, and snapshot storage caps."""
    now = datetime.now().astimezone()

    # 1. Time-based retention pruning
    if retention_days > 0:
        cutoff = now - timedelta(days=retention_days)
        old_rows = session.scalars(
            select(ReadingModel).where(ReadingModel.timestamp < cutoff)
        ).all()
        for r in old_rows:
            if r.frame_path and os.path.exists(r.frame_path):
                try:
                    os.remove(r.frame_path)
                except Exception as e:
                    logger.debug(
                        "Failed removing old snapshot file %s: %s", r.frame_path, e
                    )
        session.execute(delete(ReadingModel).where(ReadingModel.timestamp < cutoff))
        session.commit()

    # 2. Max row count limit (oldest-first FIFO)
    if max_records > 0:
        total_count = session.scalar(select(func.count(ReadingModel.id))) or 0
        if total_count > max_records:
            excess = total_count - max_records
            oldest_rows = session.scalars(
                select(ReadingModel)
                .order_by(ReadingModel.timestamp.asc())
                .limit(excess)
            ).all()
            oldest_ids = [r.id for r in oldest_rows]
            for r in oldest_rows:
                if r.frame_path and os.path.exists(r.frame_path):
                    try:
                        os.remove(r.frame_path)
                    except Exception as e:
                        logger.debug(
                            "Failed deleting snapshot file %s: %s", r.frame_path, e
                        )
                if memory_frames is not None:
                    memory_frames.pop(r.id, None)

            if oldest_ids:
                session.execute(
                    delete(ReadingModel).where(ReadingModel.id.in_(oldest_ids))
                )
                session.commit()

    # 3. Snapshot disk / file pruning
    prune_disk_snapshots(snapshots_dir, max_disk_mb)

    # 4. SQLite incremental vacuum to return freed pages to OS
    if is_sqlite and not is_memory and auto_vacuum:
        try:
            session.execute(text("PRAGMA incremental_vacuum"))
            session.commit()
        except Exception as e:
            logger.debug("Incremental vacuum ignored error: %s", e)
