import base64
from dataclasses import dataclass
import re
from typing import List, Union
from lib.Utils.FileUtils import saveFile
from lib.PreviousValueFile import (
    loadPreviousValueFromFile,
    savePreviousValueToFile,
)
from lib.Utils.MathUtils import (
    fillValueWithEndingZeros,
    fillWithPredecessorDigits,
)
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
        self._initAnalog()
        self._initDigital()
        self.imageProcessor = ImageProcessor(self.config, imageTmpFolder=imageTmpFolder)

    def getROI(self, url: str = None, timeout: int = 0) -> str:
        data = self._downloadImage(url, timeout)
        image = self.imageProcessor.convBytesToImage(data)
        image = self.imageProcessor.rotate(image)
        image = self.imageProcessor.align(image)
        logger.debug("Draw ROI")
        image = self.imageProcessor.drawROI(image)
        image = self.imageProcessor.convertBGRtoRGB(image)
        b = self.imageProcessor.convRGBimageToBytes(image)
        return base64.b64encode(b).decode()

    def getMeters(
        self,
        url: str = None,
        timeout: int = 0,
        saveImages: bool = False,
    ) -> MeterResult:

        data = self._downloadImage(url, timeout, storeIntermediateFiles=saveImages)
        startTime = time.time()
        cutIimages = self._cutImages(data, storeIntermediateFiles=saveImages)
        self._doCCN(cutIimages)
        availableValues = self._evaluateCCNresults()
        meters = self._getMeterValues(availableValues)
        self._postprocessMeterValues(
            meters=meters,
            values=availableValues,
            cnnResults=(self.cnnDigitalResults + self.cnnAnalogResults),
        )
        result = self._genResult(meters)

        logger.debug(
            f"Procesing time {time.time() - startTime:.3f} sec, result: {result}"
        )
        return result

    def _getMeterValues(self, availableValues: dict):
        meters = []
        for meterConfig in self.config.meterConfigs:
            value = meterConfig.format.format(**availableValues)
            meter = Meter(
                name=meterConfig.name, value=value, rawValue=value, config=meterConfig
            )
            meters.append(meter)
        logger.info(f" Meters: {meters}")
        return meters

    def _evaluateCCNresults(self) -> dict[str, int]:
        availableValues = {}
        model = self._solveModel(
            self.config.analogModel, self.analogCounterReader.getModelDetails()
        )
        for item in self.cnnAnalogResults:
            val = self._evaluateAnalogCounter(
                name=item.name, newValue=item.value, model=model
            )
            availableValues[item.name] = val

        model = self._solveModel(
            self.config.digitModel, self.digitalCounterReader.getModelDetails()
        )
        for item in self.cnnDigitalResults:
            val = self._evaluateDigitalCounter(
                name=item.name, newValue=item.value, model=model
            )
            availableValues[item.name] = val
        logger.debug(f"Available values: {availableValues}")
        return availableValues

    def _genResult(self, meters: List[Meter]) -> MeterResult:
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

    def _downloadImage(
        self, url: str, timeout: int, storeIntermediateFiles: bool = False
    ) -> bytes:
        url = url if url is not None else self.config.httpImageUrl
        logger.debug(f"Load image from {url}")
        data = loadImageFromUrl(
            url=url,
            timeout=timeout if timeout != 0 else self.config.httpTimeoutLoadImage,
            minImageSize=self.config.httpImageMinSize,
        )
        if self.imageProcessor.verifyImage(data) is not True:
            raise ValueError("Downloaded image file is corrupted")

        if storeIntermediateFiles:
            saveFile(f"{self.imageTmpFolder}/original.jpg", data)
        return data

    def _cutImages(
        self, data: bytes, storeIntermediateFiles: bool = False
    ) -> CutResult:
        image = self.imageProcessor.convBytesToImage(data)
        image = self.imageProcessor.rotate(image, storeIntermediateFiles)
        image = self.imageProcessor.align(image, storeIntermediateFiles)
        cutIimages = self.imageProcessor.cut(image, storeIntermediateFiles)
        if storeIntermediateFiles:
            self.imageProcessor.drawROI(image, storeToFile=True)
        return cutIimages

    def _doCCN(self, images: CutResult) -> None:
        self.cnnAnalogResults = []
        self.cnnDigitalResults = []
        if self.config.analogReadOutEnabled:
            self.cnnAnalogResults = self.analogCounterReader.readout(
                images.analogImages
            )
            logger.debug(f"Analog CNN results: {self.cnnAnalogResults}")
        if self.config.digitalReadOutEnabled:
            self.cnnDigitalResults = self.digitalCounterReader.readout(
                images.digitalImages
            )
            logger.debug(f"Digital CNN results: {self.cnnDigitalResults}")

    def _postprocessMeterValues(
        self,
        meters: List[Meter],
        values: dict,
        cnnResults: List[ReadoutResult],
    ) -> None:
        # for easier access
        meterDict = {meter.name: meter for meter in meters}
        cnnResultsDict = {item.name: item for item in cnnResults}

        for meter in meters:
            self._postprocessMeterValue(
                meterDict[meter.name],
                values,
                cnnResultsDict,
            )

    def _postprocessMeterValue(
        self,
        meter: Meter,
        values: dict,
        cnnResults: dict,
    ) -> None:
        if meter.config.consistencyEnabled is False:
            return

        logger.info(f" Postprocess meter, paramters: {meter}")

        if meter.config.usePreviuosValue:
            meter.previousValue = loadPreviousValueFromFile(
                self.prevValueFile, meter.name, meter.config.preValueFromFileMaxAge
            )

        if meter.config.useExtendedResolution:
            meter.value = self._getExtendedResolution(meter, cnnResults)
        if meter.config.usePreviuosValue:
            meter.previousValue = self._adaptPrevalueToMacthLen(
                meter.value, meter.previousValue
            )
            meter.value = fillWithPredecessorDigits(meter.value, meter.previousValue)
            self._checkConsistency(meter, meter.value, meter.previousValue)
            savePreviousValueToFile(self.prevValueFile, meter.name, meter.value)

    def _adaptPrevalueToMacthLen(self, newValue: str, previousValue: str) -> str:
        if len(newValue) > len(previousValue):
            logger.debug(
                f"Fill previousValue {previousValue} to match newValue {newValue} len"
            )
            previousValue = fillValueWithEndingZeros(len(newValue), previousValue)
        elif len(newValue) < len(previousValue):
            logger.debug(
                f"Remove digits from previousValue {previousValue} to match "
                f"newValue {newValue} len"
            )
            previousValue = previousValue[: len(newValue)]
        return previousValue

    def _getExtendedResolution(self, meter: Meter, values: dict) -> str:
        # get last digit of the value
        names = re.findall(r"\{(.*?)\}", meter.config.format)
        lastDigit = values[names[-1]]
        resultAfterDecimalPoint = math.floor(float(lastDigit.value) * 10 + 10) % 10
        return f"{meter.value}{resultAfterDecimalPoint}"

    def _checkConsistency(
        self, meter: Meter, currentValue: str, previousValue: str
    ) -> str:
        if previousValue.isnumeric() and currentValue.isnumeric():
            delta = float(currentValue) - float(self.previousValue)
            if not (meter.config.allowNegativeRates) and (delta < 0):
                raise ConcistencyError("Negative rate ({delta:.4f})")
            if abs(delta) > meter.config.maxRateValue:
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

    def _solveModel(self, model: str, details: ModelDetails) -> str:
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

    def _initAnalog(self) -> None:
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

    def _initDigital(self) -> None:
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
