from dataclasses import dataclass, field
import datetime
import io
import shutil
from typing import List
import configparser
import os
import logging

from data_classes import ImagePosition, MeterConfig, RefImage

logger = logging.getLogger(__name__)


class ConfigurationMissing(Exception):
    pass


@dataclass
class ImageSource:
    url: str = ""
    timeout: int = 30
    min_size: int = 10000


@dataclass
class CNNParams:
    enabled: bool = False
    model_file: str = ""
    model: str = ""
    cut_images: List[ImagePosition] = field(default_factory=list)


@dataclass
class Alignment:
    rotate_angle: float = 0.0
    ref_images: List[RefImage] = field(default_factory=list)
    post_rotate_angle: float = 0.0


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
    contrast: float = 1.0
    brightness: float = 1.0
    color: float = 1.0
    sharpness: float = 1.0
    grayscale: bool = False


@dataclass
class Config:
    log_level: str = "INFO"
    image_tmp_dir: str = "/image_tmp"
    config_dir: str = "/config"
    prevoius_value_file: str = "/config/prevalue.ini"
    digital_models_dir: str = "/config/neuralnets/digital"
    analog_models_dir: str = "/config/neuralnets/analog"
    image_source: ImageSource = field(default_factory=ImageSource)
    digital_readout: CNNParams = field(default_factory=CNNParams)
    analog_readout: CNNParams = field(default_factory=CNNParams)
    alignment: Alignment = field(default_factory=Alignment)
    meter_configs: List[MeterConfig] = field(default_factory=list)
    crop: Crop = field(default_factory=Crop)
    resize: Resize = field(default_factory=Resize)
    image_processing: ImageProcessing = field(default_factory=ImageProcessing)

    def load_from_string(self, config_string: str) -> "Config":
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=("#", ";"),
        )
        config.read_string(config_string)
        return self.load_config(config)

    def save_to_string(self) -> str:
        output = io.StringIO()
        self._save_to_io(output)
        return output.getvalue()

    def load_from_file(self, ini_file: str = "config.ini") -> "Config":
        # sourcery skip: avoid-builtin-shadow
        if not os.path.exists(ini_file):
            raise ConfigurationMissing(f"Configuration file '{ini_file}' not found")

        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=("#", ";"),
        )
        config.read(ini_file)
        return self.load_config(config)

    def create_backup(self, ini_file: str = "config.ini") -> "Config":
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{ini_file}_{date}.bak"
        shutil.copyfile(ini_file, backup_file)
        return self

    def save_to_file(
        self, ini_file: str = "config.ini", make_backup: bool = False
    ) -> "Config":
        if make_backup:
            self.create_backup(ini_file)
        with open(ini_file, "w") as configfile:
            self._save_to_io(configfile)
        return self

    def _save_to_io(self, fp) -> "Config":
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "LogLevel": self.log_level,
            "ImageTmpDir": self.image_tmp_dir,
            "ConfigDir": self.config_dir,
            "DigitalModelsDir": self.digital_models_dir,
            "AnalogModelsDir": self.analog_models_dir,
            "PreviousValueFile": self.prevoius_value_file,
        }

        config["ImageSource"] = {
            "URL": self.image_source.url,
            "Timeout": str(self.image_source.timeout),
            "MinSize": str(self.image_source.min_size),
        }

        config["Crop"] = {
            "Enabled": str(self.crop.enabled),
            "x": str(self.crop.x),
            "y": str(self.crop.y),
            "w": str(self.crop.w),
            "h": str(self.crop.h),
        }

        config["Resize"] = {
            "Enabled": str(self.resize.enabled),
            "w": str(self.resize.w),
            "h": str(self.resize.h),
        }

        config["ImageProcessing"] = {
            "Enabled": str(self.image_processing.enabled),
            "Contrast": str(self.image_processing.contrast),
            "Brightness": str(self.image_processing.brightness),
            "Color": str(self.image_processing.color),
            "Sharpness": str(self.image_processing.sharpness),
            "GrayScale": str(self.image_processing.grayscale),
        }

        config["Alignment"] = {
            "RotationAngle": str(self.alignment.rotate_angle),
            "Refs": ", ".join([ref.name for ref in self.alignment.ref_images]),
            "PostRotationAngle": str(self.alignment.post_rotate_angle),
        }

        for ref in self.alignment.ref_images:
            config[f"Alignment.{ref.name}"] = {
                "image": ref.file_name,
                "x": str(ref.x),
                "y": str(ref.y),
                "w": str(ref.w),
                "h": str(ref.h),
            }

        config["Meters"] = {
            "Names": ", ".join([meter.name for meter in self.meter_configs]),
        }

        for meter in self.meter_configs:
            config[f"Meter.{meter.name}"] = {
                "Value": meter.format,
                "ConsistencyEnabled": str(meter.consistency_enabled),
                "AllowNegativeRates": str(meter.allow_negative_rates),
                "MaxRateValue": str(meter.max_rate_value),
                "UsePreviuosValueFilling": str(meter.use_previuos_value),
                "PreValueFromFileMaxAge": str(meter.pre_value_from_file_max_age),
                "UseExtendedResolution": str(meter.use_extended_resolution),
                "Unit": meter.unit if meter.unit is not None else "",
            }

        config["Digits"] = {
            "Enabled": str(self.digital_readout.enabled),
            "ModelFile": self.digital_readout.model_file,
            "Model": self.digital_readout.model,
            "Names": ", ".join(
                [image.name for image in self.digital_readout.cut_images]
            ),
        }

        config["Analog"] = {
            "Enabled": str(self.analog_readout.enabled),
            "ModelFile": self.analog_readout.model_file,
            "Model": self.analog_readout.model,
            "Names": ", ".join(
                [image.name for image in self.analog_readout.cut_images]
            ),
        }

        for analog in self.analog_readout.cut_images:
            config[f"Analog.{analog.name}"] = {
                "x": str(analog.x),
                "y": str(analog.y),
                "w": str(analog.w),
                "h": str(analog.h),
            }

        for digital in self.digital_readout.cut_images:
            config[f"Digits.{digital.name}"] = {
                "x": str(digital.x),
                "y": str(digital.y),
                "w": str(digital.w),
                "h": str(digital.h),
            }

        config.write(fp, space_around_delimiters=False)

    def load_config(self, config: configparser.ConfigParser) -> "Config":

        ################## General Parameters ##########################################
        self.log_level = config.get("DEFAULT", "LogLevel", fallback="INFO")
        self.image_tmp_dir = config.get("DEFAULT", "ImageTmpDir", fallback="/image_tmp")
        self.config_dir = config.get("DEFAULT", "ConfigDir", fallback="/config")
        self.digital_models_dir = config.get(
            "DEFAULT", "DigitalModelsDir", fallback="/config/neuralnets/digital"
        )
        self.analog_models_dir = config.get(
            "DEFAULT", "AnalogModelsDir", fallback="/config/neuralnets/analog"
        )
        self.prevoius_value_file = config.get(
            "DEFAULT", "PreviousValueFile", fallback="/config/prevalue.ini"
        )

        ##################  Image Source Parameters ####################################
        url = config.get("ImageSource", "URL", fallback="")
        timeout = config.getint("ImageSource", "Timeout", fallback=30)
        min_size = config.getint("ImageSource", "MinSize", fallback=10000)
        self.image_source = ImageSource(
            url=url,
            timeout=timeout,
            min_size=min_size,
        )
        ##################  DigitalReadOut Parameters ##################################

        digital_readout = self._load_cnn_parames("Digits", config)
        self.digital_readout = digital_readout

        ##################  AnalogReadOut Parameters ###################################

        analog_readout = self._load_cnn_parames("Analog", config)
        self.analog_readout = analog_readout

        ################## Alignment Parameters ########################################
        rotate_angle = config.getfloat("Alignment", "RotationAngle", fallback=0.0)
        post_rotate_angle = config.getfloat(
            "Alignment", "PostRotationAngle", fallback=0.0
        )

        refs = config.get("Alignment", "Refs", fallback="")
        ref_images = []
        for name in [x.strip() for x in refs.split(",")]:
            image = config.get(f"Alignment.{name}", "image", fallback="")
            x = config.getint(f"Alignment.{name}", "x", fallback=0)
            y = config.getint(f"Alignment.{name}", "y", fallback=0)
            w = config.getint(f"Alignment.{name}", "w", fallback=0)
            h = config.getint(f"Alignment.{name}", "h", fallback=0)
            ref_images.append(RefImage(name=name, x=x, y=y, w=w, h=h, file_name=image))
        self.alignment = Alignment(
            rotate_angle=rotate_angle,
            ref_images=ref_images,
            post_rotate_angle=post_rotate_angle,
        )

        ################## Crop Parameters #############################################
        crop_enabled = config.getboolean("Crop", "Enabled", fallback=False)
        crop_x = config.getint("Crop", "x", fallback=0)
        crop_y = config.getint("Crop", "y", fallback=0)
        crop_w = config.getint("Crop", "w", fallback=0)
        crop_h = config.getint("Crop", "h", fallback=0)
        self.crop = Crop(enabled=crop_enabled, x=crop_x, y=crop_y, w=crop_w, h=crop_h)

        ################## Resize Parameters ###########################################
        resize_enabled = config.getboolean("Resize", "Enabled", fallback=False)
        resize_w = config.getint("Resize", "w", fallback=0)
        resize_h = config.getint("Resize", "h", fallback=0)
        self.resize = Resize(enabled=resize_enabled, w=resize_w, h=resize_h)

        ################## Image Processing Parameters #################################
        image_processing_enabled = config.getboolean(
            "ImageProcessing", "Enabled", fallback=False
        )
        image_processing_contrast = config.getfloat(
            "ImageProcessing", "Contrast", fallback=1.0
        )
        image_processing_brightness = config.getfloat(
            "ImageProcessing", "Brightness", fallback=1.0
        )
        image_processing_color = config.getfloat(
            "ImageProcessing", "Color", fallback=1.0
        )
        image_processing_sharpness = config.getfloat(
            "ImageProcessing", "Sharpness", fallback=1.0
        )
        image_processing_grayscale = config.getboolean(
            "ImageProcessing", "GrayScale", fallback=False
        )
        self.image_processing = ImageProcessing(
            enabled=image_processing_enabled,
            contrast=image_processing_contrast,
            brightness=image_processing_brightness,
            color=image_processing_color,
            sharpness=image_processing_sharpness,
            grayscale=image_processing_grayscale,
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
            cut_images=images,
        )
