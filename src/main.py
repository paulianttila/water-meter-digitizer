import argparse
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import dataclasses
import json
from pathlib import Path
import signal
import os
import logging
import sys
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from decorators.decorators import log_execution_time
from configuration import Config
from data_classes import HealthResponse
from mqtt.client import MQTTService
from poller.scheduler import BackgroundPoller
from storage import get_storage_backend
from storage.seed import seed_demo_history
from utils.cache import ImageCache
from utils.diagnostics import (
    check_camera_reachability,
    format_uptime,
    get_models_info,
    get_process_memory_info,
    get_system_info,
)
from utils.download import DownloadFailure
import utils.image
from processor.digitizer import DigitizerProcessor, MeterResult
from processor.image import ImageProcessor
import previous_value

VERSION = "8.0.0"

COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)

config_file = os.environ.get("CONFIG_FILE", "/config/config.ini")
config = Config()
_config_lock = threading.Lock()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent


def start_services() -> None:
    """Start MQTT service and background poller based on config."""
    stop_services()

    mqtt_svc = MQTTService(
        config=config.mqtt,
        meter_configs=config.meter_configs,
        version=VERSION,
    )
    if config.mqtt.enabled:
        mqtt_svc.start()
    app.state.mqtt_service = mqtt_svc

    poller = BackgroundPoller(
        config=config.poller,
        readout_func=get_meter_data,
        mqtt_service=mqtt_svc if config.mqtt.enabled else None,
    )
    if config.poller.enabled:
        poller.start()
    app.state.poller = poller


def stop_services() -> None:
    """Stop poller and MQTT services."""
    poller = getattr(app.state, "poller", None)
    if poller is not None:
        poller.stop()

    mqtt_svc = getattr(app.state, "mqtt_service", None)
    if mqtt_svc is not None:
        mqtt_svc.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_services()
    yield
    stop_services()


app = FastAPI(title="meter", lifespan=lifespan)
image_cache = ImageCache(max_size=50, ttl_seconds=300.0)
app.state.image_cache = image_cache
app.state.storage = get_storage_backend(config)
app.state.start_time = time.time()
app.state.started_at = datetime.now(timezone.utc).isoformat()
app.state.mqtt_service = MQTTService(
    config=config.mqtt,
    meter_configs=config.meter_configs,
    version=VERSION,
)
app.state.poller = BackgroundPoller(
    config=config.poller,
    readout_func=lambda *args, **kwargs: None,  # type: ignore
    mqtt_service=app.state.mqtt_service,
)
app.mount(
    "/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static"
)
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))


@app.get("/", response_class=HTMLResponse)
@log_execution_time
def get_index(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request, name="index.html", context={"version": VERSION}
    )


@app.get("/healthcheck", response_class=HTMLResponse)
@log_execution_time
def healthcheck():
    return "Health - OK"


def get_allowed_asset_directories() -> list[str]:
    """Return list of allowed base directory paths for local file:// URIs."""
    allowed: list[str] = []
    if "config" in globals() and config:
        if getattr(config, "config_dir", None):
            allowed.append(config.config_dir)
        if getattr(config, "data_dir", None):
            allowed.append(config.data_dir)
        if getattr(config, "image_tmp_dir", None):
            allowed.append(config.image_tmp_dir)
    allowed.append(os.getcwd())
    return allowed


@app.get("/health", response_model=HealthResponse)
@log_execution_time
def get_health(request: Request) -> HealthResponse:
    now = time.time()
    start_time = getattr(request.app.state, "start_time", now)
    started_at = getattr(
        request.app.state, "started_at", datetime.now(timezone.utc).isoformat()
    )
    uptime_seconds = round(now - start_time, 2)
    uptime_human = format_uptime(uptime_seconds)

    # Check camera reachability
    camera_diag = check_camera_reachability(
        config.image_source.url,
        timeout=2.0,
        allowed_directories=get_allowed_asset_directories(),
    )

    # Memory info
    mem_diag = get_process_memory_info()

    # Cache info
    cache_diag = request.app.state.image_cache.get_stats()

    # Models info
    models_diag = get_models_info(
        digital_enabled=config.digital_readout.enabled,
        digital_modelfile=config.digital_readout.model_file,
        analog_enabled=config.analog_readout.enabled,
        analog_modelfile=config.analog_readout.model_file,
    )

    # System info
    system_diag = get_system_info(VERSION)

    # Determine status:
    # "unhealthy" if camera configured but unreachable or enabled model missing
    # "degraded" if camera not configured
    # "healthy" otherwise
    status = "healthy"
    if not config.image_source.url:
        status = "degraded"
    elif not camera_diag["reachable"]:
        status = "degraded"

    for model_key in ("digital", "analog"):
        m = models_diag[model_key]
        if m["enabled"] and not m["exists"]:
            status = "unhealthy"

    return HealthResponse(
        status=status,
        uptime={
            "uptime_seconds": uptime_seconds,
            "uptime_human": uptime_human,
            "started_at": started_at,
        },
        camera=camera_diag,
        memory=mem_diag,
        cache=cache_diag,
        models=models_diag,
        system=system_diag,
    )


@app.get("/image/{image}")
@app.get("/image_tmp/{image}")
@log_execution_time
def get_image(image: str, request: Request) -> Response:
    image = image.removesuffix(".jpg")
    logger.debug(f"Getting image: {image}")
    img = request.app.state.image_cache.get(image)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    image_bytes = utils.image.convert_image_to_bytes(img)
    return Response(content=image_bytes, media_type="image/jpg")


@app.get("/version")
@log_execution_time
def get_version() -> dict[str, str]:
    return {"version": VERSION}


@app.get("/exit", response_class=HTMLResponse)
@log_execution_time
def do_exit():
    os.kill(os.getpid(), signal.SIGTERM)
    return "App will exit immediately"


@app.get("/reload", response_class=HTMLResponse)
@log_execution_time
def reload_config(request: Request, format: str = "html"):
    error_msg = None
    try:
        init_config()
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        error_msg = str(e)

    if format == "json" or "application/json" in request.headers.get("accept", ""):
        if error_msg:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"Failed to reload configuration: {error_msg}",
                    "version": VERSION,
                    "config_file": config_file,
                },
                status_code=500,
            )
        return JSONResponse(
            {
                "status": "success",
                "message": "Configuration reloaded successfully",
                "version": VERSION,
                "config_file": config_file,
                "meters_count": (
                    len(config.meter_configs) if "config" in globals() and config else 0
                ),
            }
        )

    status_code = 500 if error_msg else 200
    return templates.TemplateResponse(
        request=request,
        name="reload.html",
        context={
            "version": VERSION,
            "error": error_msg,
            "config_file": config_file,
            "config_file_display": (
                Path(config_file).name if len(config_file) > 40 else config_file
            ),
            "reloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "meters_count": (
                len(config.meter_configs) if "config" in globals() and config else 0
            ),
            "poller_enabled": (
                config.poller.enabled if "config" in globals() and config else False
            ),
            "mqtt_enabled": (
                config.mqtt.enabled if "config" in globals() and config else False
            ),
            "history_enabled": (
                config.history.enabled if "config" in globals() and config else False
            ),
        },
        status_code=status_code,
    )


@app.get("/roi", response_class=HTMLResponse)
@log_execution_time
def get_roi(
    request: Request,
    url: str = "",
    draw_refs: bool = True,
    draw_digital: bool = True,
    draw_analog: bool = True,
):
    try:
        url = url or config.image_source.url
        timeout = config.image_source.timeout

        if draw_refs:
            # Check if the image width and height is set in the config file
            # for the reference images. If not, auto fill them from the file.
            for img in config.alignment.ref_images:
                if img.w == 0 or img.h == 0:
                    img.w, img.h = utils.image.image_size_from_file(img.file_name)

        base64image = (
            ImageProcessor()
            .download_image(
                url,
                timeout,
                config.image_source.min_size,
                allowed_directories=get_allowed_asset_directories(),
            )
            .rotate_image(config.alignment.rotate_angle)
            .align_image(
                config.alignment.ref_images,
                method=config.alignment.method,
                min_match_score=config.alignment.min_match_score,
                feature_detector=config.alignment.feature_detector,
                transformation=config.alignment.transformation,
            )
            .if_(draw_refs)
            .draw_roi(config.alignment.ref_images, COLOR_GREEN)
            .endif_()
            .if_(draw_digital)
            .draw_roi(config.digital_readout.cut_images, COLOR_RED)
            .endif_()
            .if_(draw_analog)
            .draw_roi(config.analog_readout.cut_images, COLOR_BLUE)
            .endif_()
            .get_image_as_base64_str()
        )

        return templates.TemplateResponse(
            request=request,
            name="roi.html",
            context={"data": base64image},
        )
    except DownloadFailure as e:
        return f"Error: {e}"


@app.get("/setPreviousValue")
@app.get("/set_previous_value")
@log_execution_time
def set_previous_value(name: str, value: str) -> Response:
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


@app.get("/meter")
@log_execution_time
def get_meters(
    request: Request,
    format: str = "html",
    url: str = "",
    saveimages: bool = False,
):
    if format not in ["html", "json"]:
        return Response("Invalid format. Use 'html' or 'json'", media_type="text/html")

    try:
        result = get_meter_data(url=url, saveimages=saveimages)
    except Exception as e:
        logger.warning(f"Error occured: {str(e)}")
        if format != "html":
            return Response(
                json.dumps({"error": str(e)}), media_type="application/json"
            )
        return Response(f"Error: {e}", media_type="text/html")

    if format != "html":
        return Response(
            json.dumps(dataclasses.asdict(result)),
            media_type="application/json",
        )
    return templates.TemplateResponse(
        request=request,
        name="meters.html",
        context={"result": result},
        media_type="text/html",
    )


@app.get("/history/consumption")
@log_execution_time
def get_history_consumption(
    request: Request,
    meter: str = "total",
    interval: str = "daily",
    days: int = 30,
    cumulative: bool = False,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps([]), media_type="application/json")

    start = datetime.now(timezone.utc) - timedelta(days=days) if days > 0 else None
    valid_intervals = {"hourly", "daily", "weekly"}
    use_interval = interval if interval in valid_intervals else "daily"

    records = storage.get_consumption(
        meter_name=meter,
        interval=use_interval,
        start=start,
    )
    cum_total = 0.0
    data = []
    for r in records:
        cum_total += r.consumption
        data.append(
            {
                "bucket": r.bucket,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "meter_name": r.meter_name,
                "unit": r.unit,
                "consumption": (round(cum_total, 3) if cumulative else r.consumption),
                "cumulative_consumption": round(cum_total, 3),
                "start_value": r.start_value,
                "end_value": r.end_value,
                "min_value": r.min_value,
                "max_value": r.max_value,
                "reading_count": r.reading_count,
            }
        )
    return Response(json.dumps(data), media_type="application/json")


@app.get("/history/readings")
@log_execution_time
def get_history_readings(
    request: Request,
    meter: str | None = None,
    limit: int = 100,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps([]), media_type="application/json")

    records = storage.get_readings(meter_name=meter, limit=limit)
    data = [
        {
            "timestamp": r.timestamp.isoformat(),
            "meters": {k: dataclasses.asdict(v) for k, v in r.meters.items()},
            "digital_results": r.digital_results,
            "analog_results": r.analog_results,
            "error": r.error,
        }
        for r in records
    ]
    return Response(json.dumps(data), media_type="application/json")


@app.get("/history/stats")
@log_execution_time
def get_history_stats(request: Request) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(json.dumps({}), media_type="application/json")

    summary = storage.get_summary()
    data = {
        "backend": summary.backend,
        "total_records": summary.total_records,
        "memory_usage_bytes": summary.memory_usage_bytes,
        "max_memory_bytes": summary.max_memory_bytes,
        "oldest_timestamp": (
            summary.oldest_timestamp.isoformat() if summary.oldest_timestamp else None
        ),
        "newest_timestamp": (
            summary.newest_timestamp.isoformat() if summary.newest_timestamp else None
        ),
        "meters_tracked": summary.meters_tracked,
    }
    return Response(json.dumps(data), media_type="application/json")


@app.post("/history/seed")
@log_execution_time
def seed_history(
    request: Request,
    days: int = 14,
    meter: str = "total",
    base_val: float = 300.0,
) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(
            json.dumps({"error": "Storage backend disabled", "seeded": 0}),
            media_type="application/json",
            status_code=400,
        )
    count = seed_demo_history(storage, meter_name=meter, days=days, base_val=base_val)
    return Response(
        json.dumps(
            {"message": f"Successfully seeded {count} records", "seeded": count}
        ),
        media_type="application/json",
    )


@app.post("/history/clear")
@log_execution_time
def clear_history(request: Request) -> Response:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return Response(
            json.dumps({"error": "Storage backend disabled"}),
            media_type="application/json",
            status_code=400,
        )
    storage.clear()
    return Response(
        json.dumps({"message": "History cleared successfully"}),
        media_type="application/json",
    )


@log_execution_time
def get_meter_data(url: str = "", saveimages: bool = False) -> MeterResult:
    url = url or config.image_source.url
    timeout = config.image_source.timeout

    imageProcessor = ImageProcessor()
    (
        imageProcessor.enable_image_saving(saveimages)
        .download_image(
            url,
            timeout,
            config.image_source.min_size,
            allowed_directories=get_allowed_asset_directories(),
        )
        .save_image("original")
        .rotate_image(config.alignment.rotate_angle)
        .save_image("rotated")
        .align_image(
            config.alignment.ref_images,
            method=config.alignment.method,
            min_match_score=config.alignment.min_match_score,
            feature_detector=config.alignment.feature_detector,
            transformation=config.alignment.transformation,
        )
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
        .if_(config.image_processing.enabled and config.image_processing.autocontrast)
        .autocontrast_image(
            cutoff_low=config.image_processing.autocontrast.cutoff_low,
            cutoff_high=config.image_processing.autocontrast.cutoff_high,
            ignore=config.image_processing.autocontrast.ignore,
        )
        .save_image("processed")
        .endif_()
        .save_image("final", True)
    )
    autocontrast = (
        config.image_processing.enabled
        and config.image_processing.autocontrast_cut_images.enabled
    )
    digital_images = (
        imageProcessor.start_image_cutting()
        .cut_images(
            config.digital_readout.cut_images,
            autocontrast=autocontrast,
            cutoff_low=config.image_processing.autocontrast_cut_images.cutoff_low,
            cutoff_high=config.image_processing.autocontrast_cut_images.cutoff_high,
            ignore=config.image_processing.autocontrast_cut_images.ignore,
        )
        .stop_image_cutting()
        .save_cut_images()
        .get_cut_images()
    )
    analog_images = (
        imageProcessor.start_image_cutting()
        .cut_images(
            config.analog_readout.cut_images,
            autocontrast=autocontrast,
            cutoff_low=config.image_processing.autocontrast_cut_images.cutoff_low,
            cutoff_high=config.image_processing.autocontrast_cut_images.cutoff_high,
            ignore=config.image_processing.autocontrast_cut_images.ignore,
        )
        .stop_image_cutting()
        .save_cut_images()
        .get_cut_images()
    )
    app.state.image_cache.set_many(imageProcessor.get_pictures())

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

    storage = getattr(app.state, "storage", None)
    if storage is not None:
        try:
            storage.record_meter_result(meter_result)
        except Exception as e:
            logger.warning(f"Error recording meter result to history: {e}")

    mqtt_service = getattr(app.state, "mqtt_service", None)
    if mqtt_service is not None and getattr(config.mqtt, "enabled", False):
        try:
            mqtt_service.publish_meter_result(meter_result)
        except Exception as e:
            logger.warning(f"Error publishing meter result to MQTT: {e}")

    return meter_result


@app.get("/poller/status")
@log_execution_time
def get_poller_status(request: Request) -> Response:
    poller = getattr(request.app.state, "poller", None)
    status = poller.get_status() if poller else {"enabled": False, "running": False}
    return Response(json.dumps(status), media_type="application/json")


@app.post("/poller/trigger")
@log_execution_time
def trigger_poller(request: Request) -> Response:
    poller = getattr(request.app.state, "poller", None)
    if poller is None:
        raise HTTPException(status_code=400, detail="Poller service not initialized")
    poller.trigger_now()
    return Response(
        json.dumps({"message": "Poller triggered successfully"}),
        media_type="application/json",
    )


@app.get("/mqtt/status")
@log_execution_time
def get_mqtt_status(request: Request) -> Response:
    mqtt_svc = getattr(request.app.state, "mqtt_service", None)
    status = (
        mqtt_svc.get_status() if mqtt_svc else {"enabled": False, "connected": False}
    )
    return Response(json.dumps(status), media_type="application/json")


def get_image_as_base64_str(image_name: str) -> str:
    img = app.state.image_cache.get(image_name)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return utils.image.convert_image_base64str(img)


def load_config_file() -> str:
    with _config_lock:
        with open(config_file, "r") as f:
            return f.read()


def save_config_file(data: str) -> None:
    with _config_lock:
        new_config = Config().load_from_string(data)
        new_config.save_to_file(config_file, make_backup=True)


def init_gui(app) -> None:
    from callbacks import Callbacks
    import gui.frontend as frontend

    class CallbacksImpl(Callbacks):
        def get_meter_data(
            self, url: str = "", saveimages: bool = False
        ) -> MeterResult:
            return get_meter_data(url=url, saveimages=saveimages)

        def get_image_as_base64_str(self, image_name: str) -> str:
            return get_image_as_base64_str(image_name)

        def get_config(self) -> Config:
            return config

        def load_config_file(self) -> str:
            return load_config_file()

        def save_config_file(self, data: str) -> None:
            return save_config_file(data)

        def use_config(self) -> None:
            init_config()

        def get_storage(self) -> Any:
            return getattr(app.state, "storage", None)

    frontend.init(app, CallbacksImpl())


@log_execution_time
def init_config() -> None:
    with _config_lock:
        global config
        new_config = Config().load_from_file(ini_file=config_file)
        config = new_config
        app.state.config = new_config
        logger.setLevel(config.log_level)
        app.state.storage = get_storage_backend(config)
        start_services()

        logging.getLogger("CNN.CNNBase").setLevel(logger.level)
    logging.getLogger("CNN.AnalogNeedleCNN").setLevel(logger.level)
    logging.getLogger("CNN.DigitalCounterCNN").setLevel(logger.level)
    logging.getLogger("Utils.DownloadUtils").setLevel(logger.level)
    logging.getLogger("Config").setLevel(logger.level)
    logging.getLogger("decorators.decorators").setLevel(logger.level)
    logging.getLogger("Processor").setLevel(logger.level)
    logging.getLogger("PreviousValueFile").setLevel(logger.level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="meter", description="Meter reading application"
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        help="Configuration file",
        default=config_file,
    )

    args = parser.parse_args()
    config_file = args.config_file
    init_config()
    init_gui(app)

    port = 3000
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104
        port=port,
        log_level="info" if logger.level == logging.DEBUG else "warning",
    )
