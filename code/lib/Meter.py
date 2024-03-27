import configparser
from dataclasses import dataclass
from lib.CutImage import CutImage
from lib.DigitalCounterCNN import DigitalCounterCNN
from lib.AnalogCounterCNN import AnalogCounterCNN
from lib.ImageLoader import DownloadFailure, ImageLoader
from lib.Config import Config
import math
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Value:
    value: str
    analogValue: str
    digitalValue: str


@dataclass
class ValueResult:
    newValue: Value
    previousValue: Value
    digitalResults: dict
    analogResults: dict
    error: str


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
            self._loadPrevalueFromFile(
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
            imageLogFolder=self.config.httpImageLogFolder,
            logOnlyFalsePictures=self.config.httpLogOnlyFalsePictures,
        )

    def _initAnalog(self):
        if self.config.analogReadOutEnabled:
            self.analogNeedleReader = AnalogCounterCNN(
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
            self.digitalDigitsReader = DigitalCounterCNN(
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

        self._storePrevalueToFile(self.prevValueFile)
        return float(result)

    def _storePrevalueToFile(self, file: str):
        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        config = configparser.ConfigParser()
        config.read(file)
        config["PreValue"]["LastVorkomma"] = self.lastDecimalPart
        if self.config.analogReadOutEnabled:
            config["PreValue"]["LastNachkomma"] = self.lastIntegerPart
        else:
            config["PreValue"]["LastNachkomma"] = "0"
        config["PreValue"]["Time"] = logtime
        with open(file, "w") as cfg:
            config.write(cfg)

    def _loadPrevalueFromFile(self, file: str, readPreValueFromFileMaxAge):
        config = configparser.ConfigParser()
        config.read(file)
        logtime = config["PreValue"]["Time"]

        fmt = "%Y-%m-%d_%H-%M-%S"
        #        d1 = datetime.strptime(nowtime, fmt)
        d1 = datetime.now()
        d2 = datetime.strptime(logtime, fmt)
        diff = (d1 - d2).days * 24 * 60

        if diff <= readPreValueFromFileMaxAge:
            self.lastDecimalPart = config["PreValue"]["LastVorkomma"]
            self.lastIntegerPart = config["PreValue"]["LastNachkomma"]
            zw = (
                f"Previous value loaded from file: "
                f"{self.lastIntegerPart}.{self.lastDecimalPart}"
            )

        else:
            self.lastDecimalPart = ""
            self.lastIntegerPart = ""
            zw = (
                f"Previous value not loaded from file as value is too old: "
                f"({str(diff)} minutes)."
            )

        logger.info(zw)

    def getROI(self, url: str, timeout: int = 0):
        self._removeFile(f"{self.imageTmpFolder}/original.jpg")

        self.imageLoader.loadImageFromUrl(
            url, f"{self.imageTmpFolder}/original.jpg", timeout
        )
        self.cutImageHandler.cut(f"{self.imageTmpFolder}/original.jpg")
        logger.debug("Start ROI")
        self.cutImageHandler.drawRoi(
            f"{self.imageTmpFolder}/aligned.jpg", f"{self.imageTmpFolder}/roi.jpg"
        )
        logger.debug("Get ROI done")

    def getMeterValue(
        self,
        url: str,
        usePreviuosValue: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
    ) -> ValueResult:

        logger.debug("Create previous values")
        previousValues = self._createPreviousValues()

        logger.debug("Load image")
        try:
            self.imageLoader.loadImageFromUrl(
                url, f"{self.imageTmpFolder}/original.jpg", timeout
            )
        except DownloadFailure as e:
            return self._makeReturnValues(True, f"{e}", previousValues)

        startTime = time.time()
        logger.debug("Start image cutting")
        cutIimages = self.cutImageHandler.cut(f"{self.imageTmpFolder}/original.jpg")

        logger.debug("Draw roi")
        self.cutImageHandler.drawRoi(
            f"{self.imageTmpFolder}/aligned.jpg", f"{self.imageTmpFolder}/roi.jpg"
        )

        if self.config.analogReadOutEnabled:
            logger.debug("Start analog readout")
            resultAnalog = self.analogNeedleReader.readout(cutIimages.analogImages)
        if self.config.digitalReadOutEnabled:
            logger.debug("Start digital readout")
            resultDigital = self.digitalDigitsReader.readout(cutIimages.digitalImages)

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
        self.imageLoader.postProcessLogImageProcedure(True)

        logger.debug("Check consistency")
        (consistencyError, errortxt) = self._checkConsistency(ignoreConsistencyCheck)

        logger.debug("Update last values")
        self._updateLastValues(consistencyError)

        logger.debug("Generate meter value result")
        (val, analogValue, digitalValue) = self._makeReturnValues(consistencyError)

        result = self._createValueResult(
            val,
            self._fillValueWithEndingZeros(len(resultAnalog), analogValue),
            self._fillValueWithLeadingZeros(len(resultDigital), digitalValue),
            resultDigital,
            resultAnalog,
            cutIimages,
            previousValues,
            errortxt,
        )
        logger.debug(
            f"Procesing time {time.time() - startTime:.3f} sec, result: {result}"
        )
        return result

    def _createPreviousValues(self) -> Value:
        if self.config.analogReadOutEnabled:
            prevValue = self.lastIntegerPart.lstrip("0") + "." + self.lastDecimalPart
        else:
            prevValue = self.lastIntegerPart.lstrip("0")
        val = None if prevValue == "." else prevValue
        digitalValue = None if self.lastIntegerPart == "" else self.lastIntegerPart
        analogValue = None if self.lastDecimalPart == "" else self.lastDecimalPart
        return Value(value=val, analogValue=analogValue, digitalValue=digitalValue)

    def _createValueResult(
        self,
        val,
        analogValue,
        digitalValue,
        resultDigital,
        resultAnalog,
        cutIimages,
        preval,
        error,
    ) -> ValueResult:

        value = Value(
            value=val,
            analogValue=analogValue,
            digitalValue=digitalValue,
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

    def _makeReturnValues(self, error):
        value = ""
        analogCounter = ""
        digit = ""
        if error:
            if self.config.errorReturn.find("Value") > -1:
                digit = str(self.currentIntegerPart)
                value = str(self.currentIntegerPart.lstrip("0"))
                if self.config.analogReadOutEnabled:
                    value = f"{value}.{str(self.currentDecimalPart)}"
                    analogCounter = str(self.currentDecimalPart)
        else:
            digit = str(self.currentIntegerPart.lstrip("0"))
            value = str(self.currentIntegerPart.lstrip("0"))
            if self.config.analogReadOutEnabled:
                value = f"{value}.{str(self.currentDecimalPart)}"
                analogCounter = str(self.currentDecimalPart)

        return (value, analogCounter, digit)

    def _updateLastValues(self, error):
        if "N" in self.currentIntegerPart:
            return
        if error:
            if self.config.errorReturn.find("NewValue") > -1:
                self.lastDecimalPart = self.currentDecimalPart
                self.lastIntegerPart = self.currentIntegerPart
            else:
                self.currentDecimalPart = self.lastDecimalPart
                self.currentIntegerPart = self.lastIntegerPart
        else:
            self.lastDecimalPart = self.currentDecimalPart
            self.lastIntegerPart = self.currentIntegerPart

        self._storePrevalueToFile(self.prevValueFile)

    def _checkConsistency(self, ignoreConsistencyCheck):
        error = False
        errortxt = ""
        if (
            (len(self.lastIntegerPart) > 0)
            and "N" not in self.currentIntegerPart
            and self.config.consistencyEnabled
        ):
            newValue = float(
                str(self.currentIntegerPart.lstrip("0"))
                + "."
                + str(self.currentDecimalPart)
            )
            oldValue = float(
                str(self.lastIntegerPart.lstrip("0")) + "." + str(self.lastDecimalPart)
            )
            delta = newValue - oldValue
            if not (self.config.allowNegativeRates) and (delta < 0):
                error = True
                errortxt = "Error - NegativeRate"
            if abs(delta) > self.config.maxRateValue:
                if error:
                    errortxt = "Error - RateTooHigh ({:.4f})" + errortxt.format(delta)
                else:
                    errortxt = "Error - RateTooHigh ({:.4f})".format(delta)
                error = True
            if self.config.errorReturn.find("ErrorMessage") == -1:
                errortxt = ""
            if error and (self.config.errorReturn.find("Readout") > -1):
                errortxt = (
                    errortxt + "\t" + str(newValue) if len(errortxt) else str(newValue)
                )
        return (error, errortxt)

    def _analogReadoutToValue(self, analogValues: list) -> str:
        prev = -1
        strValue = ""
        for item in analogValues[::-1]:
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

    def _removeFile(self, filename):
        if os.path.exists(filename):
            os.remove(filename)

    def _fillValueWithLeadingZeros(self, length: int, value: str) -> str:
        return value.zfill(length) if len(value) < length else value

    def _fillValueWithEndingZeros(self, length: int, value: str) -> str:
        while len(value) < length:
            value = f"{value}0"
        return value
