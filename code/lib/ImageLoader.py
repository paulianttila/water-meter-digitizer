import urllib.request
from multiprocessing import Process, Event
from PIL import Image
from shutil import copyfile
import time
import os
import logging

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

    def _readImageFromUrl(self, event, url: str, target: str) -> None:
        # Todo: limit file to one folder for security reasons
        if url.startswith("file://"):
            file = url[7:]
            copyfile(file, target)
        else:
            urllib.request.urlretrieve(url, target)
        event.set()

    def loadImageFromUrl(self, url: str, target: str, timeout: int) -> None:
        self.lastImageSaved = None
        if url is None or not url:
            url = self.imageUrl
        event = Event()
        actionProcess = Process(
            target=self._readImageFromUrl, args=(event, url, target)
        )
        actionProcess.start()
        if timeout == 0:
            timeout = self.timeout
        actionProcess.join(timeout=timeout)
        actionProcess.terminate()
        if not event.is_set():
            raise DownloadFailure(f"Image download failure from {str(url)}")
        self._saveImageToLogFolder(target)
        if self._verifyImage(target) is True:
            image_size = os.stat(target).st_size
            if image_size < self.minImageSize:
                DownloadFailure(
                    f"Imagefile too small. Size {str(image_size)}, "
                    f"min size is {str(self.minImageSize)}. url: {str(url)}"
                )
        else:
            DownloadFailure(f"Imagefile is corrupted, url: {str(url)}")

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
            v_image = Image.open(imgFile)
            v_image.verify()
            return True
        except OSError:
            return False

    def _saveImageToLogFolder(self, imageFile) -> None:
        if self.imageLogFolder is not None:
            logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
            filename = f"{self.imageLogFolder}/{logtime}.jpg"
            copyfile(imageFile, filename)
            self.lastImageSaved = filename
