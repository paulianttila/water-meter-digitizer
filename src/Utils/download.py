import time
import logging
import requests

logger = logging.getLogger(__name__)


class DownloadFailure(Exception):
    ...
    pass


def load_file_from_url(url: str, timeout: int = 10, min_file_size: int = 0) -> bytes:
    """
    Loads an file from the given URL.

    Args:
        url (str): The URL of the file to be loaded.
        timeout (int, optional): The maximum time to wait for the file to be downloaded
        , in seconds. Defaults to 10.
        min_file_size (int, optional): The minimum size of the file in bytes.
        If the downloaded file is smaller than this size, a DownloadFailure exception
        will be raised. Defaults to 0.

    Returns:
        bytes: The file data as bytes.

    Raises:
        DownloadFailure: If the file download fails or the downloaded file is too
        small.

    """
    try:
        startTime = time.time()
        data = _read_file_from_url(url, timeout)
        size = len(data)
        if size < min_file_size:
            raise DownloadFailure(
                f"File too small. Size {size}, min size is {min_file_size}, "
                f"url: {url}"
            )
        return data
    except Exception as e:
        raise DownloadFailure(f"File download failure from {url}: {str(e)}") from e
    finally:
        logger.debug(f"File downloaded in {time.time() - startTime:.3f} sec")


def _read_file_from_url(url: str, timeout: int) -> None:
    # Todo: limit file to one folder for security reasons
    if url.startswith("file://"):
        file = url[7:]
        with open(file, "rb") as f:
            return f.read()
    else:
        data = requests.get(url, timeout=timeout)
        return data.content
