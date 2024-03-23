import configparser
import os
from shutil import copyfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationMissing(Exception):
    ...
    pass


class Config:
    def __init__(
        self,
        path: Path,
        defaultPath: str = "./config_default/",
        configreroute: str = "./config/",
        initializeConfig: bool = True,
    ):
        self.iniFile = "config.ini"
        self.preValueFile = "prevalue.ini"
        self.pathToConfig = path
        self.configExist = False
        if initializeConfig:
            self.checkAndLoadDefaultConfig(defaultPath)
        self.parseConfig()
        self.configOriginalPath = "./config/"
        self.configReroutePath = configreroute

    def parseConfig(self):
        pfadini = str(self.pathToConfig.joinpath("config.ini"))
        self.configExist = os.path.exists(pfadini)

        if not self.configExist:
            raise ConfigurationMissing("Configuration file not found")

        config = configparser.ConfigParser()
        config.read(pfadini)

        ##################  LoadFileFromHTTP Parameters ########################
        self.httpTimeoutLoadImage = config.getint(
            "Imagesource", "TimeoutLoadImage", fallback=30
        )

        self.httpImageUrl = config.get("Imagesource", "URLImageSource", fallback="")

        self.httpImageLogFolder = config.get("Imagesource", "LogImageLocation", fallback="")

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
        self.Cut_FastMode = config.getboolean("alignment", "fastmode", fallback=False)

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

    def CutGetAnalogCounter(self):
        return (self.analogReadOutEnabled, self.cutAnalogCounter)

    def CutGetDigitalDigit(self):
        return self.cutDigitalDigit

    def CutPreRotateAngle(self):
        return self.cutRotateAngle

    def CutReferenceParameter(self):
        return (self.cutReferenceName, self.cutReferencePos)

    def LoadHTTPParameter(self):
        return (
            self.httpTimeoutLoadImage,
            self.httpImageUrl,
            self.httpImageLogFolder,
            self.httpLogOnlyFalsePictures,
        )

    def ZaehlerAnalogEnabled(self):
        return self.analogReadOutEnabled

    def ZaehlerConsistency(self):
        return (
            self.consistencyEnabled,
            self.allowNegativeRates,
            self.maxRateValue,
            self.errorReturn,
        )

    def ZaehlerReadPrevalue(self):
        return (
            self.readPreValueFromFileAtStartup,
            self.readPreValueFromFileMaxAge,
        )

    def DigitModelFile(self):
        return self.digitModelFile

    def DigitGetLogInfo(self):
        return (
            self.digitDoImageLogging,
            self.digitLogImageNames,
            self.digitImageLogFolder,
        )

    def AnalogModelFile(self):
        return self.analogModelFile

    def AnalogGetLogInfo(self):
        return (
            self.analogDoImageLogging,
            self.analogLogImageNames,
            self.analogImageLogFolder,
        )

    def ConfigRerouteConfig(self):
        return (self.configOriginalPath, self.configReroutePath)

    def checkAndLoadDefaultConfig(self, defaultdir):
        zw = str(self.pathToConfig.joinpath(self.iniFile))
        if not os.path.exists(zw):
            for file in os.listdir(defaultdir):
                if os.path.isdir(defaultdir + file):
                    shutil.copytree(
                        defaultdir + file, str(self.pathToConfig.joinpath(file))
                    )
                else:
                    zw = str(self.pathToConfig.joinpath(file))
                    shutil.copyfile(defaultdir + file, zw)
        zw = str(self.pathToConfig.joinpath(self.preValueFile))
        if not os.path.exists(zw):
            copyfile(defaultdir + self.preValueFile, zw)
