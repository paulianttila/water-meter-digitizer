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

        self.checkAndLoadDefaultConfig()

        self.lastImageSaved = ""

    def checkAndLoadDefaultConfig(self):
        if len(self.imageLogFolder) > 0 and not os.path.exists(self.imageLogFolder):
            zerlegt = self.imageLogFolder.split("/")
            pfad = zerlegt[0]
            for i in range(1, len(zerlegt)):
                pfad = f"{pfad}/{zerlegt[i]}"
                if not os.path.exists(pfad):
                    os.makedirs(pfad)

    def readImageFromUrl(self, event, url: str, target: str):
        if url.startswith("file://"):
            file = url[7:]
            copyfile(file, target)
        else:
            urllib.request.urlretrieve(url, target)
        event.set()

    def loadImageFromUrl(self, url: str, target: str, timeout: int):
        self.lastImageSaved = ""
        if url is None or not url:
            url = self.imageUrl
        event = Event()
        action_process = Process(
            target=self.readImageFromUrl, args=(event, url, target)
        )
        action_process.start()
        if timeout == 0:
            timeout = self.timeout
        action_process.join(timeout=timeout)
        action_process.terminate()
        #        action_process.close()

        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        if event.is_set():
            self.saveImageToLogFolder(target, logtime)
            if self.verifyImage(target) is True:
                image_size = os.stat(target).st_size
                if image_size < self.minImageSize:
                    DownloadFailure(
                        f"Imagefile too small. Size {str(image_size)}, min size is {str(self.minImageSize)}. url: {str(url)}"
                    )
            else:
                DownloadFailure(f"Imagefile is corrupted, url: {str(url)}")
        else:
            raise DownloadFailure(f"Image download failure from {str(url)}")
        return logtime

    def postProcessLogImageProcedure(self, everythingsuccessfull):
        if (
            (len(self.imageLogFolder) > 0)
            and self.logOnlyFalsePictures
            and (len(self.lastImageSaved) > 0)
            and everythingsuccessfull
        ):
            os.remove(self.lastImageSaved)
            self.lastImageSaved = ""

    def verifyImage(self, img_file):
        try:
            v_image = Image.open(img_file)
            v_image.verify()
            return True
        except OSError:
            return False

    def saveImageToLogFolder(self, imageFile, logtime):
        if len(self.imageLogFolder) > 0:
            filename = f"{self.imageLogFolder}/SourceImage_{logtime}.jpg"
            copyfile(imageFile, filename)
            self.lastImageSaved = filename
