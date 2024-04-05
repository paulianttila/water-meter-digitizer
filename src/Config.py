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
    file_name: str
    x: int
    y: int
    w: int = 0
    h: int = 0


@dataclass
class MeterConfig:
    name: str
    format: str
    consistency_enabled: bool
    allow_negative_rates: bool
    max_rate_value: float
    use_previuos_value: bool
    pre_value_from_file_max_age: int
    use_extended_resolution: bool = False
    unit: str = None


@dataclass
class Config:
    log_level: str = "INFO"
    image_tmp_dir: str = "/image_tmp"
    config_dir: str = "/config"
    prevoius_value_file: str = "/config/prevalue.ini"

    ##################  LoadFileFromHTTP Parameters ########################
    http_load_image_timeout: int = 30
    http_image_url: str = ""
    http_image_min_size: int = 10000
    http_image_log_dir: str = ""
    http_log_only_false_pictures: bool = False

    ##################  DigitalReadOut Parameters ########################
    digital_readout_enabled: bool = True
    digit_model_file: str = ""
    digit_model: str = ""
    digit_do_image_logging: bool = False
    digit_image_log_dir: str = "/log"
    cut_digital_digit: List[ImagePosition] = field(default_factory=list)

    ##################  AnalogReadOut Parameters ########################
    analog_readout_enabled: bool = False
    analog_model_file: str = ""
    analog_model: str = ""
    analog_do_image_logging: bool = False
    analog_image_log_dir: str = ""
    cut_analog_counter: List[ImagePosition] = field(default_factory=list)

    ################## Alignment Parameters ###############################
    alignment_rotate_angle: float = 0.0
    alignment_ref_images: List[RefImages] = field(default_factory=list)

    ################## Meter Parameters ###############################
    meter_configs: List[MeterConfig] = field(default_factory=list)

    def load_config(self, ini_file: str = "config.ini"):
        # sourcery skip: avoid-builtin-shadow
        if not os.path.exists(ini_file):
            raise ConfigurationMissing(f"Configuration file '{ini_file}' not found")

        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(), allow_no_value=True
        )
        config.read(ini_file)

        ################## General Parameters ##################################
        self.log_level = config.get("DEFAULT", "LogLevel", fallback="INFO")
        self.image_tmp_dir = config.get("DEFAULT", "ImageTmpDir", fallback="/image_tmp")
        self.config_dir = config.get("DEFAULT", "ConfigDir", fallback="/config")
        self.prevoius_value_file = config.get(
            "DEFAULT", "PreviousValueFile", fallback="/config/prevalue.ini"
        )

        ##################  LoadFileFromHTTP Parameters ########################
        self.http_load_image_timeout = config.getint(
            "ImageSource", "TimeoutLoadImage", fallback=30
        )

        self.http_image_url = config.get("ImageSource", "URLImageSource", fallback="")

        self.http_image_min_size = config.getint(
            "ImageSource", "MinImageSize", fallback=10000
        )
        self.http_image_log_dir = config.get(
            "ImageSource", "LogImageLocation", fallback=""
        )

        self.http_log_only_false_pictures = config.getboolean(
            "ImageSource", "LogOnlyFalsePictures", fallback=False
        )

        ##################  DigitalReadOut Parameters ########################

        self.digital_readout_enabled = config.getboolean(
            "DigitalReadOut", "Enabled", fallback=True
        )

        self.digit_model_file = config.get("Digits", "Modelfile", fallback="")
        self.digit_model = config.get("Digits", "Model", fallback="auto").lower()
        if self.digit_model not in ["auto", "digital", "digital100"]:
            raise ValueError(f"Unsupported model: {self.digit_model}")

        self.digit_do_image_logging = config.has_option("Digits", "LogImageLocation")
        self.digit_image_log_dir = config.get("Digits", "LogImageLocation", fallback="")

        if self.digital_readout_enabled:
            digits = config.get("Digits", "names")
            for name in [x.strip() for x in digits.split(",")]:
                x1 = int(config[f"Digits.{name}"]["x"])
                y1 = int(config[f"Digits.{name}"]["y"])
                w = int(config[f"Digits.{name}"]["dx"])
                h = int(config[f"Digits.{name}"]["dy"])
                self.cut_digital_digit.append(ImagePosition(name, x1, y1, w, h))

        ##################  AnalogReadOut Parameters ########################

        self.analog_readout_enabled = config.getboolean(
            "AnalogReadOut", "Enabled", fallback=False
        )
        if self.digit_model not in ["auto", "analog", "analog100"]:
            raise ValueError(f"Unsupported model: {self.digit_model}")

        self.analog_model_file = config.get("Analog", "Modelfile", fallback="")
        self.analog_model = config.get("Digits", "Model", fallback="auto").lower()
        if self.digit_model not in ["auto", "analog", "analog100"]:
            raise ValueError(f"Unsupported model: {self.digit_model}")
        self.analog_do_image_logging = config.has_option("Analog", "LogImageLocation")
        self.analog_image_log_dir = config.get(
            "Analog", "LogImageLocation", fallback=""
        )

        if self.analog_readout_enabled:
            analogs = config.get("Analog", "names")
            for name in [x.strip() for x in analogs.split(",")]:
                x1 = int(config[f"Analog.{name}"]["x"])
                y1 = int(config[f"Analog.{name}"]["y"])
                w = int(config[f"Analog.{name}"]["dx"])
                h = int(config[f"Analog.{name}"]["dy"])
                self.cut_analog_counter.append(ImagePosition(name, x1, y1, w, h))

        ################## Alignment Parameters ###############################
        self.alignment_rotate_angle = config.getfloat(
            "Alignment", "InitialRotationAngle", fallback=0.0
        )

        refs = config.get("Alignment", "Refs", fallback="")
        for name in [x.strip() for x in refs.split(",")]:
            image = config.get(f"Alignment.{name}", "image", fallback="")
            x = config.getint(f"Alignment.{name}", "x", fallback=0)
            y = config.getint(f"Alignment.{name}", "y", fallback=0)
            self.alignment_ref_images.append(RefImages(name, image, x, y))

        ################## Meter Parameters ###############################
        meterVals = config.get("Meters", "Names", fallback="")
        for name in [x.strip() for x in meterVals.split(",")]:
            format = config.get(f"Meter.{name}", "Value", fallback="")
            consistency_enabled = config.getboolean(
                f"Meter.{name}", "ConsistencyEnabled", fallback=False
            )
            allow_negative_rates = config.getboolean(
                f"Meter.{name}", "AllowNegativeRates", fallback=False
            )
            max_rate_value = config.getfloat(
                f"Meter.{name}", "MaxRateValue", fallback=0.0
            )
            use_previuos_value = config.getboolean(
                f"Meter.{name}", "UsePreviuosValueFilling", fallback=False
            )
            pre_value_from_file_max_age = config.getint(
                f"Meter.{name}", "PreValueFromFileMaxAge", fallback=0
            )
            use_extended_resolution = config.getboolean(
                f"Meter.{name}", "UseExtendedResolution", fallback=False
            )
            unit = config.get(f"Meter.{name}", "Unit", fallback=None)

            self.meter_configs.append(
                MeterConfig(
                    name,
                    format,
                    consistency_enabled,
                    allow_negative_rates,
                    max_rate_value,
                    use_previuos_value,
                    pre_value_from_file_max_age,
                    use_extended_resolution,
                    unit,
                )
            )
