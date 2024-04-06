from dataclasses import dataclass, field
from typing import List
import configparser
import os
import logging

from DataClasses import ImagePosition, MeterConfig, RefImage

logger = logging.getLogger(__name__)


class ConfigurationMissing(Exception):
    pass


@dataclass
class ImageSource:
    url: str = ""
    timeout: int = 30
    min_size: int = 10000
    log_dir: str = "/log"
    log_only_false_pictures: bool = True


@dataclass
class CNNParams:
    enabled: bool = False
    model_file: str = ""
    model: str = ""
    do_image_logging: bool = False
    image_log_dir: str = ""
    cut_images: List[ImagePosition] = field(default_factory=list)


@dataclass
class Alignment:
    rotate_angle: float = 0.0
    ref_images: List[RefImage] = field(default_factory=list)


@dataclass
class Crop:
    enabled: bool = False
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


@dataclass
class Resize:
    enabled: bool = False
    w: int = 0
    h: int = 0


@dataclass
class ImageProcessing:
    enabled: bool = False
    contrast: float = 0.0
    brightness: Resize = 0


@dataclass
class Config:
    log_level: str = "INFO"
    image_tmp_dir: str = "/image_tmp"
    config_dir: str = "/config"
    prevoius_value_file: str = "/config/prevalue.ini"
    image_source: ImageSource = field(default_factory=ImageSource)
    digital_readout: CNNParams = field(default_factory=CNNParams)
    analog_readout: CNNParams = field(default_factory=CNNParams)
    alignment: Alignment = field(default_factory=Alignment)
    meter_configs: List[MeterConfig] = field(default_factory=list)
    crop: Crop = field(default_factory=Crop)
    resize: Resize = field(default_factory=Resize)
    image_processing: ImageProcessing = field(default_factory=ImageProcessing)

    def set_log_level(self, level: str) -> "Config":
        self.log_level = level

    def set_image_tmp_dir(self, dir: str) -> "Config":
        self.image_tmp_dir = dir

    def set_config_dir(self, dir: str) -> "Config":
        self.config_dir = dir

    def set_previous_value_file(self, file: str) -> "Config":
        self.prevoius_value_file = file

    def set_image_source(self, imageSource: ImageSource) -> "Config":
        self.imageSource = imageSource

    def set_digital_readout(self, digitalReadout: CNNParams) -> "Config":
        self.digital_readout = digitalReadout

    def set_analog_readout(self, analogReadout: CNNParams) -> "Config":
        self.analog_readout = analogReadout

    def set_alignment(self, alignment: Alignment) -> "Config":
        self.alignment = alignment

    def set_crop(self, crop: Crop) -> "Config":
        self.crop = crop

    def set_resize(self, resize: Resize) -> "Config":
        self.resize = resize

    def set_image_processing(self, imageProcessing: ImageProcessing) -> "Config":
        self.image_processing = imageProcessing

    def add_meter_config(self, config: MeterConfig) -> "Config":
        self.meter_configs.append(config)

    def load_from_file(self, ini_file: str = "config.ini") -> "Config":
        # sourcery skip: avoid-builtin-shadow
        if not os.path.exists(ini_file):
            raise ConfigurationMissing(f"Configuration file '{ini_file}' not found")

        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(), allow_no_value=True
        )
        config.read(ini_file)

        ################## General Parameters ##########################################
        self.log_level = config.get("DEFAULT", "LogLevel", fallback="INFO")
        self.image_tmp_dir = config.get("DEFAULT", "ImageTmpDir", fallback="/image_tmp")
        self.config_dir = config.get("DEFAULT", "ConfigDir", fallback="/config")
        self.prevoius_value_file = config.get(
            "DEFAULT", "PreviousValueFile", fallback="/config/prevalue.ini"
        )

        ##################  Image Source Parameters ####################################
        url = config.get("ImageSource", "URLImageSource", fallback="")
        timeout = config.getint("ImageSource", "TimeoutLoadImage", fallback=30)
        min_size = config.getint("ImageSource", "MinImageSize", fallback=10000)
        log_dir = config.get("ImageSource", "LogImageLocation", fallback="")
        log_only_false_pictures = config.getboolean(
            "ImageSource", "LogOnlyFalsePictures", fallback=False
        )
        self.image_source = ImageSource(
            url=url,
            timeout=timeout,
            min_size=min_size,
            log_dir=log_dir,
            log_only_false_pictures=log_only_false_pictures,
        )
        ##################  DigitalReadOut Parameters ##################################

        digital_readout = self._load_cnn_parames("Digits", config)
        self.digital_readout = digital_readout

        ##################  AnalogReadOut Parameters ###################################

        analog_readout = self._load_cnn_parames("Analog", config)
        self.analog_readout = analog_readout

        ################## Alignment Parameters ########################################
        rotate_angle = config.getfloat("Alignment", "RotationAngle", fallback=0.0)

        refs = config.get("Alignment", "Refs", fallback="")
        ref_images = []
        for name in [x.strip() for x in refs.split(",")]:
            image = config.get(f"Alignment.{name}", "image", fallback="")
            x = config.getint(f"Alignment.{name}", "x", fallback=0)
            y = config.getint(f"Alignment.{name}", "y", fallback=0)
            w = config.getint(f"Alignment.{name}", "w", fallback=0)
            h = config.getint(f"Alignment.{name}", "h", fallback=0)
            ref_images.append(RefImage(name=name, x=x, y=y, w=w, h=h, file_name=image))
        self.alignment = Alignment(rotate_angle=rotate_angle, ref_images=ref_images)

        ################## Crop Parameters #############################################
        crop_enabled = config.getboolean("Crop", "Enabled", fallback=False)
        crop_x = config.getint("Crop", "x", fallback=0)
        crop_y = config.getint("Crop", "y", fallback=0)
        crop_w = config.getint("Crop", "w", fallback=0)
        crop_h = config.getint("Crop", "h", fallback=0)
        self.crop = Crop(enabled=crop_enabled, x=crop_x, y=crop_y, w=crop_w, h=crop_h)

        ################## Resize Parameters #############################################
        resize_enabled = config.getboolean("Resize", "Enabled", fallback=False)
        resize_w = config.getint("Resize", "w", fallback=0)
        resize_h = config.getint("Resize", "h", fallback=0)
        self.resize = Resize(enabled=resize_enabled, w=resize_w, h=resize_h)

        ################## Image Processing Parameters #################################
        image_processing_enabled = config.getboolean(
            "ImageProcessing", "Enabled", fallback=False
        )
        image_processing_contrast = config.getfloat(
            "ImageProcessing", "Contrast", fallback=0.0
        )
        image_processing_brightness = config.getint(
            "ImageProcessing", "Brightness", fallback=0
        )
        self.image_processing = ImageProcessing(
            enabled=image_processing_enabled,
            contrast=image_processing_contrast,
            brightness=image_processing_brightness,
        )

        ################## Meter Parameters ############################################
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
                    name=name,
                    format=format,
                    consistency_enabled=consistency_enabled,
                    allow_negative_rates=allow_negative_rates,
                    max_rate_value=max_rate_value,
                    use_previuos_value=use_previuos_value,
                    pre_value_from_file_max_age=pre_value_from_file_max_age,
                    use_extended_resolution=use_extended_resolution,
                    unit=unit,
                )
            )
        return self

    def _load_cnn_parames(
        self, section: str, config: configparser.ConfigParser
    ) -> CNNParams:
        readout_enabled = config.getboolean(section, "Enabled", fallback=False)
        model_file = config.get(section, "Modelfile", fallback="")
        model = config.get(section, "Model", fallback="auto").lower()
        do_image_logging = config.has_option(section, "LogImageLocation")
        image_log_dir = config.get(section, "LogImageLocation", fallback="")
        images = []
        if readout_enabled:
            names = config.get(section, "names", fallback="")
            if names == "":
                raise ConfigurationMissing(
                    f"Section {section} is missing names. "
                    f"Please add a comma separated list of names or disable "
                    f"the {section} readout."
                )
            for name in [x.strip() for x in names.split(",")]:
                x = config.getint(f"{section}.{name}", "x", fallback=0)
                y = config.getint(f"{section}.{name}", "y", fallback=0)
                w = config.getint(f"{section}.{name}", "w", fallback=0)
                h = config.getint(f"{section}.{name}", "h", fallback=0)
                images.append(ImagePosition(name=name, x=x, y=y, w=w, h=h))
        return CNNParams(
            enabled=readout_enabled,
            model_file=model_file,
            model=model,
            do_image_logging=do_image_logging,
            image_log_dir=image_log_dir,
            cut_images=images,
        )
