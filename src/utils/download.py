import logging
import time

import requests

from utils.security import extract_file_path_from_uri, is_safe_path

logger = logging.getLogger(__name__)


class DownloadFailure(Exception):
    ...
    pass


def load_file_from_url(
    url: str,
    timeout: int = 10,
    min_file_size: int = 0,
    allowed_directories: list[str] | tuple[str, ...] | None = None,
) -> bytes:
    """
    Loads a file from the given URL or local file URI.

    Args:
        url (str): The URL or file:// URI of the file to be loaded.
        timeout (int, optional): The maximum time to wait for download in seconds.
        min_file_size (int, optional): The minimum size of the file in bytes.
        allowed_directories (list[str], optional): List of allowed directory paths
            when url uses file://.

    Returns:
        bytes: The file data as bytes.

    Raises:
        DownloadFailure: If the file download fails, path is restricted,
            or size is too small.
    """
    startTime = time.time()
    try:
        data = _read_file_from_url(
            url, timeout, allowed_directories=allowed_directories
        )
        size = len(data)
        if size < min_file_size:
            raise DownloadFailure(
                f"File too small. Size {size}, min size is {min_file_size}, "
                f"url: {url}"
            )
        return data
    except Exception as e:
        raise DownloadFailure(f"File download failure from {url}: {e!s}") from e
    finally:
        logger.debug(f"File downloaded in {time.time() - startTime:.3f} sec")


def _read_file_from_url(
    url: str,
    timeout: int,
    allowed_directories: list[str] | tuple[str, ...] | None = None,
) -> bytes:
    if url.startswith("file://"):
        file_path = extract_file_path_from_uri(url)
        if allowed_directories and not is_safe_path(file_path, allowed_directories):
            raise DownloadFailure(
                f"Access to local file '{file_path}' is denied. "
                "Path is outside configured asset directories."
            )
        with open(file_path, "rb") as f:
            return f.read()
    else:
        data = requests.get(url, timeout=timeout)
        return data.content
