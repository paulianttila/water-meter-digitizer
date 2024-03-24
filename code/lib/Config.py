import configparser
import os
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Union

logger = logging.getLogger(__name__)


class ConfigurationMissing(Exception):
    pass


@dataclass
class Config:
    ##################  LoadFileFromHTTP Parameters ########################
    httpTimeoutLoadImage: int = 30
    httpImageUrl: str = ""
    httpImageLogFolder: str = ""
    httpLogOnlyFalsePictures: bool = False

    ##################  ConsistencyCheck Parameters ########################
    consistencyEnabled: bool = False
    allowNegativeRates: bool = True
    maxRateValue: float = None
    errorReturn: str = None
    readPreValueFromFileMaxAge: int = 0
    readPreValueFromFileAtStartup: bool = False

    ##################  DigitalReadOut Parameters ########################
    digitalReadOutEnabled: bool = True
    digitModelFile: str = ""
    digitDoImageLogging: bool = False
    digitImageLogFolder: str = ""
    digitLogImageNames: List[str] = field(default_factory=list)
    cutDigitalDigit: List[List[Union[str, Tuple[int, int, int, int]]]] = field(
        default_factory=list
    )

    ##################  AnalogReadOut Parameters ########################
    analogReadOutEnabled: bool = False
    analogModelFile: str = ""
    analogDoImageLogging: bool = False
    analogImageLogFolder: str = ""
    analogLogImageNames: List[str] = field(default_factory=list)

    cutAnalogCounter: List[List[Union[str, Tuple[int, int, int, int]]]] = field(
        default_factory=list
    )

    ################## ImageCut Parameters ###############################
    cutFastMode: bool = False
    cutRotateAngle: float = 0.0
    cutReferenceName: List[str] = field(default_factory=list)
    cutReferencePos: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        self.parseConfig()

    def parseConfig(self, iniFile: str = "./config/config.ini"):
        if not os.path.exists(iniFile):
            raise ConfigurationMissing("Configuration file not found")

        config = configparser.ConfigParser()
        config.read(iniFile)

        ##################  LoadFileFromHTTP Parameters ########################
        self.httpTimeoutLoadImage = config.getint(
            "Imagesource", "TimeoutLoadImage", fallback=30
        )

        self.httpImageUrl = config.get("Imagesource", "URLImageSource", fallback="")

        self.httpImageLogFolder = config.get(
            "Imagesource", "LogImageLocation", fallback=""
        )

        self.httpLogOnlyFalsePictures = config.getboolean(
            "Imagesource", "LogOnlyFalsePictures", fallback=False
        )

        ##################  ConsistencyCheck Parameters ########################

        self.consistencyEnabled = config.getboolean(
            "ConsistencyCheck", "Enabled", fallback=False
        )

        self.allowNegativeRates = config.getboolean(
            "ConsistencyCheck", "AllowNegativeRates", fallback=True
        )

        self.maxRateValue = config.getfloat(
            "ConsistencyCheck", "MaxRateValue", fallback=None
        )
        self.errorReturn = config.get("ConsistencyCheck", "ErrorReturn", fallback=None)

        self.readPreValueFromFileMaxAge = config.getint(
            "ConsistencyCheck", "ReadPreValueFromFileMaxAge", fallback=0
        )

        self.readPreValueFromFileAtStartup = config.getboolean(
            "ConsistencyCheck", "ReadPreValueFromFileAtStartup", fallback=False
        )

        ##################  DigitalReadOut Parameters ########################

        self.digitalReadOutEnabled = config.getboolean(
            "DigitalReadOut", "Enabled", fallback=True
        )

        self.digitModelFile = config.get("Digital_Digit", "Modelfile", fallback="")
        self.digitDoImageLogging = config.has_option(
            "Digital_Digit", "LogImageLocation"
        )
        self.digitImageLogFolder = config.get(
            "Digital_Digit", "LogImageLocation", fallback=""
        )
        digitLogNamesFull = config.get("Digital_Digit", "LogNames", fallback="")
        self.digitLogImageNames = []
        self.digitLogImageNames.extend(
            nm.strip() for nm in digitLogNamesFull.split(",")
        )

        digitalDigitFull = config.get("Digital_Digit", "names").split(",")
        self.cutDigitalDigit = []
        for nm in digitalDigitFull:
            nm = nm.strip()
            cnt = [nm]
            x1 = int(config[f"Digital_Digit.{nm}"]["pos_x"])
            y1 = int(config[f"Digital_Digit.{nm}"]["pos_y"])
            dx = int(config[f"Digital_Digit.{nm}"]["dx"])
            dy = int(config[f"Digital_Digit.{nm}"]["dy"])
            p_neu = (x1, y1, dx, dy)
            self.digitalDigitDefault = p_neu
            cnt.append(p_neu)
            self.cutDigitalDigit.append(cnt)

        ##################  AnalogReadOut Parameters ########################

        self.analogReadOutEnabled = config.getboolean(
            "AnalogReadOut", "Enabled", fallback=False
        )

        self.analogModelFile = config.get("Analog_Counter", "Modelfile", fallback="")
        self.analogDoImageLogging = config.has_option(
            "Analog_Counter", "LogImageLocation"
        )
        self.analogImageLogFolder = config.get(
            "Analog_Counter", "LogImageLocation", fallback=""
        )
        analogLogNamesFull = config.get("Analog_Counter", "LogNames", fallback="")
        self.analogLogImageNames = []
        self.analogLogImageNames.extend(
            nm.strip() for nm in analogLogNamesFull.split(",")
        )

        analogCounter = config.get("Analog_Counter", "names").split(",")
        self.cutAnalogCounter = []
        for nm in analogCounter:
            nm = nm.strip()
            cnt = [nm]
            x1 = int(config[f"Analog_Counter.{nm}"]["pos_x"])
            y1 = int(config[f"Analog_Counter.{nm}"]["pos_y"])
            dx = int(config[f"Analog_Counter.{nm}"]["dx"])
            dy = int(config[f"Analog_Counter.{nm}"]["dy"])
            p_neu = (x1, y1, dx, dy)
            self.analogCounterDefault = p_neu
            cnt.append(p_neu)
            self.cutAnalogCounter.append(cnt)

        ################## ImageCut Parameters ###############################
        self.cutFastMode = config.getboolean("alignment", "fastmode", fallback=False)

        self.cutRotateAngle = config.getfloat(
            "alignment", "initial_rotation_angle", fallback=0.0
        )

        self.cutReferenceName = [config.get("alignment.ref0", "image", fallback="")]
        self.cutReferenceName.append(config.get("alignment.ref1", "image", fallback=""))
        self.cutReferenceName.append(config.get("alignment.ref2", "image", fallback=""))

        self.cutReferencePos = [
            (
                config.getint("alignment.ref0", "pos_x", fallback=0),
                config.getint("alignment.ref0", "pos_y", fallback=0),
            )
        ]
        self.cutReferencePos.append(
            (
                config.getint("alignment.ref1", "pos_x", fallback=0),
                config.getint("alignment.ref1", "pos_y", fallback=0),
            )
        )
        self.cutReferencePos.append(
            (
                config.getint("alignment.ref2", "pos_x", fallback=0),
                config.getint("alignment.ref2", "pos_y", fallback=0),
            )
        )
