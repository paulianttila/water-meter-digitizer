"""MeterResult builder and formatting logic for digitizer output."""

from __future__ import annotations

import math
from collections.abc import Callable

from processor.models import Meter, MeterResult, MeterValue, ReadoutResult
from processor.quality import determine_quality
from processor.rollover_corrector import INVALID_DIGIT


def build_meter_result(
    meters: list[Meter],
    analog_results: list[ReadoutResult],
    digital_results: list[ReadoutResult],
    alignment_error: str = "",
    out_of_bounds_rois: set[str] | None = None,
    has_analog_reader: bool = True,
    has_digital_reader: bool = True,
    resolve_thresholds_fn: (
        Callable[[Meter], tuple[float, float, float, float]] | None
    ) = None,
) -> MeterResult:
    """Assemble final MeterResult object from processed meter models and raw CNN readouts."""
    analog_dict: dict[str, str] = {}
    confidence_scores: dict[str, float] = {}

    if has_analog_reader:
        for item in analog_results:
            val = (
                f"{item.value:.2f}"
                if isinstance(item.value, (int, float))
                else str(item.value)
            )
            analog_dict[item.name] = val
            confidence_scores[item.name] = item.confidence

    digital_dict: dict[str, str] = {}
    if has_digital_reader:
        for item in digital_results:
            if item.value == "-":
                val = "-"
            elif isinstance(item.value, float) and math.isnan(item.value):
                val = INVALID_DIGIT
            else:
                val = str(item.value)
            digital_dict[item.name] = val
            confidence_scores[item.name] = item.confidence

    all_results_dict = {item.name: item for item in (digital_results + analog_results)}

    meter_results: list[MeterValue] = []
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

        if resolve_thresholds_fn:
            high_min, high_avg, warn_min, warn_avg = resolve_thresholds_fn(meter)
        else:
            high_min, high_avg, warn_min, warn_avg = (80.0, 85.0, 60.0, 65.0)

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
    if out_of_bounds_rois:
        unassigned_oob = [
            name
            for name in sorted(out_of_bounds_rois)
            if not any(name in m.config.value_names for m in meters)
        ]
        if unassigned_oob:
            oob_warn = f"ROI out of image bounds: {', '.join(unassigned_oob)}"
            if oob_warn not in all_warnings:
                all_warnings.append(oob_warn)
    warning_str = ", ".join(all_warnings) if all_warnings else ""
    is_valid = (
        bool(meter_results)
        and all(m.valid for m in meter_results)
        and not bool(alignment_error)
        and not bool(out_of_bounds_rois)
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
