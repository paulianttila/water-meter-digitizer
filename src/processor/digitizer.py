"""Digitizer processing pipeline orchestrator coordinating CNN inference, rollover corrections, and consistency validation."""

import logging
import math
from typing import Literal

from pydantic import BaseModel, Field

from cnn.analog_needle_cnn import AnalogNeedleCNN
from cnn.base import ModelDetails
from cnn.digital_counter_cnn import DigitalCounterCNN
from data_classes import CutImage, MeterConfig
from decorators.decorators import log_execution_time
from previous_value import (
    load_previous_value_from_file,
    save_previous_value_to_file,
)
from processor.consistency_validator import ConsistencyError, ConsistencyValidator
from processor.format_parser import FormatParser
from processor.rollover_corrector import (
    ANALOG_MODELS,
    DIGITAL_MODELS,
    INVALID_DIGIT,
    MODEL_ANALOG,
    MODEL_ANALOG100,
    MODEL_DIGITAL,
    MODEL_DIGITAL100,
    RolloverCorrector,
)
from processor.sign_detector import detect_minus_sign
from utils.math import fill_with_predecessor_digits

logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE_THRESHOLD = 60.0
MIN_CONFIDENCE_THRESHOLD = DEFAULT_MIN_CONFIDENCE_THRESHOLD
MODEL_AUTO = "auto"


class ReadoutResult(BaseModel):
    name: str
    value: float | str
    model: str
    confidence: float = 100.0


class MeterValue(BaseModel):
    name: str
    value: str
    unit: str = ""
    quality: Literal["good", "warning", "uncertain"] = "good"
    confidence: float = 100.0


class MeterResult(BaseModel):
    meters: list[MeterValue] = Field(default_factory=list)
    digital_results: dict[str, str] = Field(default_factory=dict)
    analog_results: dict[str, str] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    error: str = ""


class Meter(BaseModel):
    config: MeterConfig
    name: str = ""
    value: str = ""  # value after postprocessing
    unprocessed_value: str = ""  # value without postprocessing
    previous_value: str = ""


class DigitizerProcessor:
    """Orchestrates CNN readout inference, decimal rollover correction, format template assembly, and consistency checks."""

    def __init__(self) -> None:
        self.condition = None
        self.analog_counter_reader: AnalogNeedleCNN | None = None
        self.digital_counter_reader: DigitalCounterCNN | None = None
        self.analog_model: str = ""
        self.digital_model: str = ""
        self.previous_value_file: str | None = None
        self.min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE_THRESHOLD
        self.detect_negative_sign: bool = False
        self.cnn_digital_results: list[ReadoutResult] = []
        self.cnn_analog_results: list[ReadoutResult] = []
        self.available_values: dict[str, int | str] = {}

    def set_min_confidence_threshold(self, threshold: float) -> "DigitizerProcessor":
        self.min_confidence_threshold = threshold
        return self

    def set_detect_negative_sign(self, detect: bool) -> "DigitizerProcessor":
        self.detect_negative_sign = detect
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
        detect_negative_sign: bool | None = None,
    ) -> MeterResult:
        if self.analog_counter_reader is None and self.digital_counter_reader is None:
            raise ValueError("No CNN reader initialized")

        self.cnn_analog_results = []
        self.cnn_digital_results = []
        self.available_values = {}

        if min_confidence_threshold is not None:
            self.min_confidence_threshold = min_confidence_threshold
        if detect_negative_sign is not None:
            self.detect_negative_sign = detect_negative_sign
        elif any(getattr(m, "detect_negative_sign", False) for m in meter_configs):
            self.detect_negative_sign = True
        self.execute_analog_cnn(analog_images)
        self.execute_digital_cnn(digital_images)
        self.evaluate_cnn_results()
        return self.get_meter_values(meter_configs)

    async def process_async(
        self,
        analog_images: list[CutImage],
        digital_images: list[CutImage],
        meter_configs: list[MeterConfig],
        min_confidence_threshold: float | None = None,
        detect_negative_sign: bool | None = None,
    ) -> MeterResult:
        """Asynchronously process meter images off the main event loop."""
        import asyncio

        return await asyncio.to_thread(
            self.process,
            analog_images,
            digital_images,
            meter_configs,
            min_confidence_threshold,
            detect_negative_sign,
        )

    @log_execution_time
    def execute_analog_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        if self.analog_counter_reader is not None:
            result = []
            model = self._solve_model(
                self.analog_model, self.analog_counter_reader.get_model_details()
            )
            for item in images:
                value, conf = self.analog_counter_reader.readout_with_confidence(
                    item.image
                )
                value = round(value, 1)
                value = 0 if value == 10 else value
                result.append(
                    ReadoutResult(
                        name=item.name,
                        value=value,
                        model=model,
                        confidence=conf,
                    )
                )
            self.cnn_analog_results = result
            logger.debug("Analog CNN results: %s", self.cnn_analog_results)
        return self

    @log_execution_time
    def execute_digital_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        if self.digital_counter_reader is not None:
            result = []
            model = self._solve_model(
                self.digital_model, self.digital_counter_reader.get_model_details()
            )
            for item in images:
                value, conf = self.digital_counter_reader.readout_with_confidence(
                    item.image
                )

                if self.detect_negative_sign:
                    is_unreadable = (
                        isinstance(value, float) and math.isnan(value)
                    ) or conf < self.min_confidence_threshold
                    if is_unreadable:
                        sign_thresh = (
                            min(50.0, self.min_confidence_threshold)
                            if self.min_confidence_threshold > 0
                            else 50.0
                        )
                        is_minus, minus_conf = detect_minus_sign(
                            item.image, min_confidence=sign_thresh
                        )
                        logger.info(
                            "Minus sign detector for ROI '%s': detected=%s, confidence=%.1f%%",
                            item.name,
                            is_minus,
                            minus_conf,
                        )
                        if is_minus:
                            value = "-"
                            conf = minus_conf

                result.append(
                    ReadoutResult(
                        name=item.name,
                        value=value,
                        model=model,
                        confidence=conf,
                    )
                )
            self.cnn_digital_results = result
            logger.debug("Digital CNN results: %s", self.cnn_digital_results)
        return self

    def evaluate_cnn_results(self) -> "DigitizerProcessor":
        """Evaluate raw CNN predictions into preliminary discrete baseline digits (without predecessor chaining).

        Used to establish unprocessed_value before rollover post-processing.
        """
        available_values: dict[str, int | str] = {}

        for result in self.cnn_analog_results + self.cnn_digital_results:
            if result.value == "-":
                digit: int | str = "-"
            elif result.confidence < self.min_confidence_threshold or (
                isinstance(result.value, float) and math.isnan(result.value)
            ):
                digit = INVALID_DIGIT
            else:
                digit = RolloverCorrector.evaluate_counter(
                    name=result.name,
                    number=result.value,
                    predecessor_digit=None,
                    model=result.model,
                )
            available_values[result.name] = digit

        self.available_values = available_values
        logger.debug("Available values: %s", available_values)
        return self

    def _evaluate_counters(self, values: list[ReadoutResult]) -> dict[str, str]:
        return RolloverCorrector.evaluate_counters(
            values=values,
            min_confidence_threshold=self.min_confidence_threshold,
        )

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
            value = FormatParser.format_template(
                meter_config.format, self.available_values
            )
            meter = Meter(
                name=meter_config.name,
                value=value,
                unprocessed_value=value,
                config=meter_config,
            )
            logger.debug(" Meter: %s", meter)
            meters.append(meter)
        return meters

    def _postprocess_meter_values(
        self,
        meters: list[Meter],
        values: dict,
        cnn_results: list[ReadoutResult],
    ) -> None:
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
        logger.info(" Postprocess meter: %s, readout results: %s", meter, results)

        evaluated_values = self._evaluate_counters(results)
        meter.value = FormatParser.format_template(
            meter.config.format, evaluated_values
        )

        if meter.config.use_previous_value:
            if self.previous_value_file is None:
                raise ValueError(
                    "Previous value file must be configured when use_previous_value is enabled"
                )
            meter.previous_value = load_previous_value_from_file(
                self.previous_value_file,
                meter.name,
                meter.config.pre_value_from_file_max_age,
            )

        if meter.config.use_extended_resolution:
            meter.value = self._append_extended_digit(meter, cnn_results)

        if meter.config.use_previous_value:
            meter.previous_value = FormatParser.adapt_previous_value_to_match_length(
                meter.value, meter.previous_value
            )
            meter.value = fill_with_predecessor_digits(
                meter.value, meter.previous_value
            )
            if meter.config.consistency_enabled:
                ConsistencyValidator.validate_reading(
                    meter.config, meter.value, meter.previous_value
                )

            save_previous_value_to_file(
                str(self.previous_value_file), meter.name, meter.value
            )

    def _get_readout_results(
        self,
        meter: Meter,
        cnn_results: dict[str, ReadoutResult],
    ) -> list[ReadoutResult]:
        return [cnn_results[name] for name in meter.config.value_names]

    def _append_extended_digit(
        self,
        meter: Meter,
        cnn_results: dict[str, ReadoutResult],
    ) -> str:
        last_digit = cnn_results.get(meter.config.value_names[-1])
        last_val = last_digit.value if last_digit else None
        return FormatParser.append_extended_digit(meter.value, last_val)

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
                if item.value == "-":
                    val = "-"
                elif isinstance(item.value, float) and math.isnan(item.value):
                    val = INVALID_DIGIT
                else:
                    val = str(item.value)
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

            quality: Literal["good", "warning", "uncertain"]
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


__all__ = [
    "ANALOG_MODELS",
    "DIGITAL_MODELS",
    "INVALID_DIGIT",
    "MODEL_ANALOG",
    "MODEL_ANALOG100",
    "MODEL_AUTO",
    "MODEL_DIGITAL",
    "MODEL_DIGITAL100",
    "ConsistencyError",
    "ConsistencyValidator",
    "DigitizerProcessor",
    "FormatParser",
    "Meter",
    "MeterConfig",
    "MeterResult",
    "MeterValue",
    "ReadoutResult",
    "RolloverCorrector",
]
