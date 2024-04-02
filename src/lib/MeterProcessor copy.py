from dataclasses import dataclass
import re
from typing import List, Union
from lib.Utils.FileUtils import saveFile
from lib.PreviousValueFile import (
    loadPreviousValueFromFile,
    loadPreviousValueFromFileNew,
    savePreviousValueToFile,
    savePreviousValueToFileNew,
)
from lib.Utils.MathUtils import fillValueWithLeadingZeros, fillWithPredecessorDigits
from lib.readout import convertReadoutToValue
from lib.CNN.CNNBase import ModelDetails, ReadoutResult
from lib.Utils.ImageProcessor import CutResult, ImageProcessor
from lib.CNN.DigitalCounterCNN import DigitalCounterCNN
from lib.CNN.AnalogNeedleCNN import AnalogNeedleCNN
from lib.Utils.ImageLoader import loadImageFromUrl
from lib.Config import Config, MeterConfig
import math
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValueResult:
    value: str
    rawValue: str
    previousValue: str
    digitalResults: dict
    analogResults: dict
    error: str


@dataclass
class MeterValue:
    name: str
    value: str


@dataclass
class MeterResult:
    meters: List[MeterValue]
    digitalResults: dict
    analogResults: dict
    error: str


@dataclass
class Meter:
    name: str = None
    value: str = None
    rawValue: str = None
    previousValue: str = None
    config: MeterConfig = None


class ConcistencyError(Exception):
    ...
    pass


class ValueError(Exception):
    ...
    pass


class MeterProcessor:
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
            self.previousValue = loadPreviousValueFromFile(
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

    def getMeters(
        self,
        url: str = None,
        usePreviuosValue: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
        saveImages: bool = False,
    ) -> MeterResult:

        data = self._downloadImage(url, timeout)
        startTime = time.time()
        cutIimages = self._cutImages(data, storeIntermediateFiles=saveImages)
        self._doCCN(cutIimages)

        logger.debug("Start value evalution")
        availableValues = {}
        model = self._getModel(
            self.config.analogModel, self.analogCounterReader.getModelDetails()
        )
        for item in self.cnnAnalogResults:
            val = self._evaluateAnalogCounter(
                name=item.name, newValue=item.value, model=model
            )
            availableValues[item.name] = val

        model = self._getModel(
            self.config.digitModel, self.digitalCounterReader.getModelDetails()
        )
        for item in self.cnnDigitalResults:
            val = self._evaluateDigitalCounter(
                name=item.name, newValue=item.value, model=model
            )
            availableValues[item.name] = val
        logger.debug(f"Available values: {availableValues}")

        logger.debug("Generate meter values")
        meters = []
        for meterConfig in self.config.meterConfigs:
            value = meterConfig.format.format(**availableValues)
            meter = Meter(
                name=meterConfig.name, value=value, rawValue=value, config=meterConfig
            )
            meters.append(meter)
        logger.info(f" Meters: {meters}")

        # logger.debug("STOP TESTING")
        # result = convertReadoutToValue(cnnAnalogResults, "Analogue100", True, -1)
        # logger.debug(f"Analog readout result: {result}")
        # firstDigit = result[0] if result != "" else -1
        # result = convertReadoutToValue(
        #    cnnDigitalResults, "Digital", False, int(firstDigit)
        # )
        # logger.debug(f"Digital readout result: {result}")
        # logger.debug("STOP TESTING")

        logger.debug("Start post processing")
        cnnResults = self.cnnDigitalResults + self.cnnAnalogResults
        self.postprocessMeterValues(meters, availableValues, cnnResults)

        logger.debug("Generate result")
        result = self._genResult(meters)

        logger.debug(
            f"Procesing time {time.time() - startTime:.3f} sec, result: {result}"
        )
        return result

    def _genResult(self, meters: List[Meter]):
        analogResults = {}
        if self.config.analogReadOutEnabled:
            for item in self.cnnAnalogResults:
                val = "{:.2f}".format(item.value)
                analogResults[item.name] = val
        digitalResults = {}
        for item in self.cnnDigitalResults:
            val = "N" if item.value == "NaN" else str(int(item.value))
            digitalResults[item.name] = val

        meterResults = [
            MeterValue(name=meter.name, value=meter.value) for meter in meters
        ]
        return MeterResult(
            meters=meterResults,
            digitalResults=digitalResults,
            analogResults=analogResults,
            error="",
        )

    def _downloadImage(self, url: str, timeout: int):
        url = url if url is not None else self.config.httpImageUrl
        logger.debug(f"Load image from {url}")
        data = loadImageFromUrl(
            url=url,
            timeout=timeout if timeout != 0 else self.config.httpTimeoutLoadImage,
            minImageSize=self.config.httpImageMinSize,
        )
        if self.imageProcessor.verifyImage(data) is not True:
            raise ValueError("Downloaded image file is corrupted")

        if self.config.httpLogOnlyFalsePictures is False:
            saveFile(f"{self.imageTmpFolder}/original.jpg", data)
        return data

    def _cutImages(
        self, data: bytes, storeIntermediateFiles: bool = False
    ) -> CutResult:
        logger.debug("Start image cutting")
        image = self.imageProcessor.loadImage(data)
        image = self.imageProcessor.rotate(image, storeIntermediateFiles)
        image = self.imageProcessor.align(image, storeIntermediateFiles)
        cutIimages = self.imageProcessor.cut(image, storeIntermediateFiles)
        if storeIntermediateFiles:
            self.imageProcessor.drawRoi(image, storeToFile=True)
        return cutIimages

    def _doCCN(self, images: CutResult):
        self.cnnAnalogResults = []
        self.cnnDigitalResults = []
        if self.config.analogReadOutEnabled:
            logger.debug("Start analog readout")
            self.cnnAnalogResults = self.analogCounterReader.readout(
                images.analogImages
            )
            logger.debug(f"Analog CNN results: {self.cnnAnalogResults}")
        if self.config.digitalReadOutEnabled:
            logger.debug("Start digital readout")
            self.cnnDigitalResults = self.digitalCounterReader.readout(
                images.digitalImages
            )
            logger.debug(f"Digital CNN results: {self.cnnDigitalResults}")

    def postprocessMeterValues(
        self,
        meters: List[Meter],
        values: dict,
        cnnResults: List[ReadoutResult],
    ):
        # for easier access
        meterDict = {meter.name: meter for meter in meters}
        cnnResultsDict = {item.name: item for item in cnnResults}

        for meter in meters:
            self.postprocessMeterValue(
                meterDict[meter.name],
                values,
                cnnResultsDict,
            )

    def postprocessMeterValue(
        self,
        meter: Meter,
        values: dict,
        cnnResults: dict,
    ):
        if meter.config.consistencyEnabled is False:
            return

        logger.info(f" Postprocess meter, paramters: {meter}")

        meter.previousValue = loadPreviousValueFromFileNew(
            self.prevValueFile, meter.name, meter.config.readPreValueFromFileMaxAge
        )
        if meter.config.useExtendedResolution:
            meter.value = self._getExtendedResolution(meter, cnnResults)
            if len(meter.value) == (len(meter.previousValue) + 1):
                meter.previousValue = f"{meter.previousValue}0"

        if meter.previousValue is not None:
            meter.value = fillWithPredecessorDigits(meter.value, meter.previousValue)
            self._checkConsistency(meter.value, meter.previousValue)
            savePreviousValueToFileNew(self.prevValueFile, meter.name, meter.value)

    def _getExtendedResolution(self, meter: Meter, values: dict):
        # get last digit of the value
        names = re.findall(r"\{(.*?)\}", meter.config.format)
        lastDigit = values[names[-1]]
        resultAfterDecimalPoint = math.floor(float(lastDigit.value) * 10 + 10) % 10
        return f"{meter.value}{resultAfterDecimalPoint}"

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
            saveFile(f"{self.imageTmpFolder}/original.jpg", data)

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
        savePreviousValueToFile(self.prevValueFile, self.previousValue)

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
            prev = self._evaluateAnalogCounter(
                name=item.name, newValue=item.value, prevValue=prev
            )
            strValue = f"{prev}{strValue}"
        return strValue

    def _evaluateAnalogCounter(
        self, name: str, newValue, prevValue: int = -1, model: str = None
    ) -> int:
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
        logger.debug(f"{name}: {newValue} (prev value: {prevValue}) -> {result}")
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
        previousIntegerPart = fillValueWithLeadingZeros(
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
                f"{digitalValues[i].name}: {digitalValues[i]} "
                f"(prev value: {previousIntegerPart[i]}) -> {digit}"
            )
            strValue = f"{digit}{strValue}"

        return strValue

    def _evaluateDigitalCounter(
        self,
        name: str,
        newValue: Union[float, int],
        prevValue: int = -1,
        model: str = None,
    ) -> int:
        if model.lower() == "digital100":
            digit = (
                "N" if newValue < 0 or newValue >= 100 else int(round(newValue / 10))
            )
        elif model.lower() == "digital":
            digit = "N" if newValue < 0 or newValue >= 10 else newValue
        logger.debug(f"{name}: {newValue}  -> {digit}")
        return digit

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

    def _getModel(self, model: str, details: ModelDetails) -> str:
        if model.lower() != "auto":
            return model
        if details.numerOutput == 2:
            return "analog"
        if details.numerOutput == 11:
            return "digital"
        if details.numerOutput == 100:
            if details.xsize == 32 and details.ysize == 32:
                return "analog100"
            return "digital100"
