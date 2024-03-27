from PIL import Image
from shutil import copyfile
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
        imageLogFolder: str = None,
        logOnlyFalsePictures: bool = True,
    ):
        self.imageUrl = url
        self.timeout = timeout
        self.minImageSize = minImageSize
        self.imageLogFolder = imageLogFolder
        self.logOnlyFalsePictures = logOnlyFalsePictures
        self.lastImageSaved = None
        self._createFolders()

    def _createFolders(self) -> None:
        if len(self.imageLogFolder) > 0 and not os.path.exists(self.imageLogFolder):
            folders = self.imageLogFolder.split("/")
            path = folders[0]
            for folder in folders[1:]:
                path = f"{path}/{folder}"
                if not os.path.exists(path):
                    os.makedirs(path)

    def _readImageFromUrl(self, url: str, targetFile: str, timeout: int) -> None:
        # Todo: limit file to one folder for security reasons
        if url.startswith("file://"):
            file = url[7:]
            copyfile(file, targetFile)
        else:
            data = requests.get(url, timeout=timeout)
            with open(targetFile, "wb") as f:
                f.write(data.content)

    def loadImageFromUrl(self, url: str, targetFile: str, timeout: int = 0) -> None:
        try:
            startTime = time.time()
            self.lastImageSaved = None
            if url is None or not url:
                url = self.imageUrl
            if timeout == 0:
                timeout = self.timeout
            self._readImageFromUrl(url, targetFile, timeout)
            self._saveImageToLogFolder(targetFile)
            if self._verifyImage(targetFile) is not True:
                raise DownloadFailure(f"Imagefile is corrupted, url: {str(url)}")
            image_size = os.stat(targetFile).st_size
            if image_size < self.minImageSize:
                raise DownloadFailure(
                    f"Imagefile too small. Size {str(image_size)}, "
                    f"min size is {str(self.minImageSize)}. url: {str(url)}"
                )
        except Exception as e:
            raise DownloadFailure(
                f"Image download failure from {str(url)}: {str(e)}"
            ) from e
        finally:
            logger.debug(f"Image downloaded in {time.time() - startTime:.3f} sec")

    def postProcessLogImageProcedure(self, everythingsuccessfull) -> None:
        if (
            self.imageLogFolder is not None
            and self.logOnlyFalsePictures
            and self.lastImageSaved is not None
            and everythingsuccessfull
        ):
            os.remove(self.lastImageSaved)
            self.lastImageSaved = None

    def _verifyImage(self, imgFile) -> bool:
        try:
            image = Image.open(imgFile)
            image.verify()
            return True
        except OSError:
            return False

    def _saveImageToLogFolder(self, imageFile) -> None:
        if self.imageLogFolder is not None:
            logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
            filename = f"{self.imageLogFolder}/{logtime}.jpg"
            copyfile(imageFile, filename)
            self.lastImageSaved = filename
