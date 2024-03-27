import configparser
from dataclasses import dataclass
from typing import Union
from lib.CutImage import CutImage
from lib.DigitalCounterCNN import DigitalCounterCNN
from lib.AnalogCounterCNN import AnalogCounterCNN
from lib.ImageLoader import ImageLoader
from lib.Config import Config
import math
import os
import time
from datetime import datetime
import logging
from shutil import copyfile

logger = logging.getLogger(__name__)


@dataclass
class Value:
    value: Union[float, int]
    decimalPart: str
    integerPart: str


@dataclass
class ValueResult:
    newValue: Value
    previousValue: Value
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
            self.lastIntegerPart = ""
            self.lastDecimalPart = ""

        self.currentIntegerPart = ""
        self.currentDecimalPart = ""

        self._initAnalog()
        self._initDigital()

        self.cutImageHandler = CutImage(self.config, imageTmpFolder=imageTmpFolder)
        self.imageLoader = ImageLoader(
            url=self.config.httpImageUrl,
            timeout=self.config.httpTimeoutLoadImage,
            minImageSize=10000,
        )

    def _initAnalog(self):
        if self.config.analogReadOutEnabled:
            self.analogCounterReader = AnalogCounterCNN(
                modelfile=self.config.analogModelFile,
                dx=32,
                dy=32,
                imageTmpFolder=self.imageTmpFolder,
                imageLogFolder=self.config.analogImageLogFolder,
                imageLogNames=self.config.analogLogImageNames,
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
                imageTmpFolder=self.imageTmpFolder,
                imageLogFolder=self.config.digitImageLogFolder,
                imageLogNames=self.config.digitLogImageNames,
            )
            logger.debug("Digital model init done")
        else:
            logger.debug("Digital model disabled")

    def setPreviousValue(self, setValue: float) -> float:
        integer, decimals = str(setValue).split(".")
        nrOfDigits = len(self.config.cutDigitalDigit)
        digital = integer[:nrOfDigits]
        self.lastIntegerPart = self._fillValueWithLeadingZeros(nrOfDigits, digital)

        result = "N"
        if self.config.analogReadOutEnabled:
            nrOfAnalogs = len(self.config.cutAnalogCounter)
            analog = decimals[:nrOfAnalogs]
            self.lastDecimalPart = self._fillValueWithEndingZeros(nrOfAnalogs, analog)
            result = f"{self.lastIntegerPart}.{self.lastDecimalPart}"
        else:
            result = self.lastIntegerPart

        self._savePreviousValueToFile(self.prevValueFile)
        return float(result)

    def _savePreviousValueToFile(self, file: str):
        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        config = configparser.ConfigParser()
        config.read(file)
        config["PreviousValue"]["DecimalPart"] = self.lastDecimalPart
        if self.config.analogReadOutEnabled:
            config["PreviousValue"]["IntegerPart"] = self.lastIntegerPart
        else:
            config["PreviousValue"]["IntegerPart"] = "0"
        config["PreviousValue"]["Time"] = logtime
        with open(file, "w") as cfg:
            config.write(cfg)

    def _loadPreviousValueFromFile(self, file: str, readPreValueFromFileMaxAge):
        try:
            config = configparser.ConfigParser()
            config.read(file)
            logtime = config.get("PreviousValue", "Time")

            fmt = "%Y-%m-%d_%H-%M-%S"
            #        d1 = datetime.strptime(nowtime, fmt)
            d1 = datetime.now()
            d2 = datetime.strptime(logtime, fmt)
            diff = (d1 - d2).days * 24 * 60

            if diff <= readPreValueFromFileMaxAge:
                self.lastDecimalPart = config.get("PreviousValue", "DecimalPart")
                self.lastIntegerPart = config.get("PreviousValue", "IntegerPart")
                logger.info(
                    f"Previous value loaded from file: "
                    f"{self.lastIntegerPart}.{self.lastDecimalPart}"
                )
            else:
                self.lastDecimalPart = ""
                self.lastIntegerPart = ""
                logger.info(
                    f"Previous value not loaded from file as value is too old: "
                    f"({str(diff)} minutes)."
                )
        except Exception as e:
            logger.warn(f"Error occured during previous value loading: {str(e)}")

    def getROI(self, url: str, timeout: int = 0):
        IMAGE_FILE = f"{self.imageTmpFolder}/original.jpg"
        ALIGNED_FILE = f"{self.imageTmpFolder}/aligned.jpg"
        ROI_FILE = f"{self.imageTmpFolder}/roi.jpg"

        self._removeFileIfExists(IMAGE_FILE)
        self._loadImage(url, timeout, IMAGE_FILE)
        self.cutImageHandler.cut(IMAGE_FILE)
        logger.debug("Start ROI")
        self.cutImageHandler.drawRoi(ALIGNED_FILE, ROI_FILE)

    def getMeterValue(
        self,
        url: str,
        usePreviuosValue: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
    ) -> ValueResult:

        logger.debug("Create previous values")
        previousValue = self._createPreviousValues()

        IMAGE_FILE = f"{self.imageTmpFolder}/original.jpg"
        ALIGNED_FILE = f"{self.imageTmpFolder}/aligned.jpg"
        ROI_FILE = f"{self.imageTmpFolder}/roi.jpg"

        logger.debug("Load image")
        self._loadImage(url, timeout, IMAGE_FILE)

        startTime = time.time()
        logger.debug("Start image cutting")
        cutIimages = self.cutImageHandler.cut(IMAGE_FILE)

        logger.debug("Draw roi")
        self.cutImageHandler.drawRoi(ALIGNED_FILE, ROI_FILE)

        if self.config.analogReadOutEnabled:
            logger.debug("Start analog readout")
            resultAnalog = self.analogCounterReader.readout(cutIimages.analogImages)
        if self.config.digitalReadOutEnabled:
            logger.debug("Start digital readout")
            resultDigital = self.digitalCounterReader.readout(cutIimages.digitalImages)

        logger.debug("Start post processing")
        if self.config.analogReadOutEnabled:
            self.currentDecimalPart = self._analogReadoutToValue(resultAnalog)
        else:
            self.currentDecimalPart = 0
        if self.config.digitalReadOutEnabled:
            self.currentIntegerPart = self._digitalReadoutToValue(
                resultDigital,
                usePreviuosValue,
                self.lastDecimalPart,
                self.currentDecimalPart,
            )
        else:
            self.currentIntegerPart = 0

        logger.debug("Check consistency")
        if not ignoreConsistencyCheck:
            self._checkConsistency()

        logger.debug("Update last values")
        self._updateLastValues()

        logger.debug("Generate meter value result")
        currentValue = self._getCurrentValueAsNumber()
        newValue = Value(currentValue, self.currentDecimalPart, self.currentIntegerPart)

        result = self._createValueResult(
            newValue.value,
            self._fillValueWithEndingZeros(len(resultAnalog), newValue.decimalPart),
            self._fillValueWithLeadingZeros(len(resultDigital), newValue.integerPart),
            resultDigital,
            resultAnalog,
            cutIimages,
            previousValue,
            "",
        )
        logger.debug(
            f"Procesing time {time.time() - startTime:.3f} sec, result: {result}"
        )
        return result

    def _loadImage(self, url: str, timeout: int, file) -> None:
        data = self.imageLoader.loadImageFromUrl(url, timeout)
        self._saveImageToFile(file, data)
        if self.config.httpLogOnlyFalsePictures is False:
            self._copyImageToLogFolder(file)

    def _createPreviousValues(self) -> Value:
        prevValue = self._getPreviousValueAsNumber()
        integerPart = None if self.lastIntegerPart == "" else self.lastIntegerPart
        decimalPart = None if self.lastDecimalPart == "" else self.lastDecimalPart
        return Value(value=prevValue, decimalPart=decimalPart, integerPart=integerPart)

    def _createValueResult(
        self,
        val,
        decimalPart,
        integerPart,
        resultDigital,
        resultAnalog,
        cutIimages,
        preval,
        error,
    ) -> ValueResult:

        value = Value(
            value=val,
            decimalPart=decimalPart,
            integerPart=integerPart,
        )

        digitalResults = {}
        for i in range(len(resultDigital)):
            val = "NaN" if resultDigital[i] == "NaN" else str(int(resultDigital[i]))
            name = str(cutIimages.digitalImages[i][0])
            digitalResults[name] = val

        analogResults = {}
        if self.config.analogReadOutEnabled:
            for i in range(len(resultAnalog)):
                val = "{:.1f}".format(resultAnalog[i])
                name = str(cutIimages.analogImages[i][0])
                analogResults[name] = val

        return ValueResult(
            newValue=value,
            previousValue=preval,
            digitalResults=digitalResults,
            analogResults=analogResults,
            error=error,
        )

    def _updateLastValues(self):
        if "N" in self.currentIntegerPart:
            return
        self.lastDecimalPart = self.currentDecimalPart
        self.lastIntegerPart = self.currentIntegerPart
        self._savePreviousValueToFile(self.prevValueFile)

    def _checkConsistency(self):
        if (
            (len(self.lastIntegerPart) > 0)
            and "N" not in self.currentIntegerPart
            and self.config.consistencyEnabled
        ):
            delta = self._getCurrentValueAsNumber() - self._getPreviousValueAsNumber()
            if not (self.config.allowNegativeRates) and (delta < 0):
                raise ConcistencyError("Negative rate ({delta:.4f})")
            if abs(delta) > self.config.maxRateValue:
                raise ConcistencyError("Rate too high ({delta:.4f})")

    def _analogReadoutToValue(self, decimalParts: list) -> str:
        prev = -1
        strValue = ""
        for item in decimalParts[::-1]:
            prev = self._evaluateAnalogCounters(item, prev)
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

    def _digitalReadoutToValue(
        self,
        digitalValues: list,
        usePreviuosValue: bool,
        lastDecimalPart,
        currentDecimalPart,
    ) -> str:
        lastIntegerPart = self._fillValueWithLeadingZeros(
            len(digitalValues), self.lastIntegerPart
        )

        if (
            usePreviuosValue
            and str(self.lastIntegerPart) != ""
            and str(self.lastDecimalPart) != ""
        ):
            last = int(str(lastDecimalPart)[:1])
            aktu = int(str(currentDecimalPart)[:1])
            overZero = 1 if aktu < last else 0
        else:
            usePreviuosValue = False

        strValue = ""

        for i in range(len(digitalValues) - 1, -1, -1):
            digit = digitalValues[i]
            if digit == "NaN":
                if usePreviuosValue:
                    digit = int(lastIntegerPart[i])
                    if overZero:
                        digit += 1
                        if digit == 10:
                            digit = 0
                            overZero = 1
                        else:
                            overZero = 0
                else:
                    digit = "N"
            logger.debug(
                f"Digital value: {digitalValues[i]} "
                f"(prev value: {lastIntegerPart[i]}) -> {digit}"
            )
            strValue = f"{digit}{strValue}"

        return strValue

    def _removeFileIfExists(self, filename):
        if os.path.exists(filename):
            os.remove(filename)

    def _fillValueWithLeadingZeros(self, length: int, value: str) -> str:
        return value.zfill(length) if len(value) < length else value

    def _fillValueWithEndingZeros(self, length: int, value: str) -> str:
        while len(value) < length:
            value = f"{value}0"
        return value

    def _getCurrentValueAsNumber(self) -> Union[float, int]:
        if self.config.analogReadOutEnabled:
            return float(
                f"{self.currentIntegerPart.lstrip('0')}.{self.currentDecimalPart}"
            )
        else:
            return int(self.currentIntegerPart.lstrip("0"))

    def _getPreviousValueAsNumber(self) -> Union[float, int]:
        if self.config.analogReadOutEnabled:
            return float(f"{self.lastIntegerPart.lstrip('0')}.{self.lastDecimalPart}")
        else:
            return int(self.lastIntegerPart.lstrip("0"))

    def _saveImageToFile(self, file: str, data: bytes) -> None:
        with open(file, "wb") as f:
            f.write(data)

    def _copyImageToLogFolder(self, imageFile) -> None:
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
