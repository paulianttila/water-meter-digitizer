import configparser
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


class LoadFileFromHttp:
    def __init__(
        self,
        url: str,
        timeout: int = 30,
        minImageSize: int = 10000,
        imageLogFolder: str = None,
        logOnlyFalsePictures: bool = True,
    ):
        config = configparser.ConfigParser()
        config.read("./config/config.ini")

        self.imageUrl = url
        self.timeout = timeout
        self.minImageSize = minImageSize
        self.imageLogFolder = imageLogFolder
        self.logOnlyFalsePictures = logOnlyFalsePictures
        self.lastImageSaved = None
        self.createFolders()

    def createFolders(self):
        if len(self.imageLogFolder) > 0 and not os.path.exists(self.imageLogFolder):
            folders = self.imageLogFolder.split("/")
            path = folders[0]
            for folder in folders[1:]:
                path = f"{path}/{folder}"
                if not os.path.exists(path):
                    os.makedirs(path)

    def readImageFromUrl(self, event, url: str, target: str):
        if url.startswith("file://"):
            file = url[7:]
            copyfile(file, target)
        else:
            urllib.request.urlretrieve(url, target)
        event.set()

    def loadImageFromUrl(self, url: str, target: str, timeout: int):
        self.lastImageSaved = None
        if url is None or not url:
            url = self.imageUrl
        event = Event()
        actionProcess = Process(
            target=self.readImageFromUrl, args=(event, url, target)
        )
        actionProcess.start()
        if timeout == 0:
            timeout = self.timeout
        actionProcess.join(timeout=timeout)
        actionProcess.terminate()
        #actionProcess.close()

        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        if event.is_set():
            self.saveImageToLogFolder(target, logtime)
            if self.verifyImage(target) is True:
                image_size = os.stat(target).st_size
                if image_size < self.minImageSize:
                    DownloadFailure(
                        f"Imagefile too small. Size {str(image_size)}, "
                        "min size is {str(self.minImageSize)}. url: {str(url)}"
                    )
            else:
                DownloadFailure(f"Imagefile is corrupted, url: {str(url)}")
        else:
            raise DownloadFailure(f"Image download failure from {str(url)}")
        return logtime

    def postProcessLogImageProcedure(self, everythingsuccessfull):
        if (
            self.imageLogFolder is not None
            and self.logOnlyFalsePictures
            and self.lastImageSaved is not None
            and everythingsuccessfull
        ):
            os.remove(self.lastImageSaved)
            self.lastImageSaved = None

    def verifyImage(self, imgFile):
        try:
            v_image = Image.open(imgFile)
            v_image.verify()
            return True
        except OSError:
            return False

    def saveImageToLogFolder(self, imageFile, logtime):
        if self.imageLogFolder is not None:
            filename = f"{self.imageLogFolder}/SourceImage_{logtime}.jpg"
            copyfile(imageFile, filename)
            self.lastImageSaved = filename
