import configparser
from dataclasses import dataclass
from lib.CNNBase import ReadoutResult
from lib.ImageProcessor import ImageProcessor
from lib.DigitalCounterCNN import DigitalCounterCNN
from lib.AnalogNeedleCNN import AnalogNeedleCNN
from lib.ImageLoader import loadImageFromUrl
from lib.Config import Config
import math
import os
import time
from datetime import datetime
import logging
from shutil import copyfile

logger = logging.getLogger(__name__)


@dataclass
class ValueResult:
    value: str
    rawValue: str
    previousValue: str
    digitalResults: dict
    analogResults: dict
    error: str


class ConcistencyError(Exception):
    ...
    pass


class ValueError(Exception):
    ...
    pass


class Meter:
    def __init__(
        self,
        configFile: str = "/config/config.ini",
        prevValueFile: str = "/config/prevalue.ini",
        imageTmpFolder: str = "/tmp_images",
    ):
        logger.debug("Start Init Meter Reader")
        self.prevValueFile = prevValueFile
        self.imageTmpFolder = imageTmpFolder
        self.config = Config()
        self.config.parseConfig(configFile)

        if self.config.readPreValueFromFileAtStartup:
            self._loadPreviousValueFromFile(
                self.prevValueFile, self.config.readPreValueFromFileMaxAge
            )
        else:
            self.previousValue = ""
        self.currentValue = ""

        self._initAnalog()
        self._initDigital()

        self.imageProcessor = ImageProcessor(self.config, imageTmpFolder=imageTmpFolder)

    def _initAnalog(self):
        if self.config.analogReadOutEnabled:
            self.analogCounterReader = AnalogNeedleCNN(
                modelfile=self.config.analogModelFile,
                dx=32,
                dy=32,
                imageLogFolder=self.config.analogImageLogFolder,
            )
            logger.debug("Analog model init done")
        else:
            logger.debug("Analog model disabled")

    def _initDigital(self):
        if self.config.digitalReadOutEnabled:
            self.digitalCounterReader = DigitalCounterCNN(
                modelfile=self.config.digitModelFile,
                dx=20,
                dy=32,
                imageLogFolder=self.config.digitImageLogFolder,
            )
            logger.debug("Digital model init done")
        else:
            logger.debug("Digital model disabled")

    def _savePreviousValueToFile(self, file: str):
        logtime = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime())
        config = configparser.ConfigParser()
        config.read(file)
        config["PreviousValue"]["Time"] = logtime
        config["PreviousValue"]["Value"] = self.previousValue
        with open(file, "w") as cfg:
            config.write(cfg)

    def _loadPreviousValueFromFile(self, file: str, readPreValueFromFileMaxAge):
        try:
            config = configparser.ConfigParser()
            config.read(file)
            time = config.get("PreviousValue", "Time")

            valueTime = datetime.strptime(time, "%Y.%m.%d %H:%M:%S")
            diff = (datetime.now() - valueTime).days * 24 * 60

            if diff <= readPreValueFromFileMaxAge:
                self.previousValue = config.get("PreviousValue", "Value")
                logger.info(
                    f"Previous value loaded from file: " f"{self.previousValue}"
                )
            else:
                self.previousValue = ""
                logger.info(
                    f"Previous value not loaded from file as value is too old: "
                    f"({str(diff)} minutes)."
                )
        except Exception as e:
            logger.warning(f"Error occured during previous value loading: {str(e)}")

    def getROI(self, url: str = None, timeout: int = 0):
        data = loadImageFromUrl(
            url=url if url is not None else self.config.httpImageUrl,
            timeout=timeout if timeout != 0 else self.config.httpTimeoutLoadImage,
            minImageSize=self.config.httpImageMinSize,
        )
        if self.imageProcessor.verifyImage(data) is not True:
            raise ValueError("Downloaded image file is corrupted")

        image = self.imageProcessor.loadImage(data)
        image = self.imageProcessor.rotate(image)
        image = self.imageProcessor.align(image)
        logger.debug("Start ROI")
        image = self.imageProcessor.drawRoi(image, storeToFile=True)


    def getMeterValue(
        self,
        url: str = None,
        usePreviuosValue: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
        saveImages: bool = False,
    ) -> ValueResult:

        logger.debug("Load image")
        data = loadImageFromUrl(
            url=url if url is not None else self.config.httpImageUrl,
            timeout=timeout if timeout != 0 else self.config.httpTimeoutLoadImage,
            minImageSize=self.config.httpImageMinSize,
        )
        if self.imageProcessor.verifyImage(data) is not True:
            raise ValueError("Downloaded image file is corrupted")

        if self.config.httpLogOnlyFalsePictures is False:
            self._saveImageToFile(f"{self.imageTmpFolder}/original.jpg", data)

        startTime = time.time()
        logger.debug("Start image cutting")
        image = self.imageProcessor.loadImage(data)
        image = self.imageProcessor.rotate(image, storeIntermediateFiles=saveImages)
        image = self.imageProcessor.align(image, storeIntermediateFiles=saveImages)
        cutIimages = self.imageProcessor.cut(image, storeIntermediateFiles=saveImages)
        if saveImages:
            self.imageProcessor.drawRoi(image, storeToFile=True)

        if self.config.analogReadOutEnabled:
            logger.debug("Start analog readout")
            resultAnalog = self.analogCounterReader.readout(cutIimages.analogImages)
        if self.config.digitalReadOutEnabled:
            logger.debug("Start digital readout")
            resultDigital = self.digitalCounterReader.readout(cutIimages.digitalImages)

        logger.debug("Start post processing")
        if self.config.analogReadOutEnabled:
            currentDecimalPart = self._analogReadoutToValue(resultAnalog)
        else:
            currentDecimalPart = ""

        if self.config.digitalReadOutEnabled:
            currentIntegerPartRaw = self._digitalReadoutToRawValue(resultDigital)
            currentIntegerPart = self._digitalReadoutToValue(
                resultDigital,
                usePreviuosValue,
                currentDecimalPart,
            )

        else:
            currentIntegerPart = ""

        self.currentValue = self._createTotalValue(
            currentIntegerPart, currentDecimalPart
        )
        currentRawValue = f"{currentIntegerPartRaw}.{currentDecimalPart}"

        if not ignoreConsistencyCheck and self.config.consistencyEnabled:
            logger.debug("Check consistency")
            self._checkConsistency(self.currentValue, self.previousValue)

        logger.debug("Update last values")
        self._updateLastValues()

        logger.debug("Generate meter value result")

        result = self._createValueResult(
            self.currentValue,
            currentRawValue,
            resultDigital,
            resultAnalog,
            self.previousValue,
            "",
        )
        logger.debug(
            f"Procesing time {time.time() - startTime:.3f} sec, result: {result}"
        )
        return result

    def _createValueResult(
        self,
        currentValue,
        currentRawValue,
        resultDigital,
        resultAnalog,
        previousValue,
        error,
    ) -> ValueResult:

        digitalResults = {}
        for item in resultDigital:
            val = "NaN" if item.value == "NaN" else str(int(item.value))
            digitalResults[item.name] = val

        analogResults = {}
        if self.config.analogReadOutEnabled:
            for item in resultAnalog:
                val = "{:.1f}".format(item.value)
                analogResults[item.name] = val

        return ValueResult(
            value=currentValue,
            rawValue=currentRawValue,
            previousValue=previousValue if previousValue != "" else None,
            digitalResults=digitalResults,
            analogResults=analogResults,
            error=error,
        )

    def _updateLastValues(self):
        if "N" in self.currentValue:
            return
        self.previousValue = self.currentValue
        self._savePreviousValueToFile(self.prevValueFile)

    def _checkConsistency(self, currentValue: str, previousValue: str):
        if previousValue.isnumeric() and currentValue.isnumeric():
            delta = float(currentValue) - float(self.previousValue)
            if not (self.config.allowNegativeRates) and (delta < 0):
                raise ConcistencyError("Negative rate ({delta:.4f})")
            if abs(delta) > self.config.maxRateValue:
                raise ConcistencyError("Rate too high ({delta:.4f})")
        return currentValue

    def _analogReadoutToValue(self, decimalParts: list[ReadoutResult]) -> str:
        prev = -1
        strValue = ""
        for item in decimalParts[::-1]:
            prev = self._evaluateAnalogCounters(item.value, prev)
            strValue = f"{prev}{strValue}"
        return strValue

    def _evaluateAnalogCounters(self, newValue, prevValue: int) -> int:
        decimalPart = math.floor((newValue * 10) % 10)
        integerPart = math.floor(newValue % 10)

        if prevValue == -1:
            result = integerPart
        else:
            result_rating = decimalPart - prevValue
            if decimalPart >= 5:
                result_rating -= 5
            else:
                result_rating += 5
            result = round(newValue)
            if result_rating < 0:
                result -= 1
            if result == -1:
                result += 10

        result = result % 10
        logger.debug(f"Analog value: {newValue} (prev value: {prevValue}) -> {result}")
        return result

    def _digitalReadoutToRawValue(
        self,
        digitalValues: list[ReadoutResult],
    ) -> str:

        strValue = ""

        for i in range(len(digitalValues) - 1, -1, -1):
            digit = digitalValues[i].value
            if digit == "NaN":
                digit = "N"
            strValue = f"{digit}{strValue}"

        return strValue

    def _digitalReadoutToValue(
        self,
        digitalValues: list[ReadoutResult],
        usePreviuosValue: bool,
        currentDecimalPart: str,
    ) -> str:

        previousIntegerPart, previousDecimalPart = self.previousValue.split(".")
        previousIntegerPart = self._fillValueWithLeadingZeros(
            len(digitalValues), previousIntegerPart
        )

        if (
            usePreviuosValue
            and str(previousIntegerPart) != ""
            and str(previousDecimalPart) != ""
        ):
            previousMostSignificantDigit = int(previousDecimalPart[:1])
            currentMostSignificantDigit = int(currentDecimalPart[:1])
            rollover = currentMostSignificantDigit < previousMostSignificantDigit
        else:
            usePreviuosValue = False

        strValue = ""

        for i in range(len(digitalValues) - 1, -1, -1):
            digit = digitalValues[i].value
            if digit == "NaN":
                if usePreviuosValue:
                    digit = int(previousIntegerPart[i])
                    if rollover:
                        digit += 1
                        if digit == 10:
                            digit = 0
                            rollover = True
                        else:
                            rollover = False
                else:
                    digit = "N"
            logger.debug(
                f"Digital value: {digitalValues[i]} "
                f"(prev value: {previousIntegerPart[i]}) -> {digit}"
            )
            strValue = f"{digit}{strValue}"

        return strValue

    def _createTotalValue(self, integerPart: str, decimalPart: str) -> str:
        if self.config.analogReadOutEnabled and self.config.digitalReadOutEnabled:
            return f"{integerPart}.{decimalPart}"
        if (
            self.config.analogReadOutEnabled is False
            and self.config.digitalReadOutEnabled
        ):
            return f"{integerPart}"
        if (
            self.config.analogReadOutEnabled
            and self.config.digitalReadOutEnabled is False
        ):
            return f"{decimalPart}"
        return ""

    def _fillValueWithLeadingZeros(self, length: int, value: str) -> str:
        return value.zfill(length) if len(value) < length else value

    def _fillValueWithEndingZeros(self, length: int, value: str) -> str:
        while len(value) < length:
            value = f"{value}0"
        return value

    def _saveImageToFile(self, file: str, data: bytes) -> None:
        with open(file, "wb") as f:
            f.write(data)

    def _copyImageToLogFolder(self, imageFile: str) -> None:
        self._createFolders(self.config.httpImageLogFolder)
        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        filename = f"{self.config.httpImageLogFolder }/{logtime}.jpg"
        copyfile(imageFile, filename)

    def _createFolders(self, path: str) -> None:
        if path != "" and not os.path.exists(path):
            folders = path.split("/")
            path = folders[0]
            for folder in folders[1:]:
                path = f"{path}/{folder}"
                if not os.path.exists(path):
                    os.makedirs(path)
