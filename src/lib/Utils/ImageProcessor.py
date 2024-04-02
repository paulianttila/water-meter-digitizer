from dataclasses import dataclass

import io
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
        for item in self.config.alignmentRefImages:
            if os.path.exists(item.fileName):
                logger.debug(f"Use reference image {item.fileName}")
                self.referenceImages.append(cv2.imread(item.fileName))
            else:
                logger.warning(f"Reference Image {item.fileName} not found")

    def verifyImage(self, data: bytes) -> bool:
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            return True
        except Exception as e:
            logger.warning(f"Image verification failed: {str(e)}")
            return False

    def convertBGRtoRGB(self, image: Image) -> Image:
        success, buffer = cv2.imencode(".jpg", image)
        return self.convBytesToImage(buffer.tobytes())

    def convBytesToImage(self, data: bytes) -> Image:
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    def convRGBimageToBytes(self, image: Image) -> bytes:
        success, buffer = cv2.imencode(".jpg", image)
        return buffer.tobytes()

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
        source: Image,
        imagePositions: ImagePosition,
        storeIntermediateFiles: bool = False,
    ) -> List[CutImage]:
        return [
            CutImage(digit.name, self._cutImage(source, digit, storeIntermediateFiles))
            for digit in imagePositions
        ]

    def _cutImage(
        self,
        source: Image,
        imgPosition: ImagePosition,
        storeIntermediateFiles: bool = False,
    ) -> Image:
        x, y, w, h = imgPosition.x1, imgPosition.y1, imgPosition.w, imgPosition.h
        cropImg = source[y : y + h, x : x + w]
        if storeIntermediateFiles:
            cv2.imwrite(f"{self.imageTmpFolder}/{imgPosition.name}.jpg", cropImg)
        cropImg = cv2.cvtColor(cropImg, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cropImg)

    def _align(self, source: Image) -> Image:
        h, w, ch = source.shape

        refImageCordinates = [
            self._getRefCoordinate(source, self.referenceImages[i])
            for i in range(len(self.referenceImages))
        ]

        alignmentRefPos = [
            (
                self.config.alignmentRefImages[i].x,
                self.config.alignmentRefImages[i].y,
            )
            for i in range(len(self.config.alignmentRefImages))
        ]
        pts1 = np.float32(refImageCordinates)
        pts2 = np.float32(alignmentRefPos)
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
        M = cv2.getRotationMatrix2D(center, self.config.alignmentRotateAngle, 1.0)
        image = cv2.warpAffine(image, M, (w, h))
        return image

    def drawROI(
        self,
        image: Image,
        storeToFile: bool = False,
        rawRefs=False,
        drawDigitals=True,
        drawAnalogs=True,
    ) -> Image:

        if rawRefs:
            self._drawRefs(image)

        if drawDigitals:
            self._drawDigitals(image)

        if drawAnalogs:
            self._drawAnalogs(image)

        if storeToFile:
            cv2.imwrite(f"{self.imageTmpFolder}/roi.jpg", image)

        return image

    def _drawRefs(self, image: Image) -> Image:
        colour = (255, 0, 0)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.alignmentRefImages)):
            ref = self.config.alignmentRefImages[i]
            x, y = ref.x, ref.y
            h, w = self.referenceImages[i].shape[:2]
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            cv2.putText(
                img=image,
                text=ref.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.4,
                color=colour,
            )
        return image

    def _drawAnalogs(self, image: Image) -> Image:
        eclipse = 1
        colour = (0, 255, 0)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.cutAnalogCounter)):
            imgPos = self.config.cutAnalogCounter[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            xct = int(x + w / 2) + 1
            yct = int(y + h / 2) + 1
            cv2.line(image, (x, yct), (x + w + 5, yct), colour, 1)
            cv2.line(image, (xct, y), (xct, y + h), colour, 1)
            cv2.ellipse(
                img=image,
                center=(xct, yct),
                axes=(int(w / 2) + 2 * eclipse, int(h / 2) + 2 * eclipse),
                angle=0,
                startAngle=0,
                endAngle=360,
                color=colour,
                thickness=eclipse,
            )
            cv2.putText(
                img=image,
                text=imgPos.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.5,
                color=colour,
            )
        return image

    def _drawDigitals(self, image: Image) -> Image:
        colour = (0, 255, 255)
        thickness = 3
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(len(self.config.cutDigitalDigit)):
            imgPos = self.config.cutDigitalDigit[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                img=image,
                pt1=(x - thickness, y - thickness),
                pt2=(x + w + 2 * thickness, y + h + 2 * thickness),
                color=colour,
                thickness=thickness,
            )
            cv2.putText(
                img=image,
                text=imgPos.name,
                org=(x, y - 8),
                fontFace=font,
                fontScale=0.5,
                color=colour,
            )
        return image

    def _getOptimalFontScale(
        self, text: str, width: int, fontFace=cv2.FONT_HERSHEY_SIMPLEX, thickness=1
    ):
        for scale in reversed(range(0, 60, 1)):
            textSize = cv2.getTextSize(
                text,
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=scale / 10,
                thickness=1,
            )
            new_width = textSize[0][0]
            if new_width <= width:
                return scale / 10
        return 1
