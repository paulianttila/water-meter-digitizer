"""Digitizer processing pipeline orchestrator coordinating CNN inference, rollover corrections, and consistency validation."""

import logging
import math

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
from processor.models import (
    DEFAULT_MIN_CONFIDENCE_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    MODEL_AUTO,
    QUALITY_HIGH_AVG_CONFIDENCE,
    QUALITY_HIGH_MIN_CONFIDENCE,
    QUALITY_WARNING_AVG_CONFIDENCE,
    QUALITY_WARNING_MIN_CONFIDENCE,
    Meter,
    MeterResult,
    MeterValue,
    ReadoutResult,
)
from processor.quality import determine_quality
from processor.result_builder import build_meter_result
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

__all__ = [
    "DEFAULT_MIN_CONFIDENCE_THRESHOLD",
    "MIN_CONFIDENCE_THRESHOLD",
    "MODEL_AUTO",
    "QUALITY_HIGH_AVG_CONFIDENCE",
    "QUALITY_HIGH_MIN_CONFIDENCE",
    "QUALITY_WARNING_AVG_CONFIDENCE",
    "QUALITY_WARNING_MIN_CONFIDENCE",
    "DigitizerProcessor",
    "Meter",
    "MeterResult",
    "MeterValue",
    "ReadoutResult",
    "determine_quality",
]

logger = logging.getLogger(__name__)


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
        self.out_of_bounds_rois: set[str] = set()
        self.quality_high_min_confidence: float = QUALITY_HIGH_MIN_CONFIDENCE
        self.quality_high_avg_confidence: float = QUALITY_HIGH_AVG_CONFIDENCE
        self.quality_warning_min_confidence: float = QUALITY_WARNING_MIN_CONFIDENCE
        self.quality_warning_avg_confidence: float = QUALITY_WARNING_AVG_CONFIDENCE

    def set_quality_thresholds(
        self,
        high_min: float | None = None,
        high_avg: float | None = None,
        warning_min: float | None = None,
        warning_avg: float | None = None,
    ) -> "DigitizerProcessor":
        if high_min is not None:
            self.quality_high_min_confidence = high_min
        if high_avg is not None:
            self.quality_high_avg_confidence = high_avg
        if warning_min is not None:
            self.quality_warning_min_confidence = warning_min
        if warning_avg is not None:
            self.quality_warning_avg_confidence = warning_avg
        return self

    def _resolve_quality_thresholds(
        self, meter: Meter
    ) -> tuple[float, float, float, float]:
        cfg = getattr(meter, "config", None)
        high_min = (
            getattr(cfg, "quality_high_min_confidence", None)
            if cfg is not None
            else None
        )
        if high_min is None:
            high_min = self.quality_high_min_confidence

        high_avg = (
            getattr(cfg, "quality_high_avg_confidence", None)
            if cfg is not None
            else None
        )
        if high_avg is None:
            high_avg = self.quality_high_avg_confidence

        warn_min = (
            getattr(cfg, "quality_warning_min_confidence", None)
            if cfg is not None
            else None
        )
        if warn_min is None:
            warn_min = self.quality_warning_min_confidence

        warn_avg = (
            getattr(cfg, "quality_warning_avg_confidence", None)
            if cfg is not None
            else None
        )
        if warn_avg is None:
            warn_avg = self.quality_warning_avg_confidence

        return high_min, high_avg, warn_min, warn_avg

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

        oob_rois = {
            img.name
            for img in (analog_images + digital_images)
            if getattr(img, "out_of_bounds", False)
        }

        # Update instance attributes for backward compatibility / inspection
        self.cnn_analog_results = analog_results
        self.cnn_digital_results = digital_results
        self.available_values = available_values
        self.out_of_bounds_rois = oob_rois

        return self._build_meter_values(
            meter_configs=meter_configs,
            analog_results=analog_results,
            digital_results=digital_results,
            available_values=available_values,
            min_confidence_threshold=min_conf,
            alignment_error=alignment_error,
            out_of_bounds_rois=oob_rois,
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
        out_of_bounds_rois: set[str] | None = None,
    ) -> MeterResult:
        if out_of_bounds_rois is None:
            out_of_bounds_rois = self.out_of_bounds_rois
        meters = self._get_meter_values(meter_configs, available_values)
        self._postprocess_meter_values(
            meters=meters,
            values=available_values,
            cnn_results=(digital_results + analog_results),
            min_confidence_threshold=min_confidence_threshold,
            out_of_bounds_rois=out_of_bounds_rois,
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
            out_of_bounds_rois=out_of_bounds_rois,
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
            out_of_bounds_rois=self.out_of_bounds_rois,
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
        out_of_bounds_rois: set[str] | None = None,
    ) -> None:
        cnn_results_dict = {item.name: item for item in cnn_results}
        for meter in meters:
            self._postprocess_meter_value(
                meter,
                values,
                cnn_results_dict,
                min_confidence_threshold=min_confidence_threshold,
                out_of_bounds_rois=out_of_bounds_rois,
            )

    def _postprocess_meter_value(
        self,
        meter: Meter,
        values: dict,
        cnn_results: dict[str, ReadoutResult],
        min_confidence_threshold: float | None = None,
        out_of_bounds_rois: set[str] | None = None,
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

        oobs = out_of_bounds_rois or set()
        meter_oob = [name for name in meter.config.value_names if name in oobs]
        if meter_oob:
            oob_warn = f"ROI out of image bounds: {', '.join(meter_oob)}"
            meter.valid = False
            meter.warning = (
                f"{oob_warn}, {meter.warning}" if meter.warning else oob_warn
            )

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

        high_min, high_avg, warn_min, warn_avg = self._resolve_quality_thresholds(meter)
        quality = determine_quality(
            value=meter.value,
            valid=meter.valid,
            warning=meter.warning,
            min_conf=min_conf,
            avg_conf=avg_conf,
            quality_high_min_confidence=high_min,
            quality_high_avg_confidence=high_avg,
            quality_warning_min_confidence=warn_min,
            quality_warning_avg_confidence=warn_avg,
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
        out_of_bounds_rois: set[str] | None = None,
    ) -> MeterResult:
        return build_meter_result(
            meters=meters,
            analog_results=(
                analog_results
                if analog_results is not None
                else self.cnn_analog_results
            ),
            digital_results=(
                digital_results
                if digital_results is not None
                else self.cnn_digital_results
            ),
            alignment_error=alignment_error,
            out_of_bounds_rois=(
                out_of_bounds_rois
                if out_of_bounds_rois is not None
                else self.out_of_bounds_rois
            ),
            has_analog_reader=self.analog_counter_reader is not None,
            has_digital_reader=self.digital_counter_reader is not None,
            resolve_thresholds_fn=self._resolve_quality_thresholds,
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
