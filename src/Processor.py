from dataclasses import dataclass
from enum import Enum
from typing import List, Union
import base64
import re
import math
import logging

from PIL import Image

from PreviousValueFile import (
    load_previous_value_from_file,
    save_previous_value_to_file,
)
from Utils.MathUtils import (
    fill_value_with_ending_zeros,
    fill_with_predecessor_digits,
)
from CNN.CNNBase import ModelDetails, ReadoutResult
from CNN.DigitalCounterCNN import DigitalCounterCNN
from CNN.AnalogNeedleCNN import AnalogNeedleCNN
from Config import ImagePosition, MeterConfig
from Utils import ImageUtils
from Utils import DownloadUtils
from DataClasses import CutImage

logger = logging.getLogger(__name__)


class CNNType(Enum):
    ANALOG = 1
    DIGITAL = 2


@dataclass
class ValueResult:
    value: str
    raw_value: str
    previous_value: str
    digital_results: dict
    analog_results: dict
    error: str


@dataclass
class MeterValue:
    name: str
    value: str
    unit: str = None


@dataclass
class MeterResult:
    meters: List[MeterValue]
    digital_results: dict
    analog_results: dict
    error: str


@dataclass
class Meter:
    name: str = None
    value: str = None
    raw_value: str = None
    previous_value: str = None
    config: MeterConfig = None


class ConcistencyError(Exception):
    ...
    pass


class ValueError(Exception):
    ...
    pass


class Processor:
    def __init__(self):
        self.image = None
        self.cutted_analog_images = [CutImage]
        self.cutted_digital_images = [CutImage]
        self.analog_counter_reader = None
        self.digital_counter_reader = None
        self.analog_model = None
        self.digital_model = None
        self.previous_value_file = None
        self.cnn_digital_results = []
        self.cnn_analog_results = []
        self.enable_img_saving = False

    def init_analog_model(
        self, modelfile: str, model: str, image_log_dir: str = None
    ) -> "Processor":
        self.analog_model = model
        self.analog_counter_reader = AnalogNeedleCNN(
            modelfile=modelfile, dx=32, dy=32, image_log_dir=image_log_dir
        )
        return self

    def enable_image_saving(self, state: bool = True) -> "Processor":
        self.enable_img_saving = state
        return self

    def use_previous_value_file(self, previous_value_file: str) -> "Processor":
        self.previous_value_file = previous_value_file
        return self

    def init_digital_model(
        self, modelfile: str, model: str, image_log_dir: str = None
    ) -> "Processor":
        self.digital_model = model
        self.digital_counter_reader = DigitalCounterCNN(
            modelfile=modelfile, dx=20, dy=32, image_log_dir=image_log_dir
        )
        return self

    def set_image(self, image: Image) -> "Processor":
        self.image = image
        return self

    def get_image(self) -> Image:
        return self.image

    def get_image_as_base64_str(self) -> str:
        image = ImageUtils.convert_bgr_to_rgb(image=self.image)
        b = ImageUtils.conv_rgb_image_to_bytes(image=image)
        return base64.b64encode(b).decode()

    def save_image(self, path: str) -> "Processor":
        if self.enable_img_saving:
            ImageUtils.save_image(self.image, path)
        return self

    def download_image(
        self, url: str, timeout: int, min_image_size: int = 0
    ) -> "Processor":
        logger.debug(f"Download image from {url}")
        data = DownloadUtils.load_file_from_url(
            url=url,
            timeout=timeout,
            min_file_size=min_image_size,
        )
        self.image = ImageUtils.bytes_to_image(data)
        return self

    def rotate_image(self, angle: float) -> "Processor":
        logger.debug(f"Rotate image by {angle} degrees")
        self.image = ImageUtils.rotate(self.image, angle)
        return self

    def crop_image(self, x: int, y: int, w: int, h: int) -> "Processor":
        self.image = ImageUtils.crop_image(self.image, x, y, w, h)
        return self

    def resize_image(self, width: int, height: int) -> "Processor":
        self.image = ImageUtils.resize_image(self.image, width, height)
        return self

    def adjust_contrast(self, contrast: int) -> "Processor":
        self.image = ImageUtils.adjust_contrast_brightness(
            image=self.image, contrast=contrast
        )
        return self

    def adjust_brightness(self, brightness: int) -> "Processor":
        self.image = ImageUtils.adjust_contrast_brightness(
            image=self.image, brightness=brightness
        )
        return self

    def to_gray_scale(self) -> "Processor":
        self.image = ImageUtils.convert_to_gray_scale(self.image)
        return self

    def align_image(self, align_images: List[ImagePosition]) -> "Processor":
        self.image = ImageUtils.align(self.image, align_images)
        return self

    def draw_roi(
        self, images: List[ImagePosition], bgr_colour: tuple[int, int, int]
    ) -> "Processor":
        for img in images:
            self.image = ImageUtils.draw_rectangle(
                self.image,
                img.x,
                img.y,
                img.w,
                img.h,
                colour=bgr_colour,
                thickness=3,
            )
            self.image = ImageUtils.draw_text(
                self.image,
                img.name,
                img.x,
                img.y - 8,
                colour=bgr_colour,
            )
        return self

    def cut_images(self, positions: List[ImagePosition], type: CNNType) -> "Processor":
        for img in positions:
            image = ImageUtils.cut_image(self.image, img)
            if type == CNNType.ANALOG:
                self.cutted_analog_images.append(CutImage(name=img.name, image=image))
            else:
                self.cutted_digital_images.append(CutImage(name=img.name, image=image))
        return self

    def start_image_cutting(self) -> "Processor":
        self.cutted_analog_images = []
        self.cutted_digital_images = []
        return self

    def stop_image_cutting(self) -> "Processor":
        return self

    def save_cutted_images(self, path: str) -> "Processor":
        for img in self.cutted_analog_images + self.cutted_digital_images:
            ImageUtils.save_image(img.image, f"{path}/{img.name}.jpg")
        return self

    def execute_analog_ccn(self) -> "Processor":
        if self.analog_counter_reader is None and self.digital_counter_reader is None:
            raise ValueError("No CNN reader initialized")
        if self.analog_counter_reader is not None:
            self.cnn_analog_results = self.analog_counter_reader.readout(
                self.cutted_digital_images
            )
            logger.debug(f"Analog CNN results: {self.cnn_analog_results}")
        return self

    def execute_digital_ccn(self) -> "Processor":
        if self.digital_counter_reader is not None:
            self.cnn_digital_results = self.digital_counter_reader.readout(
                self.cutted_analog_images
            )
            logger.debug(f"Digital CNN results: {self.cnn_digital_results}")
        return self

    def evaluate_ccn_results(self) -> "Processor":
        available_values = {}

        if self.analog_counter_reader is not None:
            model = self._solve_model(
                self.analog_model, self.analog_counter_reader.getModelDetails()
            )
            for item in self.cnn_analog_results:
                val = self._evaluate_analog_counter(
                    name=item.name, new_value=item.value, model=model
                )
                available_values[item.name] = val

        if self.digital_counter_reader is not None:
            model = self._solve_model(
                self.digital_model, self.digital_counter_reader.getModelDetails()
            )
            for item in self.cnn_digital_results:
                val = self._evaluate_digital_counter(
                    name=item.name, new_value=item.value, model=model
                )
                available_values[item.name] = val
        logger.debug(f"Available values: {available_values}")
        self.available_values = available_values
        return self

    def get_meter_values(self, meters: MeterConfig) -> ValueResult:
        meters = self._get_meter_values(meters)
        self._postprocess_meter_values(
            meters=meters,
            values=self.available_values,
            cnn_results=(self.cnn_digital_results + self.cnn_analog_results),
        )
        return self._gen_result(meters)

    def _get_meter_values(self, meter_configs: List[MeterConfig]):
        meters = []
        for meter_config in meter_configs:
            value = meter_config.format.format(**self.available_values)
            meter = Meter(
                name=meter_config.name,
                value=value,
                raw_value=value,
                config=meter_config,
            )
            meters.append(meter)
        logger.info(f" Meters: {meters}")
        return meters

    def _gen_result(self, meters: List[Meter]) -> MeterResult:
        analog_results = {}
        if self.analog_counter_reader is not None:
            for item in self.cnn_analog_results:
                val = "{:.2f}".format(item.value)
                analog_results[item.name] = val
        digital_results = {}
        if self.digital_counter_reader is not None:
            for item in self.cnn_digital_results:
                val = "N" if item.value == "NaN" else str(int(item.value))
                digital_results[item.name] = val

        meter_results = [
            MeterValue(
                name=meter.name,
                value=meter.value,
                unit=meter.config.unit if meter.config.unit is not None else "",
            )
            for meter in meters
        ]
        return MeterResult(
            meters=meter_results,
            digital_results=digital_results,
            analog_results=analog_results,
            error="",
        )

    def _postprocess_meter_values(
        self,
        meters: List[Meter],
        values: dict,
        cnn_results: List[ReadoutResult],
    ) -> None:
        # for easier access
        meter_dict = {meter.name: meter for meter in meters}
        cnn_results_dict = {item.name: item for item in cnn_results}

        for meter in meters:
            self._postprocess_meter_value(
                meter_dict[meter.name],
                values,
                cnn_results_dict,
            )

    def _postprocess_meter_value(
        self,
        meter: Meter,
        values: dict,
        cnn_results: dict,
    ) -> None:
        if meter.config.consistency_enabled is False:
            return

        logger.info(f" Postprocess meter, paramters: {meter}")

        if self.previous_value_file is not None:
            meter.previous_value = load_previous_value_from_file(
                self.previous_value_file,
                meter.name,
                meter.config.pre_value_from_file_max_age,
            )

        if meter.config.use_extended_resolution:
            meter.value = self._get_extended_resolution(meter, cnn_results)
        if meter.config.use_previuos_value:
            meter.previous_value = self._adapt_prevalue_to_macth_len(
                meter.value, meter.previous_value
            )
            meter.value = fill_with_predecessor_digits(
                meter.value, meter.previous_value
            )
            self._check_consistency(meter, meter.value, meter.previous_value)
            save_previous_value_to_file(
                self.previous_value_file, meter.name, meter.value
            )

    def _adapt_prevalue_to_macth_len(self, new_value: str, previous_value: str) -> str:
        if len(new_value) > len(previous_value):
            logger.debug(
                f"Fill previous value {previous_value} "
                f"to match new value {new_value} len"
            )
            previous_value = fill_value_with_ending_zeros(
                len(new_value), previous_value
            )
        elif len(new_value) < len(previous_value):
            logger.debug(
                f"Remove digits from previous value {previous_value} to match "
                f"new value {new_value} len"
            )
            previous_value = previous_value[: len(new_value)]
        return previous_value

    def _get_extended_resolution(self, meter: Meter, values: dict) -> str:
        # get last digit of the value
        names = re.findall(r"\{(.*?)\}", meter.config.format)
        last_digit = values[names[-1]]
        result_after_decimal_point = math.floor(float(last_digit.value) * 10 + 10) % 10
        return f"{meter.value}{result_after_decimal_point}"

    def _check_consistency(
        self, meter: Meter, currentValue: str, previous_value: str
    ) -> str:
        if previous_value.isnumeric() and currentValue.isnumeric():
            delta = float(currentValue) - float(previous_value)
            if not (meter.config.allow_negative_rates) and (delta < 0):
                raise ConcistencyError("Negative rate ({delta:.4f})")
            if abs(delta) > meter.config.max_rate_value:
                raise ConcistencyError("Rate too high ({delta:.4f})")
        return currentValue

    def _analog_readout_to_value(self, decimal_parts: list[ReadoutResult]) -> str:
        prev = -1
        strValue = ""
        for item in decimal_parts[::-1]:
            prev = self._evaluate_analog_counter(
                name=item.name, new_value=item.value, prev_value=prev
            )
            strValue = f"{prev}{strValue}"
        return strValue

    def _evaluate_analog_counter(
        self, name: str, new_value, prev_value: int = -1, model: str = None
    ) -> int:
        decimal_part = math.floor((new_value * 10) % 10)
        integer_part = math.floor(new_value % 10)

        if prev_value == -1:
            result = integer_part
        else:
            result_rating = decimal_part - prev_value
            if decimal_part >= 5:
                result_rating -= 5
            else:
                result_rating += 5
            result = round(new_value)
            if result_rating < 0:
                result -= 1
            if result == -1:
                result += 10

        result = result % 10
        logger.debug(f"{name}: {new_value} (prev value: {prev_value}) -> {result}")
        return result

    def _evaluate_digital_counter(
        self,
        name: str,
        new_value: Union[float, int],
        prev_value: int = -1,
        model: str = None,
    ) -> int:
        if model.lower() == "digital100":
            digit = (
                "N" if new_value < 0 or new_value >= 100 else int(round(new_value / 10))
            )
        elif model.lower() == "digital":
            digit = "N" if new_value < 0 or new_value >= 10 else new_value
        logger.debug(f"{name}: {new_value}  -> {digit}")
        return digit

    def _solve_model(self, model: str, details: ModelDetails) -> str:
        if model.lower() != "auto":
            return model
        if details.numer_output == 2:
            return "analog"
        if details.numer_output == 11:
            return "digital"
        if details.numer_output == 100:
            if details.xsize == 32 and details.ysize == 32:
                return "analog100"
            return "digital100"
