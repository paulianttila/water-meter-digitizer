import io
from PIL import Image
import time
import os
import logging
import requests

logger = logging.getLogger(__name__)


class DownloadFailure(Exception):
    ...
    pass


class ImageLoader:
    def __init__(
        self,
        url: str,
        timeout: int = 30,
        minImageSize: int = 10000,
    ):
        self.imageUrl = url
        self.timeout = timeout
        self.minImageSize = minImageSize

    def loadImageFromUrl(self, url: str, timeout: int = 0) -> bytes:
        try:
            startTime = time.time()
            self.lastImageSaved = None
            if url is None or not url:
                url = self.imageUrl
            if timeout == 0:
                timeout = self.timeout
            data = self._readImageFromUrl(url, timeout)
            if self._verifyImage(data) is not True:
                raise DownloadFailure(f"Imagefile is corrupted, url: {str(url)}")
            size = len(data)
            if size < self.minImageSize:
                raise DownloadFailure(
                    f"Imagefile too small. Size {size}, min size is "
                    f"{str(self.minImageSize)}. url: {str(url)}"
                )
            return data
        except Exception as e:
            raise DownloadFailure(
                f"Image download failure from {str(url)}: {str(e)}"
            ) from e
        finally:
            logger.debug(f"Image downloaded in {time.time() - startTime:.3f} sec")

    def _readImageFromUrl(self, url: str, timeout: int) -> None:
        # Todo: limit file to one folder for security reasons
        if url.startswith("file://"):
            file = url[7:]
            with open(file, "rb") as f:
                return f.read()
        else:
            data = requests.get(url, timeout=timeout)
            return data.content

    def _verifyImage(self, data) -> bool:
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            return True
        except Exception as e:
            logger.warn(f"Image verification failed: {str(e)}")
            return False
