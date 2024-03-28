from dataclasses import dataclass, field

import os
from typing import List
import numpy as np
import cv2
from PIL import Image
import logging
from lib.Config import Config, ImagePosition

logger = logging.getLogger(__name__)


@dataclass
class CutImage:
    name: str
    image: Image


@dataclass
class CutResult:
    analogImages: List[CutImage]
    digitalImages: List[CutImage]

    def __init__(self, analogImages, digitalImages):
        self.analogImages = analogImages
        self.digitalImages = digitalImages


class ImageProcessor:
    def __init__(self, config: Config, imageTmpFolder="/image_tmp/"):
        self.imageTmpFolder = imageTmpFolder
        self.config = config
        self.referenceImages = []
        for file in self.config.cutReferenceName:
            if os.path.exists(file):
                logger.debug(f"Use reference image {file}")
                self.referenceImages.append(cv2.imread(file))
            else:
                logger.warning(f"Reference Image {file} not found")

    def convertImageToBytes(self, image: Image) -> bytes:
        success, buffer = cv2.imencode(".jpg", image)
        return buffer.tobytes()

    def loadImage(self, data: bytes) -> Image:
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    def rotate(self, image: Image, storeIntermediateFiles: bool = False) -> Image:
        image = self._rotateImage(image)
        if storeIntermediateFiles:
            cv2.imwrite(f"{self.imageTmpFolder}/rotated.jpg", image)
        return image

    def align(self, image: Image, storeIntermediateFiles: bool = False) -> Image:
        image = self._align(image)
        if storeIntermediateFiles:
            cv2.imwrite(f"{self.imageTmpFolder}/aligned.jpg", image)
        return image

    def cut(self, image: Image, storeIntermediateFiles: bool = False) -> CutResult:
        digits = (
            self._cutImages(image, self.config.cutDigitalDigit, storeIntermediateFiles)
            if self.config.digitalReadOutEnabled
            else []
        )
        analogs = (
            self._cutImages(image, self.config.cutAnalogCounter, storeIntermediateFiles)
            if self.config.analogReadOutEnabled
            else []
        )
        return CutResult(analogs, digits)

    def _cutImages(
        self,
        source,
        imagePositions: ImagePosition,
        storeIntermediateFiles: bool = False,
    ) -> List[CutImage]:
        return [
            CutImage(digit.name, self._cutImage(source, digit, storeIntermediateFiles))
            for digit in imagePositions
        ]

    def _cutImage(
        self, source, imgPosition: ImagePosition, storeIntermediateFiles: bool = False
    ) -> Image:
        x, y, w, h = imgPosition.x1, imgPosition.y1, imgPosition.w, imgPosition.h
        cropImg = source[y : y + h, x : x + w]
        if storeIntermediateFiles:
            cv2.imwrite(f"{self.imageTmpFolder}/{imgPosition.name}.jpg", cropImg)
        cropImg = cv2.cvtColor(cropImg, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cropImg)

    def _align(self, source) -> Image:
        h, w, ch = source.shape
        p0 = self._getRefCoordinate(source, self.referenceImages[0])
        p1 = self._getRefCoordinate(source, self.referenceImages[1])
        p2 = self._getRefCoordinate(source, self.referenceImages[2])

        pts1 = np.float32([p0, p1, p2])
        pts2 = np.float32(
            [
                self.config.cutReferencePos[0],
                self.config.cutReferencePos[1],
                self.config.cutReferencePos[2],
            ]
        )
        M = cv2.getAffineTransform(pts1, pts2)
        return cv2.warpAffine(source, M, (w, h))

    def _getRefCoordinate(self, image: Image, template):
        # method = cv2.TM_SQDIFF         #2
        method = cv2.TM_SQDIFF_NORMED  # 1
        # method = cv2.TM_CCORR_NORMED   #3
        method = cv2.TM_CCOEFF_NORMED  # 4
        res = cv2.matchTemplate(image, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc

    def _rotateImage(self, image: Image) -> Image:
        h, w, ch = image.shape
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, self.config.cutRotateAngle, 1.0)
        image = cv2.warpAffine(image, M, (w, h))
        return image

    def drawRoi(
        self,
        image: Image,
        storeToFile: bool = False,
        drawRef=False,
        drawDig=True,
        drawCou=True,
    ) -> Image:

        if drawRef:
            self._drawRef(image)

        if drawDig:
            self._drawDig(image)

        if drawCou:
            self._drawCou(image)

        if storeToFile:
            cv2.imwrite(f"{self.imageTmpFolder}/roi.jpg", image)

        return image

    def _drawRef(self, image: Image) -> Image:
        colour = (255, 0, 0)
        thickness = 3
        for i in range(len(self.config.cutReferencePos)):
            x, y = self.config.cutReferencePos[i]
            h, w = self.referenceImages[i].shape[:2]
            cv2.rectangle(
                image,
                (x - thickness, y - thickness),
                (x + w + 2 * thickness, y + h + 2 * thickness),
                colour,
                thickness,
            )
            cv2.putText(
                image,
                self.config.cutReferenceName[i].replace("/config/", ""),
                (x, y - 5),
                0,
                0.4,
                colour,
            )
        return image

    def _drawCou(self, image: Image) -> Image:
        eclipse = 1
        thickness = 3
        for i in range(len(self.config.cutAnalogCounter)):
            imgPos = self.config.cutAnalogCounter[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                image,
                (x - thickness, y - thickness),
                (x + w + 2 * thickness, y + h + 2 * thickness),
                (0, 255, 0),
                thickness,
            )
            xct = int(x + w / 2) + 1
            yct = int(y + h / 2) + 1
            cv2.line(image, (x, yct), (x + w + 5, yct), (0, 255, 0), 1)
            cv2.line(image, (xct, y), (xct, y + h), (0, 255, 0), 1)
            cv2.ellipse(
                image,
                (xct, yct),
                (int(w / 2) + 2 * eclipse, int(h / 2) + 2 * eclipse),
                0,
                0,
                360,
                (0, 255, 0),
                eclipse,
            )
            cv2.putText(
                image,
                imgPos.name,
                (x, y - 5),
                0,
                0.5,
                (0, 255, 0),
            )
        return image

    def _drawDig(self, image: Image) -> Image:
        thickness = 3
        for i in range(len(self.config.cutDigitalDigit)):
            imgPos = self.config.cutDigitalDigit[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                image,
                (x - thickness, y - thickness),
                (x + w + 2 * thickness, y + h + 2 * thickness),
                (0, 255, 0),
                thickness,
            )
            cv2.putText(
                image,
                imgPos.name,
                (x, y - 5),
                0,
                0.5,
                (0, 255, 0),
            )
        return image
