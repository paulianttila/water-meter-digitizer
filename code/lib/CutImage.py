import os
import numpy as np
import cv2
from PIL import Image
import logging
from lib.Config import Config, ImagePosition

logger = logging.getLogger(__name__)


class CutImage:
    def __init__(self, config: Config, imageTmpFolder="/image_tmp/"):
        self.imageTmpFolder = imageTmpFolder
        self.config = config
        self.referenceImages = []
        for file in self.config.cutReferenceName:
            if os.path.exists(file):
                logger.debug(f"Use reference image {file}")
                self.referenceImages.append(cv2.imread(file))
            else:
                logger.warn(f"Reference Image {file} not found")

    def cut(self, image):
        source = cv2.imread(image)
        cv2.imwrite(f"{self.imageTmpFolder}/original.jpg", source)
        target = self._rotateImage(source)
        cv2.imwrite(f"{self.imageTmpFolder}/rotated.jpg", target)
        target = self._align(target)
        cv2.imwrite(f"{self.imageTmpFolder}/aligned.jpg", target)

        digits = (
            self._cutImages(target, self.config.cutDigitalDigit)
            if self.config.digitalReadOutEnabled
            else []
        )
        analogs = (
            self._cutImages(target, self.config.cutAnalogCounter)
            if self.config.analogReadOutEnabled
            else []
        )
        return [analogs, digits]

    def _cutImages(self, source, imagePositions: ImagePosition):
        return [self.cutImage(source, digit) for digit in imagePositions]

    def cutImage(self, source, imgPosition: ImagePosition):
        x, y, w, h = imgPosition.x1, imgPosition.y1, imgPosition.w, imgPosition.h
        cropImg = source[y : y + h, x : x + w]
        cv2.imwrite(f"{self.imageTmpFolder}/{imgPosition.name}.jpg", cropImg)
        cropImg = cv2.cvtColor(cropImg, cv2.COLOR_BGR2RGB)
        return Image.fromarray(cropImg)

    def _align(self, source):
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

    def _getRefCoordinate(self, image, template):
        # method = cv2.TM_SQDIFF         #2
        method = cv2.TM_SQDIFF_NORMED  # 1
        # method = cv2.TM_CCORR_NORMED   #3
        method = cv2.TM_CCOEFF_NORMED  # 4
        res = cv2.matchTemplate(image, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc

    def _rotateImage(self, image):
        h, w, ch = image.shape
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, self.config.cutRotateAngle, 1.0)
        image = cv2.warpAffine(image, M, (w, h))
        return image

    def drawRoi(
        self,
        imageIn: str,
        imageOut: str = "/image_tmp/roi.jpg",
        drawRef=False,
        drawDig=True,
        drawCou=True,
    ):
        image = cv2.imread(imageIn)

        if drawRef:
            self._drawRef(image)

        if drawDig:
            self.drawDig(image)

        if drawCou:
            self.drawCou(image)

        cv2.imwrite(imageOut, image)

    def _drawRef(self, image):
        _colour = (255, 0, 0)
        d = 3
        for i in range(len(self.config.cutReferencePos)):
            x, y = self.config.cutReferencePos[i]
            h, w = self.referenceImages[i].shape[:2]
            cv2.rectangle(
                image, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), _colour, d
            )
            cv2.putText(
                image,
                self.config.cutReferenceName[i].replace("/config/", ""),
                (x, y - 5),
                0,
                0.4,
                _colour,
            )
        return image

    def drawCou(self, image):
        d_eclipse = 1
        d = 3
        for i in range(len(self.config.cutAnalogCounter)):
            imgPos = self.config.cutAnalogCounter[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                image,
                (x - d, y - d),
                (x + w + 2 * d, y + h + 2 * d),
                (0, 255, 0),
                d,
            )
            xct = int(x + w / 2) + 1
            yct = int(y + h / 2) + 1
            cv2.line(image, (x, yct), (x + w + 5, yct), (0, 255, 0), 1)
            cv2.line(image, (xct, y), (xct, y + h), (0, 255, 0), 1)
            cv2.ellipse(
                image,
                (xct, yct),
                (int(w / 2) + 2 * d_eclipse, int(h / 2) + 2 * d_eclipse),
                0,
                0,
                360,
                (0, 255, 0),
                d_eclipse,
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

    def drawDig(self, image):
        d = 3
        for i in range(len(self.config.cutDigitalDigit)):
            imgPos = self.config.cutDigitalDigit[i]
            x, y, w, h = imgPos.x1, imgPos.y1, imgPos.w, imgPos.h
            cv2.rectangle(
                image,
                (x - d, y - d),
                (x + w + 2 * d, y + h + 2 * d),
                (0, 255, 0),
                d,
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
