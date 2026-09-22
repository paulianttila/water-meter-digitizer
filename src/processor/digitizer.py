"""Digitizer processing pipeline orchestrator coordinating CNN inference, rollover corrections, and consistency validation."""

import logging
import math
from typing import Literal

from pydantic import BaseModel, Field

from cnn.analog_needle_cnn import AnalogNeedleCNN
from cnn.base import ModelDetails
from cnn.digital_counter_cnn import DigitalCounterCNN
from data_classes import CutImage, MeterConfig
from previous_value import (
    load_previous_value_from_file,
    load_previous_value_record,
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
from utils.decorators import log_execution_time
from utils.math import fill_with_predecessor_digits

logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE_THRESHOLD = 60.0
MIN_CONFIDENCE_THRESHOLD = DEFAULT_MIN_CONFIDENCE_THRESHOLD
MODEL_AUTO = "auto"

QUALITY_HIGH_MIN_CONFIDENCE = 80.0
QUALITY_HIGH_AVG_CONFIDENCE = 85.0
QUALITY_WARNING_MIN_CONFIDENCE = 60.0
QUALITY_WARNING_AVG_CONFIDENCE = 65.0


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
    min_confidence: float = 100.0
    filled_digits: int = 0
    warning: str = ""
    valid: bool = True


def determine_quality(
    value: str,
    valid: bool,
    warning: str,
    min_conf: float,
    avg_conf: float,
) -> Literal["good", "warning", "uncertain"]:
    """Classify readout quality based on unreadable digits, warnings, validity, and confidence thresholds."""
    if INVALID_DIGIT in value:
        return "uncertain"
    elif warning:
        return "warning"
    elif not valid:
        return "uncertain"
    elif (
        min_conf >= QUALITY_HIGH_MIN_CONFIDENCE
        and avg_conf >= QUALITY_HIGH_AVG_CONFIDENCE
    ):
        return "good"
    elif (
        min_conf >= QUALITY_WARNING_MIN_CONFIDENCE
        and avg_conf >= QUALITY_WARNING_AVG_CONFIDENCE
    ):
        return "warning"
    else:
        return "uncertain"


class MeterResult(BaseModel):
    meters: list[MeterValue] = Field(default_factory=list)
    digital_results: dict[str, str] = Field(default_factory=dict)
    analog_results: dict[str, str] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    error: str = ""
    warning: str = ""
    valid: bool = True


class Meter(BaseModel):
    config: MeterConfig
    name: str = ""
    value: str = ""  # value after postprocessing
    unprocessed_value: str = ""  # value without postprocessing
    previous_value: str = ""
    previous_value_last_change: str = ""
    warning: str = ""
    valid: bool = True
    filled_digits: int = 0


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
        alignment_error: str = "",
    ) -> MeterResult:
        if self.analog_counter_reader is None and self.digital_counter_reader is None:
            raise ValueError("No CNN reader initialized")

        min_conf = (
            min_confidence_threshold
            if min_confidence_threshold is not None
            else self.min_confidence_threshold
        )
        if detect_negative_sign is not None:
            detect_neg = detect_negative_sign
        elif any(getattr(m, "detect_negative_sign", False) for m in meter_configs):
            detect_neg = True
        else:
            detect_neg = self.detect_negative_sign

        analog_results = self._run_analog_cnn(analog_images)
        digital_results = self._run_digital_cnn(
            digital_images,
            detect_negative_sign=detect_neg,
            min_confidence_threshold=min_conf,
        )
        all_results = analog_results + digital_results
        available_values = self._evaluate_cnn_results(
            all_results, min_confidence_threshold=min_conf
        )

        # Update instance attributes for backward compatibility / inspection
        self.cnn_analog_results = analog_results
        self.cnn_digital_results = digital_results
        self.available_values = available_values

        return self._build_meter_values(
            meter_configs=meter_configs,
            analog_results=analog_results,
            digital_results=digital_results,
            available_values=available_values,
            min_confidence_threshold=min_conf,
            alignment_error=alignment_error,
        )

    async def process_async(
        self,
        analog_images: list[CutImage],
        digital_images: list[CutImage],
        meter_configs: list[MeterConfig],
        min_confidence_threshold: float | None = None,
        detect_negative_sign: bool | None = None,
        alignment_error: str = "",
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
            alignment_error,
        )

    def _run_analog_cnn(self, images: list[CutImage]) -> list[ReadoutResult]:
        if self.analog_counter_reader is None or not images:
            return []
        result: list[ReadoutResult] = []
        model = self._solve_model(
            self.analog_model, self.analog_counter_reader.get_model_details()
        )
        for item in images:
            value, conf = self.analog_counter_reader.readout_with_confidence(item.image)
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
        logger.debug("Analog CNN results: %s", result)
        return result

    def _run_digital_cnn(
        self,
        images: list[CutImage],
        detect_negative_sign: bool,
        min_confidence_threshold: float,
    ) -> list[ReadoutResult]:
        if self.digital_counter_reader is None or not images:
            return []
        result: list[ReadoutResult] = []
        model = self._solve_model(
            self.digital_model, self.digital_counter_reader.get_model_details()
        )
        for item in images:
            value, conf = self.digital_counter_reader.readout_with_confidence(
                item.image
            )

            if detect_negative_sign:
                is_unreadable = (
                    isinstance(value, float) and math.isnan(value)
                ) or conf < min_confidence_threshold
                if is_unreadable:
                    sign_thresh = (
                        min(50.0, min_confidence_threshold)
                        if min_confidence_threshold > 0
                        else 50.0
                    )
                    is_minus, minus_conf = detect_minus_sign(
                        item.image, min_confidence=sign_thresh
                    )
                    logger.debug(
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
        logger.debug("Digital CNN results: %s", result)
        return result

    def _evaluate_cnn_results(
        self,
        cnn_results: list[ReadoutResult],
        min_confidence_threshold: float,
    ) -> dict[str, int | str]:
        """Evaluate raw CNN predictions into preliminary discrete baseline digits (without predecessor chaining).

        Used to establish unprocessed_value before rollover post-processing.
        """
        available_values: dict[str, int | str] = {}

        for result in cnn_results:
            if result.value == "-":
                digit: int | str = "-"
            elif result.confidence < min_confidence_threshold or (
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

        logger.debug("Available values: %s", available_values)
        return available_values

    @log_execution_time
    def execute_analog_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        self.cnn_analog_results = self._run_analog_cnn(images)
        return self

    @log_execution_time
    def execute_digital_cnn(self, images: list[CutImage]) -> "DigitizerProcessor":
        self.cnn_digital_results = self._run_digital_cnn(
            images,
            detect_negative_sign=self.detect_negative_sign,
            min_confidence_threshold=self.min_confidence_threshold,
        )
        return self

    def evaluate_cnn_results(self) -> "DigitizerProcessor":
        self.available_values = self._evaluate_cnn_results(
            self.cnn_analog_results + self.cnn_digital_results,
            min_confidence_threshold=self.min_confidence_threshold,
        )
        return self

    def _evaluate_counters(
        self, values: list[ReadoutResult], min_confidence_threshold: float | None = None
    ) -> dict[str, str]:
        thresh = (
            min_confidence_threshold
            if min_confidence_threshold is not None
            else self.min_confidence_threshold
        )
        return RolloverCorrector.evaluate_counters(
            values=values,
            min_confidence_threshold=thresh,
        )

    # ------------------------------------------------------------------
    # Meter post-processing
    # ------------------------------------------------------------------

    def _build_meter_values(
        self,
        meter_configs: list[MeterConfig],
        analog_results: list[ReadoutResult],
        digital_results: list[ReadoutResult],
        available_values: dict[str, int | str],
        min_confidence_threshold: float,
        alignment_error: str = "",
    ) -> MeterResult:
        meters = self._get_meter_values(meter_configs, available_values)
        self._postprocess_meter_values(
            meters=meters,
            values=available_values,
            cnn_results=(digital_results + analog_results),
            min_confidence_threshold=min_confidence_threshold,
        )
        if alignment_error:
            align_warn = f"Alignment failed: {alignment_error}"
            for meter in meters:
                meter.valid = False
                meter.warning = (
                    f"{align_warn}, {meter.warning}" if meter.warning else align_warn
                )
        return self._gen_result(
            meters,
            analog_results=analog_results,
            digital_results=digital_results,
            alignment_error=alignment_error,
        )

    def get_meter_values(
        self, meter_configs: list[MeterConfig], alignment_error: str = ""
    ) -> MeterResult:
        return self._build_meter_values(
            meter_configs=meter_configs,
            analog_results=self.cnn_analog_results,
            digital_results=self.cnn_digital_results,
            available_values=self.available_values,
            min_confidence_threshold=self.min_confidence_threshold,
            alignment_error=alignment_error,
        )

    def _get_meter_values(
        self,
        meter_configs: list[MeterConfig],
        available_values: dict[str, int | str] | None = None,
    ) -> list[Meter]:
        vals = (
            available_values if available_values is not None else self.available_values
        )
        meters: list[Meter] = []
        for meter_config in meter_configs:
            value = FormatParser.format_template(meter_config.format, vals)
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
        min_confidence_threshold: float | None = None,
    ) -> None:
        cnn_results_dict = {item.name: item for item in cnn_results}
        for meter in meters:
            self._postprocess_meter_value(
                meter,
                values,
                cnn_results_dict,
                min_confidence_threshold=min_confidence_threshold,
            )

    def _postprocess_meter_value(
        self,
        meter: Meter,
        values: dict,
        cnn_results: dict[str, ReadoutResult],
        min_confidence_threshold: float | None = None,
    ) -> None:
        results = self._get_readout_results(meter, cnn_results)
        logger.debug(" Postprocess meter: %s, readout results: %s", meter, results)

        evaluated_values = self._evaluate_counters(
            results, min_confidence_threshold=min_confidence_threshold
        )
        meter.value = FormatParser.format_template(
            meter.config.format, evaluated_values
        )
        if not meter.unprocessed_value or "{" in meter.unprocessed_value:
            meter.unprocessed_value = meter.value

        if meter.config.use_previous_value:
            if self.previous_value_file is None:
                raise ValueError(
                    "Previous value file must be configured when use_previous_value is enabled"
                )
            try:
                meter.previous_value = load_previous_value_from_file(
                    self.previous_value_file,
                    meter.name,
                    meter.config.pre_value_from_file_max_age,
                )
                try:
                    record = load_previous_value_record(
                        self.previous_value_file,
                        meter.name,
                        meter.config.pre_value_from_file_max_age,
                    )
                    meter.previous_value_last_change = record.get(
                        "last_change", ""
                    ) or record.get("time", "")
                except Exception:
                    meter.previous_value_last_change = ""
            except ValueError as e:
                logger.info(
                    "Previous value could not be loaded for meter '%s': %s",
                    meter.name,
                    e,
                )
                meter.previous_value = ""
                meter.previous_value_last_change = ""

        if meter.config.use_extended_resolution:
            meter.value = self._append_extended_digit(meter, cnn_results)

        if (
            meter.config.use_previous_value
            and meter.previous_value
            and INVALID_DIGIT not in meter.previous_value
        ):
            orig_prev_len = len(meter.previous_value)
            meter.previous_value = FormatParser.adapt_previous_value_to_match_length(
                meter.value, meter.previous_value
            )
            if len(meter.previous_value) < orig_prev_len:
                meter.warning = "Previous value truncated to match format length"
                meter.valid = False

            before_invalids = meter.value.count(INVALID_DIGIT)
            meter.value = fill_with_predecessor_digits(
                meter.value, meter.previous_value
            )
            after_invalids = meter.value.count(INVALID_DIGIT)
            meter.filled_digits = max(0, before_invalids - after_invalids)

        if INVALID_DIGIT in meter.value:
            meter.valid = False
            if not meter.warning:
                meter.warning = "Unreadable digit(s)"
        elif (
            meter.config.use_previous_value
            and meter.previous_value
            and meter.config.consistency_enabled
            and meter.valid
        ):
            try:
                ConsistencyValidator.validate_reading(
                    meter.config,
                    meter.value,
                    meter.previous_value,
                    last_change_time=meter.previous_value_last_change,
                )
            except ConsistencyError as err:
                logger.warning(
                    "Consistency validation warning for meter '%s': %s",
                    meter.name,
                    err,
                )
                meter.warning = str(err)
                meter.valid = False

        if (
            meter.config.use_previous_value
            and self.previous_value_file
            and meter.valid
            and not meter.warning
            and INVALID_DIGIT not in meter.value
        ):
            try:
                save_previous_value_to_file(
                    str(self.previous_value_file), meter.name, meter.value
                )
            except Exception as e:
                logger.warning(
                    "Failed to save previous value for meter '%s': %s",
                    meter.name,
                    e,
                )

        component_confs = [r.confidence for r in results if r.confidence is not None]
        if component_confs:
            avg_conf = round(sum(component_confs) / len(component_confs), 1)
            min_conf = round(min(component_confs), 1)
        else:
            avg_conf = 100.0
            min_conf = 100.0

        quality = determine_quality(
            value=meter.value,
            valid=meter.valid,
            warning=meter.warning,
            min_conf=min_conf,
            avg_conf=avg_conf,
        )

        warn_field = f' warning="{meter.warning}"' if meter.warning else ""
        logger.info(
            "Meter '%s': raw=%s, corrected=%s prev=%s filled=%d conf_avg=%.1f%% conf_min=%.1f%% quality=%s valid=%s%s",
            meter.name,
            meter.unprocessed_value,
            meter.value,
            meter.previous_value or "none",
            meter.filled_digits,
            avg_conf,
            min_conf,
            quality,
            meter.valid,
            warn_field,
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

    def _gen_result(
        self,
        meters: list[Meter],
        analog_results: list[ReadoutResult] | None = None,
        digital_results: list[ReadoutResult] | None = None,
        alignment_error: str = "",
    ) -> MeterResult:
        if analog_results is None:
            analog_results = self.cnn_analog_results
        if digital_results is None:
            digital_results = self.cnn_digital_results

        analog_dict = {}
        confidence_scores = {}
        if self.analog_counter_reader is not None:
            for item in analog_results:
                val = f"{item.value:.2f}"
                analog_dict[item.name] = val
                confidence_scores[item.name] = item.confidence
        digital_dict = {}
        if self.digital_counter_reader is not None:
            for item in digital_results:
                if item.value == "-":
                    val = "-"
                elif isinstance(item.value, float) and math.isnan(item.value):
                    val = INVALID_DIGIT
                else:
                    val = str(item.value)
                digital_dict[item.name] = val
                confidence_scores[item.name] = item.confidence

        all_results_dict = {
            item.name: item for item in (digital_results + analog_results)
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
                min_conf = round(min(component_confs), 1)
            else:
                avg_conf = 100.0
                min_conf = 100.0

            quality = determine_quality(
                value=meter.value,
                valid=meter.valid,
                warning=meter.warning,
                min_conf=min_conf,
                avg_conf=avg_conf,
            )

            meter_results.append(
                MeterValue(
                    name=meter.name,
                    value=meter.value,
                    unit=meter.config.unit,
                    quality=quality,
                    confidence=avg_conf,
                    min_confidence=min_conf,
                    filled_digits=meter.filled_digits,
                    warning=meter.warning,
                    valid=meter.valid,
                )
            )

        all_warnings = [m.warning for m in meter_results if m.warning]
        if alignment_error:
            align_warn = f"Alignment failed: {alignment_error}"
            if align_warn not in all_warnings:
                all_warnings.insert(0, align_warn)
        warning_str = ", ".join(all_warnings) if all_warnings else ""
        is_valid = (
            bool(meter_results)
            and all(m.valid for m in meter_results)
            and not bool(alignment_error)
        )

        return MeterResult(
            meters=meter_results,
            digital_results=digital_dict,
            analog_results=analog_dict,
            confidence_scores=confidence_scores,
            error="",
            warning=warning_str,
            valid=is_valid,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _solve_model(self, model: str, details: ModelDetails) -> str:
        if model.lower() != MODEL_AUTO:
            return model
        if details.num_outputs == 2:
            return MODEL_ANALOG
        if details.num_outputs == 11:
            return MODEL_DIGITAL
        if details.num_outputs == 100:
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
    "determine_quality",
]
