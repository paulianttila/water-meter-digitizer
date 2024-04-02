import configparser
import os
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


class ConfigurationMissing(Exception):
    pass


@dataclass
class ImagePosition:
    name: str
    x1: int
    y1: int
    w: int = 0
    h: int = 0


@dataclass
class RefImages:
    name: str
    fileName: str
    x: int
    y: int


@dataclass
class MeterConfig:
    name: str
    format: str
    consistencyEnabled: bool
    allowNegativeRates: bool
    maxRateValue: float
    usePreviuosValue: bool
    preValueFromFileMaxAge: int
    useExtendedResolution: bool = False


@dataclass
class Config:
    ##################  LoadFileFromHTTP Parameters ########################
    httpTimeoutLoadImage: int = 30
    httpImageUrl: str = ""
    httpImageMinSize: int = 10000
    httpImageLogFolder: str = ""
    httpLogOnlyFalsePictures: bool = False

    ##################  DigitalReadOut Parameters ########################
    digitalReadOutEnabled: bool = True
    digitModelFile: str = ""
    digitModel: str = ""
    digitDoImageLogging: bool = False
    digitImageLogFolder: str = "/log"
    cutDigitalDigit: List[ImagePosition] = field(default_factory=list)

    ##################  AnalogReadOut Parameters ########################
    analogReadOutEnabled: bool = False
    analogModelFile: str = ""
    analogModel: str = ""
    analogDoImageLogging: bool = False
    analogImageLogFolder: str = ""
    cutAnalogCounter: List[ImagePosition] = field(default_factory=list)

    ################## Alignment Parameters ###############################
    alignmentRotateAngle: float = 0.0
    alignmentRefImages: List[RefImages] = field(default_factory=list)

    ################## Meter Parameters ###############################
    meterConfigs: List[MeterConfig] = field(default_factory=list)

    def parseConfig(self, iniFile: str = "/config/config.ini"):
        # sourcery skip: avoid-builtin-shadow
        if not os.path.exists(iniFile):
            raise ConfigurationMissing("Configuration file '{iniFile}' not found")

        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(), allow_no_value=True
        )
        config.read(iniFile)

        ##################  LoadFileFromHTTP Parameters ########################
        self.httpTimeoutLoadImage = config.getint(
            "ImageSource", "TimeoutLoadImage", fallback=30
        )

        self.httpImageUrl = config.get("ImageSource", "URLImageSource", fallback="")

        self.httpImageMinSize = config.getint(
            "ImageSource", "MinImageSize", fallback=10000
        )
        self.httpImageLogFolder = config.get(
            "ImageSource", "LogImageLocation", fallback=""
        )

        self.httpLogOnlyFalsePictures = config.getboolean(
            "ImageSource", "LogOnlyFalsePictures", fallback=False
        )

        ##################  DigitalReadOut Parameters ########################

        self.digitalReadOutEnabled = config.getboolean(
            "DigitalReadOut", "Enabled", fallback=True
        )

        self.digitModelFile = config.get("Digits", "Modelfile", fallback="")
        self.digitModel = config.get("Digits", "Model", fallback="auto").lower()
        if self.digitModel not in ["auto", "digital", "digital100"]:
            raise ValueError(f"Unsupported model: {self.digitModel}")

        self.digitDoImageLogging = config.has_option("Digits", "LogImageLocation")
        self.digitImageLogFolder = config.get("Digits", "LogImageLocation", fallback="")

        digits = config.get("Digits", "names")
        for name in [x.strip() for x in digits.split(",")]:
            x1 = int(config[f"Digits.{name}"]["x"])
            y1 = int(config[f"Digits.{name}"]["y"])
            w = int(config[f"Digits.{name}"]["dx"])
            h = int(config[f"Digits.{name}"]["dy"])
            self.cutDigitalDigit.append(ImagePosition(name, x1, y1, w, h))

        ##################  AnalogReadOut Parameters ########################

        self.analogReadOutEnabled = config.getboolean(
            "AnalogReadOut", "Enabled", fallback=False
        )
        if self.digitModel not in ["auto", "analog", "analog100"]:
            raise ValueError(f"Unsupported model: {self.digitModel}")

        self.analogModelFile = config.get("Analog", "Modelfile", fallback="")
        self.analogModel = config.get("Digits", "Model", fallback="auto").lower()
        if self.digitModel not in ["auto", "analog", "analog100"]:
            raise ValueError(f"Unsupported model: {self.digitModel}")
        self.analogDoImageLogging = config.has_option("Analog", "LogImageLocation")
        self.analogImageLogFolder = config.get(
            "Analog", "LogImageLocation", fallback=""
        )

        analogs = config.get("Analog", "names")
        for name in [x.strip() for x in analogs.split(",")]:
            x1 = int(config[f"Analog.{name}"]["x"])
            y1 = int(config[f"Analog.{name}"]["y"])
            w = int(config[f"Analog.{name}"]["dx"])
            h = int(config[f"Analog.{name}"]["dy"])
            self.cutAnalogCounter.append(ImagePosition(name, x1, y1, w, h))

        ################## Alignment Parameters ###############################
        self.alignmentRotateAngle = config.getfloat(
            "Alignment", "InitialRotationAngle", fallback=0.0
        )

        refs = config.get("Alignment", "Refs", fallback="")
        for name in [x.strip() for x in refs.split(",")]:
            image = config.get(f"Alignment.{name}", "image", fallback="")
            x = config.getint(f"Alignment.{name}", "x", fallback=0)
            y = config.getint(f"Alignment.{name}", "y", fallback=0)
            self.alignmentRefImages.append(RefImages(name, image, x, y))

        ################## Meter Parameters ###############################
        meterVals = config.get("Meters", "Names", fallback="")
        for name in [x.strip() for x in meterVals.split(",")]:
            format = config.get(f"Meter.{name}", "Value", fallback="")
            consistencyEnabled = config.getboolean(
                f"Meter.{name}", "ConsistencyEnabled", fallback=False
            )
            allowNegativeRates = config.getboolean(
                f"Meter.{name}", "AllowNegativeRates", fallback=False
            )
            maxRateValue = config.getfloat(
                f"Meter.{name}", "MaxRateValue", fallback=0.0
            )
            usePreviuosValue = config.getboolean(
                f"Meter.{name}", "UsePreviuosValueFilling", fallback=False
            )
            preValueFromFileMaxAge = config.getint(
                f"Meter.{name}", "PreValueFromFileMaxAge", fallback=0
            )
            useExtendedResolution = config.getboolean(
                f"Meter.{name}", "UseExtendedResolution", fallback=False
            )
            self.meterConfigs.append(
                MeterConfig(
                    name,
                    format,
                    consistencyEnabled,
                    allowNegativeRates,
                    maxRateValue,
                    usePreviuosValue,
                    preValueFromFileMaxAge,
                    useExtendedResolution,
                )
            )
