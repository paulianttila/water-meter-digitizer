"""Meter readout, ROI visualization, baseline setting, and image caching endpoints."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

import previous_value
import utils.image
from configuration import Config
from decorators.decorators import log_execution_time
from processor.digitizer import DigitizerProcessor, MeterResult
from processor.image import (
    ImageProcessor,
)
from utils.diagnostics import get_allowed_asset_directories
from utils.download import DownloadFailure

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meter"])

# Global fallback reference to the FastAPI app, populated during main startup
_app_ref: Any = None


def set_app_ref(app_instance: Any) -> None:
    """Set global app reference for standalone get_meter_data calls."""
    global _app_ref
    _app_ref = app_instance


def get_current_app(request: Request | None = None) -> Any:
    """Retrieve app instance from request or fallback reference."""
    if request is not None:
        return request.app
    return _app_ref


@router.get("/image/{image}")
@log_execution_time
def get_image(image: str, request: Request) -> Response:
    image = image.removesuffix(".jpg")
    logger.debug(f"Getting image: {image}")
    cache = getattr(request.app.state, "image_cache", None)
    img = cache.get(image) if cache else None
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    image_bytes = utils.image.convert_image_to_bytes(img)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.get("/roi")
@log_execution_time
def get_roi(
    request: Request,
    url: str = "",
    draw_refs: bool = True,
    draw_digital: bool = True,
    draw_analog: bool = True,
) -> Response:
    """Generate and return the composite ROI overlay image as a direct JPEG stream."""
    config: Config = getattr(request.app.state, "config", Config())
    try:
        url = url or config.image_source.url
        timeout = config.image_source.timeout

        roi_proc = (
            ImageProcessor()
            .download_image(
                url,
                timeout,
                config.image_source.min_size,
                allowed_directories=get_allowed_asset_directories(config),
            )
            .rotate_image(config.alignment.rotate_angle)
            .align_image(config.alignment.ref_images)
            .draw_meter_rois(
                config,
                draw_refs=draw_refs,
                draw_digital=draw_digital,
                draw_analog=draw_analog,
            )
        )

        image_bytes = utils.image.convert_image_to_bytes(roi_proc.get_image())
        return Response(content=image_bytes, media_type="image/jpeg")
    except DownloadFailure as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/setPreviousValue")
@router.get("/set_previous_value")
@log_execution_time
def set_previous_value(name: str, value: str, request: Request) -> Response:
    config: Config = getattr(request.app.state, "config", Config())
    try:
        if not value or not isinstance(value, str):
            raise ValueError("Value cannot be empty")
        cleaned_value = value.strip()
        try:
            val_float = float(cleaned_value)
            if val_float < 0:
                raise ValueError("Value cannot be negative")
        except ValueError as e:
            if "negative" in str(e):
                raise
            raise ValueError(f"Value {value} is not a number") from e

        if not name or not name.strip():
            raise ValueError("Meter name cannot be empty")
        cleaned_name = name.strip()

        previous_value.save_previous_value_to_file(
            config.previous_value_file, cleaned_name, cleaned_value
        )
        return JSONResponse(
            {
                "status": "success",
                "message": (
                    f"Successfully updated baseline for '{cleaned_name}' to "
                    f"{cleaned_value}"
                ),
                "meter": cleaned_name,
                "value": cleaned_value,
                "error": "",
            }
        )
    except Exception as e:
        return JSONResponse(
            {
                "status": "error",
                "message": str(e),
                "error": str(e),
            },
            status_code=400,
        )


@router.get("/get_previous_values")
@router.get("/getPreviousValues")
@log_execution_time
def get_previous_values(request: Request) -> Response:
    config: Config = getattr(request.app.state, "config", Config())
    prev_file = getattr(config, "previous_value_file", "/config/prevalue.ini")
    meter_configs = getattr(config, "meter_configs", [])
    raw_values = previous_value.get_all_previous_values(prev_file)

    enabled_meters = []
    for m in meter_configs:
        if getattr(m, "use_previous_value", False):
            m_data = raw_values.get(m.name, {})
            enabled_meters.append(
                {
                    "name": m.name,
                    "value": m_data.get("value", ""),
                    "time": m_data.get("time", ""),
                    "unit": getattr(m, "unit", ""),
                    "max_age_minutes": getattr(m, "pre_value_from_file_max_age", 0),
                    "consistency_enabled": getattr(m, "consistency_enabled", False),
                    "max_rate_value": getattr(m, "max_rate_value", 0.0),
                }
            )

    if not enabled_meters:
        for m in meter_configs:
            if m.name == "total":
                m_data = raw_values.get(m.name, {})
                enabled_meters.append(
                    {
                        "name": m.name,
                        "value": m_data.get("value", ""),
                        "time": m_data.get("time", ""),
                        "unit": getattr(m, "unit", ""),
                        "max_age_minutes": getattr(m, "pre_value_from_file_max_age", 0),
                        "consistency_enabled": getattr(m, "consistency_enabled", False),
                        "max_rate_value": getattr(m, "max_rate_value", 0.0),
                    }
                )

    return JSONResponse(
        {
            "status": "success",
            "file": prev_file,
            "meters": enabled_meters,
            "raw_sections": raw_values,
        }
    )


@router.get("/meter")
@log_execution_time
def get_meters(
    request: Request,
    format: str = "json",
    url: str = "",
    saveimages: bool = False,
) -> Response:
    """Execute meter readout and return structured JSON (or raw value)."""
    if format not in ["json", "value", "raw"]:
        return JSONResponse(
            {"error": "Invalid format. Use 'json' or 'value'"},
            status_code=400,
        )

    try:
        result = get_meter_data(url=url, saveimages=saveimages, request=request)
    except Exception as e:
        logger.warning(f"Error occurred: {e!s}")
        return JSONResponse({"error": str(e)}, status_code=500)

    if format in ["value", "raw"]:
        main_val = result.meters[0].value if result.meters else ""
        return Response(content=main_val, media_type="text/plain")

    return JSONResponse(result.model_dump())


@log_execution_time
def get_meter_data(
    url: str = "",
    saveimages: bool = False,
    request: Request | None = None,
    app_instance: Any = None,
) -> MeterResult:
    """Execute complete meter reading pipeline (fetch, CNN, evaluate, publish)."""
    app = app_instance or get_current_app(request)
    config: Config = getattr(app.state, "config", Config()) if app else Config()

    url = url or config.image_source.url
    if not url:
        raise ValueError(
            "No camera or image URL configured. Please set 'image_source.url' "
            "in config."
        )
    timeout = config.image_source.timeout

    image_processor = ImageProcessor()
    (
        image_processor.enable_image_saving(saveimages)
        .download_image(
            url,
            timeout,
            config.image_source.min_size,
            allowed_directories=get_allowed_asset_directories(config),
        )
        .save_image("original")
        .rotate_image(config.alignment.rotate_angle)
        .save_image("rotated")
        .align_image(config.alignment.ref_images)
        .save_image("aligned")
        .rotate_image(config.alignment.post_rotate_angle)
        .save_image("post_rotated")
        .if_(config.crop.enabled)
        .crop_image(config.crop.x, config.crop.y, config.crop.w, config.crop.h)
        .save_image("cropped")
        .endif_()
        .if_(config.resize.enabled)
        .resize_image(config.resize.w, config.resize.h)
        .save_image("resized")
        .endif_()
        .if_(config.image_processing.enabled and config.image_processing.grayscale)
        .to_gray_scale()
        .save_image("gray")
        .endif_()
        .if_(config.image_processing.enabled)
        .adjust_image(
            brightness=config.image_processing.brightness,
            contrast=config.image_processing.contrast,
            sharpness=config.image_processing.sharpness,
            color=config.image_processing.color,
        )
        .endif_()
        .if_(
            config.image_processing.enabled
            and config.image_processing.autocontrast.enabled
        )
        .autocontrast_image(
            cutoff_low=config.image_processing.autocontrast.cutoff_low,
            cutoff_high=config.image_processing.autocontrast.cutoff_high,
            ignore=config.image_processing.autocontrast.ignore,
        )
        .save_image("processed")
        .endif_()
        .if_(
            config.image_processing.enabled
            and config.image_processing.glare_suppression.enabled
        )
        .suppress_glare(
            mode=config.image_processing.glare_suppression.mode,
            inpaint_threshold=config.image_processing.glare_suppression.inpaint_threshold,
            inpaint_radius=config.image_processing.glare_suppression.inpaint_radius,
            clahe_clip_limit=config.image_processing.glare_suppression.clahe_clip_limit,
            clahe_grid_size=config.image_processing.glare_suppression.clahe_grid_size,
        )
        .save_image("glare_suppressed")
        .endif_()
        .save_image("final", True)
    )
    autocontrast = (
        config.image_processing.enabled
        and config.image_processing.autocontrast_cut_images.enabled
    )
    glare_cut = (
        config.image_processing.enabled
        and config.image_processing.glare_suppression.enabled
        and config.image_processing.glare_suppression.apply_to_cut_images
    )

    def _extract_rois(positions):
        return (
            image_processor.start_image_cutting()
            .cut_images(
                positions,
                autocontrast=autocontrast,
                cutoff_low=config.image_processing.autocontrast_cut_images.cutoff_low,
                cutoff_high=config.image_processing.autocontrast_cut_images.cutoff_high,
                ignore=config.image_processing.autocontrast_cut_images.ignore,
                glare_suppression=glare_cut,
                glare_mode=config.image_processing.glare_suppression.mode,
                glare_inpaint_threshold=config.image_processing.glare_suppression.inpaint_threshold,
                glare_inpaint_radius=config.image_processing.glare_suppression.inpaint_radius,
                glare_clahe_clip_limit=config.image_processing.glare_suppression.clahe_clip_limit,
                glare_clahe_grid_size=config.image_processing.glare_suppression.clahe_grid_size,
            )
            .stop_image_cutting()
            .save_cut_images()
            .get_cut_images()
        )

    digital_images = _extract_rois(config.digital_readout.cut_images)
    analog_images = _extract_rois(config.analog_readout.cut_images)

    # Generate and store ROI overlay image with distinct colors
    final_img = image_processor.pictures.get("final")
    if final_img is not None:
        roi_proc = ImageProcessor().set_image(final_img.copy()).draw_meter_rois(config)
        image_processor.pictures["roi"] = roi_proc.get_image()

    if app and hasattr(app.state, "image_cache"):
        app.state.image_cache.set_many(image_processor.get_pictures())

    meter_result = (
        DigitizerProcessor()
        .set_min_confidence_threshold(config.min_confidence_threshold)
        .init_analog_model(
            config.analog_readout.model_file, config.analog_readout.model
        )
        .init_digital_model(
            config.digital_readout.model_file, config.digital_readout.model
        )
        .use_previous_value_file(config.previous_value_file)
        .process(
            analog_images=analog_images,
            digital_images=digital_images,
            meter_configs=config.meter_configs,
        )
    )

    storage = getattr(app.state, "storage", None) if app else None
    if storage is not None:
        try:
            storage.record_meter_result(meter_result, image=final_img, config=config)
        except Exception as e:
            logger.warning(f"Error recording meter result to history: {e}")

    mqtt_service = getattr(app.state, "mqtt_service", None) if app else None
    if mqtt_service is not None and getattr(config.mqtt, "enabled", False):
        try:
            mqtt_service.publish_meter_result(meter_result)
        except Exception as e:
            logger.warning(f"Error publishing meter result to MQTT: {e}")

    zero_flow_tracker = getattr(app.state, "zero_flow_tracker", None) if app else None
    if zero_flow_tracker is not None and getattr(
        config.zero_flow_monitor, "enabled", False
    ):
        try:
            target_name = config.zero_flow_monitor.meter_name
            target_val = None
            target_conf = 100.0
            target_qual = "good"
            for m in meter_result.meters:
                if m.name == target_name:
                    try:
                        target_val = float(m.value)
                    except (ValueError, TypeError):
                        target_val = None
                    target_conf = getattr(m, "confidence", 100.0)
                    target_qual = getattr(m, "quality", "good")
                    break

            if target_val is not None:
                zero_status = zero_flow_tracker.evaluate_reading(
                    timestamp=datetime.now(UTC),
                    meter_value=target_val,
                    confidence=target_conf,
                    quality=target_qual,
                    min_confidence_threshold=config.min_confidence_threshold,
                )
                if mqtt_service is not None and getattr(config.mqtt, "enabled", False):
                    mqtt_service.publish_zero_flow_status(zero_status)
        except Exception as e:
            logger.warning(f"Error evaluating zero-flow leak status: {e}")

    return meter_result
