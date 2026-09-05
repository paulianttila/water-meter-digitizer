from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
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

INVALID_DIGIT = "N"
DEFAULT_MIN_CONFIDENCE_THRESHOLD = 60.0
MIN_CONFIDENCE_THRESHOLD = DEFAULT_MIN_CONFIDENCE_THRESHOLD

MODEL_AUTO = "auto"
MODEL_ANALOG = "analog"  # Analogue
MODEL_DIGITAL = "digital"  # Digit
MODEL_ANALOG100 = "analog100"  # Analogue100
MODEL_DIGITAL100 = "digital100"  # Digit100
# DoubleHyprid10

ANALOG_MODELS = {MODEL_ANALOG, MODEL_ANALOG100}
DIGITAL_MODELS = {MODEL_DIGITAL, MODEL_DIGITAL100}


@dataclass
class ReadoutResult:
    name: str
    value: float
    model: str
    confidence: float = 100.0


@dataclass
class MeterValue:
    name: str
    value: str
    unit: str = ""
    quality: str = "good"  # "good", "warning", or "uncertain"
    confidence: float = 100.0


@dataclass
class MeterResult:
    meters: list[MeterValue]
    digital_results: dict
    analog_results: dict
    confidence_scores: dict[str, float] = field(default_factory=dict)
    error: str = ""


@dataclass
class Meter:
    config: MeterConfig
    name: str = ""
    value: str = ""  # value after postprocessing
    unprocessed_value: str = ""  # value without postprocessing
    previous_value: str = ""


class ConsistencyError(Exception):
    pass


class DigitizerProcessor:

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.condition = None
        self.analog_counter_reader: AnalogNeedleCNN = None  # type: ignore
        self.digital_counter_reader: DigitalCounterCNN = None  # type: ignore
        self.analog_model: str = ""
        self.digital_model: str = ""
        self.previous_value_file: str | None = None
        self.min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE_THRESHOLD
        self.cnn_digital_results: list[ReadoutResult] = []
        self.cnn_analog_results: list[ReadoutResult] = []
        self.available_values: dict[str, int | str] = {}

    def set_min_confidence_threshold(self, threshold: float) -> "DigitizerProcessor":
        self.min_confidence_threshold = threshold
        return self

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

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(
        self,
        analog_images: list[CutImage],
        digital_images: list[CutImage],
        meter_configs: list[MeterConfig],
        min_confidence_threshold: float | None = None,
    ) -> MeterResult:
        if min_confidence_threshold is not None:
            self.min_confidence_threshold = min_confidence_threshold
        self.execute_analog_cnn(analog_images)
        self.execute_digital_cnn(digital_images)
        self.evaluate_cnn_results()
        return self.get_meter_values(meter_configs)

    @log_execution_time
    def execute_analog_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        if self.analog_counter_reader is None and self.digital_counter_reader is None:
            raise ValueError("No CNN reader initialized")
        if self.analog_counter_reader is not None:
            result = []
            model = self._solve_model(
                self.analog_model, self.analog_counter_reader.getModelDetails()
            )
            for item in images:
                if hasattr(self.analog_counter_reader, "readout_with_confidence"):
                    value, conf = self.analog_counter_reader.readout_with_confidence(
                        item.image
                    )
                else:
                    value = self.analog_counter_reader.readout(item.image)
                    conf = 100.0
                value = round(value, 1)
                value = 0 if value == 10 else value
                result.append(
                    ReadoutResult(
                        item.name,
                        value,
                        model,
                        confidence=conf,
                    )
                )
            self.cnn_analog_results = result
            logger.debug(f"Analog CNN results: {self.cnn_analog_results}")
        return self

    @log_execution_time
    def execute_digital_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        if self.digital_counter_reader is not None:
            result = []
            model = self._solve_model(
                self.digital_model, self.digital_counter_reader.getModelDetails()
            )
            for item in images:
                if hasattr(self.digital_counter_reader, "readout_with_confidence"):
                    value, conf = self.digital_counter_reader.readout_with_confidence(
                        item.image
                    )
                else:
                    value = self.digital_counter_reader.readout(item.image)
                    conf = 100.0
                result.append(
                    ReadoutResult(
                        item.name,
                        value,
                        model,
                        confidence=conf,
                    )
                )
            self.cnn_digital_results = result
            logger.debug(f"Digital CNN results: {self.cnn_digital_results}")
        return self

    # ------------------------------------------------------------------
    # CNN results evaluation
    # ------------------------------------------------------------------

    def evaluate_cnn_results(self) -> "DigitizerProcessor":
        available_values: dict[str, int | str] = {}

        for result in self.cnn_analog_results + self.cnn_digital_results:
            if result.confidence < self.min_confidence_threshold or math.isnan(
                result.value
            ):
                digit: int | str = INVALID_DIGIT
            else:
                digit = self._evaluate_counter(
                    name=result.name,
                    number=result.value,
                    predecessor_digit=None,
                    model=result.model,
                )
            available_values[result.name] = digit

        self.available_values = available_values
        logger.debug(f"Available values: {available_values}")
        return self

    def _evaluate_counters(self, values: list[ReadoutResult]) -> dict[str, str]:
        predecessor_value: float | None = None
        predecessor_model: str | None = None
        evaluated: dict[str, str] = {}

        for result in reversed(values):
            model = result.model.lower()

            # A change of model means a new independent wheel group.
            if model != predecessor_model:
                predecessor_value = None

            if result.confidence < self.min_confidence_threshold or math.isnan(
                result.value
            ):
                digit: int | str = INVALID_DIGIT
            else:
                digit = self._evaluate_counter(
                    name=result.name,
                    number=result.value,
                    predecessor_digit=None,
                    predecessor_value=predecessor_value,
                    model=model,
                )

            evaluated[result.name] = str(digit)

            predecessor_value = result.value
            predecessor_model = model

        return evaluated

    def _evaluate_counter(
        self,
        name: str,
        number: float,
        predecessor_digit: int | None,
        model: str,
        predecessor_value: float | None = None,
    ) -> int | str:

        model = model.lower()

        if model in ANALOG_MODELS:
            digit = self._evaluate_analog_counter(
                name=name,
                number=number,
                predecessor_digit=predecessor_digit,
                predecessor_value=predecessor_value,
                model=model,
            )
        elif model in DIGITAL_MODELS:
            digit = self._evaluate_digital_counter(
                name=name,
                number=number,
                predecessor_digit=predecessor_digit,
                predecessor_value=predecessor_value,
                model=model,
            )
        else:
            raise ValueError(f"Unknown model: {model}")

        logger.debug(
            f"Evaluate {name}: {number} "
            f"(predecessor: {predecessor_digit}, "
            f"predecessor_value: {predecessor_value}) -> {digit}"
        )

        return digit

    def _evaluate_analog_counter(
        self,
        name: str,
        number: float,
        predecessor_digit: int | None = None,
        predecessor_value: float | None = None,
        model: str = "",
    ) -> int:
        return self._evaluate_wheel_counter(
            number=number,
            predecessor_value=predecessor_value,
        )

    def _evaluate_digital_counter(
        self,
        name: str,
        number: float | int,
        predecessor_digit: int | None = None,
        predecessor_value: float | None = None,
        model: str = "",
    ) -> int | str:

        model = model.lower()

        if model == MODEL_DIGITAL:
            if number < 0 or number >= 10:
                return INVALID_DIGIT
            return int(number)

        if model == MODEL_DIGITAL100:
            if math.isnan(number) or number < 0 or number >= 100:
                return INVALID_DIGIT
            if predecessor_value is None:
                return int(math.floor(number)) % 10

            return int(math.floor(number + 0.5)) % 10

        raise ValueError(f"Unknown digital model: {model}")

    def _evaluate_wheel_counter(
        self,
        number: float,
        predecessor_value: float | None = None,
    ) -> int:
        if predecessor_value is None:
            return int(math.floor(number + 0.5)) % 10

        digit = int(math.floor(number + 0.5)) % 10

        if number % 1 >= 0.5 and predecessor_value % 1 < 0.5:
            return (digit - 1) % 10

        if number % 1 < 0.5 and predecessor_value % 1 >= 0.5:
            return 9

        return digit

    # ------------------------------------------------------------------
    # Meter post-processing
    # ------------------------------------------------------------------

    def get_meter_values(self, meter_configs: list[MeterConfig]) -> MeterResult:
        meters = self._get_meter_values(meter_configs)
        self._postprocess_meter_values(
            meters=meters,
            values=self.available_values,
            cnn_results=(self.cnn_digital_results + self.cnn_analog_results),
        )
        return self._gen_result(meters)

    def _get_meter_values(self, meter_configs: list[MeterConfig]) -> list[Meter]:
        meters: list[Meter] = []
        for meter_config in meter_configs:
            value = meter_config.format.format(**self.available_values)
            meter = Meter(
                name=meter_config.name,
                value=value,
                unprocessed_value=value,
                config=meter_config,
            )
            logger.debug(f" Meter: {meter}")
            meters.append(meter)
        # logger.debug(f" Meters: {meters}")
        return meters

    def _postprocess_meter_values(
        self,
        meters: list[Meter],
        values: dict,
        cnn_results: list[ReadoutResult],
    ) -> None:

        # for easier access
        cnn_results_dict = {item.name: item for item in cnn_results}

        for meter in meters:
            self._postprocess_meter_value(
                meter,
                values,
                cnn_results_dict,
            )

    def _postprocess_meter_value(
        self,
        meter: Meter,
        values: dict,
        cnn_results: dict[str, ReadoutResult],
    ) -> None:

        results = self._get_readout_results(meter, cnn_results)
        logger.info(f" Postprocess meter: {meter}, readout results: {results}")

        values = self._evaluate_counters(results)
        meter.value = meter.config.format.format(**values)

        if meter.config.use_previous_value:
            if self.previous_value_file is None:
                raise ValueError(
                    "Previous value file must be configured "
                    "when use_previous_value is enabled"
                )
            meter.previous_value = load_previous_value_from_file(
                self.previous_value_file,
                meter.name,
                meter.config.pre_value_from_file_max_age,
            )

        if meter.config.use_extended_resolution:
            meter.value = self._append_extended_digit(meter, cnn_results)

        if meter.config.use_previous_value:
            meter.previous_value = self._adapt_previous_value_to_match_length(
                meter.value, meter.previous_value
            )
            meter.value = fill_with_predecessor_digits(
                meter.value, meter.previous_value
            )
            if meter.config.consistency_enabled:
                self._check_consistency(meter, meter.value, meter.previous_value)

            save_previous_value_to_file(
                str(self.previous_value_file), meter.name, meter.value
            )

    def _get_readout_results(
        self,
        meter: Meter,
        cnn_results: dict[str, ReadoutResult],
    ) -> list[ReadoutResult]:
        return [cnn_results[name] for name in meter.config.value_names]

    def _adapt_previous_value_to_match_length(
        self, number: str, previous_value: str
    ) -> str:
        if len(number) > len(previous_value):
            logger.debug(
                f"Fill previous value {previous_value} "
                f"to match new value {number} len"
            )
            previous_value = fill_value_with_ending_zeros(len(number), previous_value)
        elif len(number) < len(previous_value):
            logger.debug(
                f"Remove digits from previous value {previous_value} to match "
                f"new value {number} len"
            )
            previous_value = previous_value[: len(number)]
        return previous_value

    def _append_extended_digit(
        self,
        meter: Meter,
        cnn_results: dict[str, ReadoutResult],
    ) -> str:

        last_digit = cnn_results[meter.config.value_names[-1]]
        if math.isnan(last_digit.value):
            return meter.value  # can't extend with invalid data
        decimal_digit = math.floor(last_digit.value * 10) % 10
        return f"{meter.value}{decimal_digit}"

    def _check_consistency(
        self, meter: Meter, currentValue: str, previousValue: str
    ) -> None:

        try:
            current = Decimal(currentValue)
            previous = Decimal(previousValue)
        except InvalidOperation:
            raise ConsistencyError(f"Invalid value: {currentValue} or {previousValue}")

        delta = current - previous
        # delta = float(currentValue) - float(previous_value)
        if not (meter.config.allow_negative_rates) and (delta < 0):
            raise ConsistencyError(f"Negative rate ({delta:.3f})")
        if abs(delta) > meter.config.max_rate_value:
            raise ConsistencyError(f"Rate too high ({delta:.3f})")

    # ------------------------------------------------------------------
    # Result generation
    # ------------------------------------------------------------------

    def _gen_result(self, meters: list[Meter]) -> MeterResult:
        analog_results = {}
        confidence_scores = {}
        if self.analog_counter_reader is not None:
            for item in self.cnn_analog_results:
                val = f"{item.value:.2f}"
                analog_results[item.name] = val
                confidence_scores[item.name] = item.confidence
        digital_results = {}
        if self.digital_counter_reader is not None:
            for item in self.cnn_digital_results:
                val = INVALID_DIGIT if math.isnan(item.value) else str(item.value)
                digital_results[item.name] = val
                confidence_scores[item.name] = item.confidence

        all_results_dict = {
            item.name: item
            for item in (self.cnn_digital_results + self.cnn_analog_results)
        }

        meter_results = []
        for meter in meters:
            component_confs = [
                all_results_dict[name].confidence
                for name in meter.config.value_names
                if name in all_results_dict
            ]
            if component_confs:
                avg_conf = round(sum(component_confs) / len(component_confs), 1)
                min_conf = min(component_confs)
            else:
                avg_conf = 100.0
                min_conf = 100.0

            if min_conf >= 80.0 and avg_conf >= 85.0:
                quality = "good"
            elif min_conf >= 60.0 and avg_conf >= 65.0:
                quality = "warning"
            else:
                quality = "uncertain"

            meter_results.append(
                MeterValue(
                    name=meter.name,
                    value=meter.value,
                    unit=meter.config.unit,
                    quality=quality,
                    confidence=avg_conf,
                )
            )

        return MeterResult(
            meters=meter_results,
            digital_results=digital_results,
            analog_results=analog_results,
            confidence_scores=confidence_scores,
            error="",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _solve_model(self, model: str, details: ModelDetails) -> str:
        if model.lower() != MODEL_AUTO:
            return model
        if details.numer_output == 2:
            return MODEL_ANALOG
        if details.numer_output == 11:
            return MODEL_DIGITAL
        if details.numer_output == 100:
            # 32x32 model = analog 0.00-9.99
            if details.xsize == 32 and details.ysize == 32:
                return MODEL_ANALOG100
            # Other 100-output models are digital 00-99
            return MODEL_DIGITAL100
        raise ValueError(f"Unable to determine model from details: {details}")
