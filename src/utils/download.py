import logging
import time

import requests

from utils.security import extract_file_path_from_uri, is_safe_path

logger = logging.getLogger(__name__)


class DownloadFailure(Exception):
    ...
    pass


def _download_http_stream(url: str, timeout: float) -> bytes:
    """Downloads an HTTP stream with connection/read timeouts and an explicit
    wall-clock watchdog over chunk iteration to prevent slowloris/stalled streams.
    """
    start_time = time.monotonic()
    t = float(timeout) if timeout > 0 else 10.0
    connect_timeout = min(t, 5.0)
    read_timeout = t

    try:
        with requests.get(
            url,
            timeout=(connect_timeout, read_timeout),
            stream=True,
        ) as resp:
            resp.raise_for_status()
            chunks: list[bytes] = []
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
                if t > 0 and (time.monotonic() - start_time) > t:
                    raise DownloadFailure(
                        f"Download exceeded wall-clock timeout of {timeout}s from {url}"
                    )
            return b"".join(chunks)
    except DownloadFailure:
        raise
    except requests.exceptions.Timeout as e:
        raise DownloadFailure(
            f"Download timed out after {timeout}s from {url}: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise DownloadFailure(f"HTTP request error from {url}: {e}") from e


def load_file_from_url(
    url: str,
    timeout: int | float = 10,
    min_file_size: int = 0,
    allowed_directories: list[str] | tuple[str, ...] | None = None,
) -> bytes:
    """Loads a file from the given URL or local file URI.

    Args:
        url (str): The URL or file:// URI of the file to be loaded.
        timeout (int | float, optional): The maximum time to wait for download in seconds.
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
    except DownloadFailure:
        raise
    except Exception as e:
        raise DownloadFailure(f"File download failure from {url}: {e!s}") from e
    finally:
        logger.debug(f"File downloaded in {time.time() - startTime:.3f} sec")


def _read_file_from_url(
    url: str,
    timeout: int | float,
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
    elif "mock_camera" in url or url.startswith("mock://"):
        from api.routes_mock_camera import render_mock_camera_from_url

        return render_mock_camera_from_url(url)
    else:
        return _download_http_stream(url, float(timeout))
