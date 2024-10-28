from dataclasses import dataclass
from typing import List, Union
import re
import math
import logging


from previous_value import (
    load_previous_value_from_file,
    save_previous_value_to_file,
)
from utils.math import (
    fill_value_with_ending_zeros,
    fill_with_predecessor_digits,
)
from cnn.base import ModelDetails
from cnn.digital_counter_cnn import DigitalCounterCNN
from cnn.analog_needle_cnn import AnalogNeedleCNN
from data_classes import MeterConfig, CutImage
from decorators.decorators import log_execution_time


logger = logging.getLogger(__name__)


@dataclass
class ReadoutResult:
    name: str
    value: float


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
    unit: str = ""


@dataclass
class MeterResult:
    meters: List[MeterValue]
    digital_results: dict
    analog_results: dict
    error: str


@dataclass
class Meter:
    config: MeterConfig
    name: str = ""
    value: str = ""
    raw_value: str = ""
    previous_value: str = ""


class ConcistencyError(Exception):
    ...
    pass


class DigitizerProcessor:
    def __init__(self) -> None:
        self.condition = None
        self.analog_counter_reader: AnalogNeedleCNN = None  # type: ignore
        self.digital_counter_reader: DigitalCounterCNN = None  # type: ignore
        self.analog_model: str = ""
        self.digital_model: str = ""
        self.previous_value_file: str = ""
        self.cnn_digital_results: list[ReadoutResult] = []
        self.cnn_analog_results: list[ReadoutResult] = []

    @log_execution_time
    def init_analog_model(
        self, modelfile: str, model_name: str
    ) -> "DigitizerProcessor":
        self.analog_model = model_name
        self.analog_counter_reader = AnalogNeedleCNN(modelfile=modelfile, dx=32, dy=32)
        return self

    def set_analog_model(
        self, model: AnalogNeedleCNN, model_name: str
    ) -> "DigitizerProcessor":
        self.analog_model = model_name
        self.analog_counter_reader = model
        return self

    @log_execution_time
    def init_digital_model(
        self, modelfile: str, model_name: str
    ) -> "DigitizerProcessor":
        self.digital_model = model_name
        self.digital_counter_reader = DigitalCounterCNN(
            modelfile=modelfile, dx=20, dy=32
        )
        return self

    def set_digital_model(
        self, model: DigitalCounterCNN, model_name: str
    ) -> "DigitizerProcessor":
        self.digital_model = model_name
        self.digital_counter_reader = model
        return self

    def use_previous_value_file(self, previous_value_file: str) -> "DigitizerProcessor":
        self.previous_value_file = previous_value_file
        return self

    @log_execution_time
    def execute_analog_ccn(self, images: List[CutImage]) -> "DigitizerProcessor":
        if self.analog_counter_reader is None and self.digital_counter_reader is None:
            raise ValueError("No CNN reader initialized")
        if self.analog_counter_reader is not None:
            result = []
            for item in images:
                value = self.analog_counter_reader.readout(item.image)
                result.append(ReadoutResult(item.name, value))
            self.cnn_analog_results = result
            logger.debug(f"Analog CNN results: {self.cnn_analog_results}")
        return self

    @log_execution_time
    def execute_digital_ccn(self, images: List[CutImage]) -> "DigitizerProcessor":
        if self.digital_counter_reader is not None:
            result = []
            for item in images:
                value = self.digital_counter_reader.readout(item.image)
                result.append(ReadoutResult(item.name, value))
            self.cnn_digital_results = result
            logger.debug(f"Digital CNN results: {self.cnn_digital_results}")
        return self

    def evaluate_ccn_results(self) -> "DigitizerProcessor":
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

    def get_meter_values(self, meter_configs: list[MeterConfig]) -> MeterResult:
        meters = self._get_meter_values(meter_configs)
        self._postprocess_meter_values(
            meters=meters,
            values=self.available_values,
            cnn_results=(self.cnn_digital_results + self.cnn_analog_results),
        )
        return self._gen_result(meters)

    def _get_meter_values(self, meter_configs: List[MeterConfig]) -> List[Meter]:
        meters: list[Meter] = []
        for meter_config in meter_configs:
            value = meter_config.format.format(**self.available_values)
            meter = Meter(
                name=meter_config.name,
                value=value,
                raw_value=value,
                config=meter_config,
            )
            meters.append(meter)
        logger.debug(f" Meters: {meters}")
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
                unit=meter.config.unit,
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
        self, name: str, new_value, prev_value: int = -1, model: str = ""
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
        model: str = "",
    ) -> int:
        digit = 0
        if model.lower() == "digital100":
            digit = (
                "N" if new_value < 0 or new_value >= 100 else int(round(new_value / 10))
            )
        elif model.lower() == "digital":
            digit = "N" if new_value < 0 or new_value >= 10 else new_value
        logger.debug(f"{name}: {new_value}  -> {digit}")
        return int(digit)

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
        return ""
