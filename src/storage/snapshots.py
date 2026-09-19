"""Snapshot frame storage, encoding, fallback resolution, and disk retention management."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_mime(data: bytes, path_str: str = "") -> str:
    """Detect MIME type from image magic bytes or file extension."""
    if data.startswith(b"RIFF") or path_str.lower().endswith(".webp"):
        return "image/webp"
    if data.startswith(b"\x89PNG") or path_str.lower().endswith(".png"):
        return "image/png"
    return "image/jpeg"


def read_file_safe(p: Path | str) -> tuple[bytes | None, str | None]:
    """Safely read binary file contents and return with detected MIME type."""
    target = Path(p)
    if target.is_file():
        try:
            data = target.read_bytes()
            mime_type = detect_mime(data, str(target))
            logger.debug(
                "read_file_safe: successfully read %s (%d bytes, mime=%s)",
                target,
                len(data),
                mime_type,
            )
            return data, mime_type
        except Exception as e:
            logger.warning(
                "read_file_safe: error reading snapshot file %s: %s", target, e
            )
    else:
        logger.debug("read_file_safe: path does not exist: %s", target)
    return None, None


def ensure_snapshots_dir(snapshots_dir: str | None) -> Path | None:
    """Ensure that the snapshot storage directory exists on the filesystem."""
    if not snapshots_dir:
        return None
    p = Path(snapshots_dir)
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception as e:
        logger.warning(
            "Failed creating snapshots directory %s: %s. Falling back to in-memory/blob storage.",
            p,
            e,
        )
        return None


def prune_disk_snapshots(
    snapshots_dir: str | None,
    max_disk_mb: float = 500.0,
) -> int:
    """Prune snapshot files exceeding max disk quota, removing oldest first."""
    snap_dir = ensure_snapshots_dir(snapshots_dir)
    if not snap_dir or not snap_dir.exists():
        return 0

    target_max_mb = max_disk_mb or 500.0
    max_bytes = int(target_max_mb * 1024 * 1024)
    deleted_count = 0

    try:
        files = sorted(
            snap_dir.glob("*.*"),
            key=lambda f: f.stat().st_mtime,
        )
        total_size = sum(f.stat().st_size for f in files)

        for f in files:
            if total_size <= max_bytes:
                break
            sz = f.stat().st_size
            f.unlink(missing_ok=True)
            total_size -= sz
            deleted_count += 1
    except Exception as e:
        logger.debug("Error during snapshot disk pruning: %s", e)

    return deleted_count


def find_frame_bytes(
    reading_id: int,
    row_frame_path: str | None,
    row_frame_blob: bytes | None,
    memory_frames: dict[int, tuple[bytes, str]],
    snapshots_dir: str | None,
) -> tuple[bytes | None, str | None]:
    """Retrieve raw snapshot frame bytes and MIME type via ring buffer, row path, blob, or fallback search."""
    # 1. Check in-memory ring buffer
    if reading_id in memory_frames:
        data, _ftype = memory_frames[reading_id]
        mime = "image/webp" if data.startswith(b"RIFF") else "image/jpeg"
        logger.debug(
            "find_frame_bytes: found frame in memory ring buffer for reading_id=%s (%d bytes, %s)",
            reading_id,
            len(data),
            mime,
        )
        return data, mime

    # 2. Check explicit row path and relocations
    if row_frame_path:
        logger.debug(
            "find_frame_bytes: checking exact row.frame_path='%s'", row_frame_path
        )
        file_res = read_file_safe(row_frame_path)
        if file_res[0] is not None:
            return file_res[0], file_res[1]

        # Check inside configured snapshots_dir
        if snapshots_dir:
            candidate = Path(snapshots_dir) / Path(row_frame_path).name
            logger.debug(
                "find_frame_bytes: checking snapshots_dir/basename='%s'", candidate
            )
            file_res = read_file_safe(candidate)
            if file_res[0] is not None:
                return file_res[0], file_res[1]

            candidate_sub = Path(snapshots_dir) / row_frame_path
            logger.debug(
                "find_frame_bytes: checking snapshots_dir/relpath='%s'", candidate_sub
            )
            file_res = read_file_safe(candidate_sub)
            if file_res[0] is not None:
                return file_res[0], file_res[1]

        # Check inside common default locations
        for candidate_dir in [
            Path("snapshots"),
            Path("data/snapshots"),
            Path("/data/snapshots"),
            Path("/config/snapshots"),
        ]:
            candidate = candidate_dir / Path(row_frame_path).name
            logger.debug(
                "find_frame_bytes: checking fallback candidate '%s'", candidate
            )
            file_res = read_file_safe(candidate)
            if file_res[0] is not None:
                return file_res[0], file_res[1]

    # 3. Check binary blob in database row
    if row_frame_blob:
        logger.debug(
            "find_frame_bytes: returning frame_blob from DB row #%s (%d bytes)",
            reading_id,
            len(row_frame_blob),
        )
        return row_frame_blob, detect_mime(row_frame_blob)

    # 4. Fallback search across snapshot directories using reading_id pattern matching
    search_dirs: list[Path] = []
    if snapshots_dir:
        search_dirs.append(Path(snapshots_dir))
    for d in [
        Path("snapshots"),
        Path("data/snapshots"),
        Path("/data/snapshots"),
        Path("/config/snapshots"),
    ]:
        if d not in search_dirs:
            search_dirs.append(d)

    logger.debug(
        "find_frame_bytes: searching for snapshot files matching reading_id=%s in dirs: %s",
        reading_id,
        [str(d) for d in search_dirs],
    )

    for s_dir in search_dirs:
        if not s_dir.is_dir():
            logger.debug("find_frame_bytes: directory %s is not accessible/dir", s_dir)
            continue

        existing_files = [f.name for f in list(s_dir.glob("*.*"))[:15]]
        logger.debug(
            "find_frame_bytes: dir '%s' contains %d files (sample: %s)",
            s_dir,
            len(list(s_dir.glob("*.*"))),
            existing_files,
        )

        for pattern in [
            f"*_{reading_id}_*.*",
            f"*_{reading_id}.*",
            f"{reading_id}.*",
            f"frame_{reading_id}*.*",
            f"strip_{reading_id}*.*",
        ]:
            matches = sorted(
                list(s_dir.glob(pattern)),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if matches:
                logger.debug(
                    "find_frame_bytes: pattern '%s' matched file %s in %s",
                    pattern,
                    matches[0],
                    s_dir,
                )
                file_res = read_file_safe(matches[0])
                if file_res[0] is not None:
                    return file_res[0], file_res[1]

    logger.debug(
        "find_frame_bytes: no snapshot frame found for reading_id=%s",
        reading_id,
    )
    return None, None
