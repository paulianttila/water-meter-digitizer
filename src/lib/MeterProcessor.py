import base64
from dataclasses import dataclass
import re
from typing import List, Union
from lib.Utils.FileUtils import save_file
from lib.PreviousValueFile import (
    load_previous_value_from_file,
    save_previous_value_to_file,
)
from lib.Utils.MathUtils import (
    fill_value_with_ending_zeros,
    fill_with_predecessor_digits,
)
from lib.CNN.CNNBase import ModelDetails, ReadoutResult
from lib.Utils.ImageProcessor import CutResult, ImageProcessor
from lib.CNN.DigitalCounterCNN import DigitalCounterCNN
from lib.CNN.AnalogNeedleCNN import AnalogNeedleCNN
from lib.Utils.ImageLoader import load_image_from_url
from lib.Config import Config, MeterConfig
import math
import time
import logging

logger = logging.getLogger(__name__)


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


class MeterProcessor:
    def __init__(self, config: Config):
        logger.debug("Start Init Meter Reader")
        self.config = config
        self._init_analog()
        self._init_digital()
        self.image_processor = ImageProcessor(
            self.config, image_tmp_dir=config.image_tmp_dir
        )

    def get_roi_image(self, url: str = None, timeout: int = 0) -> str:
        """
        Draw the region of interest (ROI) to the image.

        Args:
            url (str, optional): The URL of the image. Defaults to None.
            timeout (int, optional): The timeout value for downloading the image.
            Defaults to 0.

        Returns:
            str: The base64-encoded ROI image.

        Raises:
            Any exceptions that may occur during the image processing.

        """
        data = self._download_image(url, timeout)
        image = self.image_processor.conv_bytes_to_image(data)
        image = self.image_processor.rotate(image)
        image = self.image_processor.align(image)
        logger.debug("Draw ROI")
        image = self.image_processor.draw_roi(image)
        image = self.image_processor.convert_bgr_to_rgb(image)
        b = self.image_processor.conv_rgb_image_to_bytes(image)
        return base64.b64encode(b).decode()

    def get_meters(
        self,
        url: str = None,
        timeout: int = 0,
        save_images: bool = False,
    ) -> MeterResult:
        """
        Retrieves the meter values from the given URL.

        Args:
            url (str, optional): The URL of the image containing the meter.
            Defaults to None.
            timeout (int, optional): The timeout value for downloading the image.
            Defaults to 0.
            save_images (bool, optional): Whether to save intermediate images.
            Defaults to False.

        Returns:
            MeterResult: The result object containing the meter values.

        """
        data = self._download_image(url, timeout, store_intermediate_files=save_images)
        starttime = time.time()
        cut_images = self._cut_images(data, store_intermediate_files=save_images)
        self._doCCN(cut_images)
        available_values = self._evaluate_ccn_results()
        meters = self._get_meter_values(available_values)
        self._postprocess_meter_values(
            meters=meters,
            values=available_values,
            cnn_results=(self.cnn_digital_results + self.cnn_analog_results),
        )
        result = self._gen_result(meters)

        logger.debug(
            f"Procesing time {time.time() - starttime:.3f} sec, result: {result}"
        )
        return result

    def _get_meter_values(self, available_values: dict):
        meters = []
        for meter_config in self.config.meter_configs:
            value = meter_config.format.format(**available_values)
            meter = Meter(
                name=meter_config.name,
                value=value,
                raw_value=value,
                config=meter_config,
            )
            meters.append(meter)
        logger.info(f" Meters: {meters}")
        return meters

    def _evaluate_ccn_results(self) -> dict[str, int]:
        available_values = {}
        model = self._solve_model(
            self.config.analog_model, self.analog_counter_reader.getModelDetails()
        )
        for item in self.cnn_analog_results:
            val = self._evaluate_analog_counter(
                name=item.name, new_value=item.value, model=model
            )
            available_values[item.name] = val

        model = self._solve_model(
            self.config.digit_model, self.digital_counter_reader.getModelDetails()
        )
        for item in self.cnn_digital_results:
            val = self._evaluate_digital_counter(
                name=item.name, new_value=item.value, model=model
            )
            available_values[item.name] = val
        logger.debug(f"Available values: {available_values}")
        return available_values

    def _gen_result(self, meters: List[Meter]) -> MeterResult:
        analog_results = {}
        if self.config.analog_readout_enabled:
            for item in self.cnn_analog_results:
                val = "{:.2f}".format(item.value)
                analog_results[item.name] = val
        digital_results = {}
        for item in self.cnn_digital_results:
            val = "N" if item.value == "NaN" else str(int(item.value))
            digital_results[item.name] = val

        meter_results = [
            MeterValue(name=meter.name, value=meter.value) for meter in meters
        ]
        return MeterResult(
            meters=meter_results,
            digital_results=digital_results,
            analog_results=analog_results,
            error="",
        )

    def _download_image(
        self, url: str, timeout: int, store_intermediate_files: bool = False
    ) -> bytes:
        url = url if url is not None else self.config.http_image_url
        logger.debug(f"Load image from {url}")
        data = load_image_from_url(
            url=url,
            timeout=timeout if timeout != 0 else self.config.http_load_image_timeout,
            min_image_size=self.config.http_image_min_size,
        )
        if self.image_processor.verify_image(data) is not True:
            raise ValueError("Downloaded image file is corrupted")

        if store_intermediate_files:
            save_file(f"{self.config.image_tmp_dir}/original.jpg", data)
        return data

    def _cut_images(
        self, data: bytes, store_intermediate_files: bool = False
    ) -> CutResult:
        image = self.image_processor.conv_bytes_to_image(data)
        image = self.image_processor.rotate(image, store_intermediate_files)
        image = self.image_processor.align(image, store_intermediate_files)
        cut_images = self.image_processor.cut(image, store_intermediate_files)
        if store_intermediate_files:
            self.image_processor.draw_roi(image, store_to_file=True)
        return cut_images

    def _doCCN(self, images: CutResult) -> None:
        self.cnn_analog_results = []
        self.cnn_digital_results = []
        if self.config.analog_readout_enabled:
            self.cnn_analog_results = self.analog_counter_reader.readout(
                images.analog_images
            )
            logger.debug(f"Analog CNN results: {self.cnn_analog_results}")
        if self.config.digital_readout_enabled:
            self.cnn_digital_results = self.digital_counter_reader.readout(
                images.digital_images
            )
            logger.debug(f"Digital CNN results: {self.cnn_digital_results}")

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

        if meter.config.use_previuos_value:
            meter.previous_value = load_previous_value_from_file(
                self.config.prevoius_value_file,
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
                self.config.prevoius_value_file, meter.name, meter.value
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
            delta = float(currentValue) - float(self.previous_value)
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

    def _init_analog(self) -> None:
        if self.config.analog_readout_enabled:
            self.analog_counter_reader = AnalogNeedleCNN(
                modelfile=self.config.analog_model_file,
                dx=32,
                dy=32,
                image_log_dir=self.config.analog_image_log_dir,
            )
            logger.debug("Analog model init done")
        else:
            logger.debug("Analog model disabled")

    def _init_digital(self) -> None:
        if self.config.digital_readout_enabled:
            self.digital_counter_reader = DigitalCounterCNN(
                modelfile=self.config.digit_model_file,
                dx=20,
                dy=32,
                image_log_dir=self.config.digit_image_log_dir,
            )
            logger.debug("Digital model init done")
        else:
            logger.debug("Digital model disabled")
