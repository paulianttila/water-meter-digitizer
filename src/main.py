import argparse
from datetime import datetime, timezone
import dataclasses
import json
from pathlib import Path
import signal
import os
import logging
import sys
import time

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from decorators.decorators import log_execution_time
from configuration import Config
from data_classes import HealthResponse
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

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="meter")
image_cache = ImageCache(max_size=50, ttl_seconds=300.0)
app.state.image_cache = image_cache
app.state.start_time = time.time()
app.state.started_at = datetime.now(timezone.utc).isoformat()
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
    camera_diag = check_camera_reachability(config.image_source.url, timeout=2.0)

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
def reload_config():
    init_config()
    return "Configuration reloaded"


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
            .download_image(url, timeout, config.image_source.min_size)
            .rotate_image(config.alignment.rotate_angle)
            .align_image(config.alignment.ref_images)
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
@log_execution_time
def set_previous_value(name: str, value: str) -> Response:
    try:
        if value is None or not value.isnumeric():
            raise ValueError(f"Value {value} is not a number")
        previous_value.save_previous_value_to_file(
            config.previous_value_file, name, value
        )
        err = ""
    except Exception as e:
        err = f"{e}"
    return Response(json.dumps({"error": err}), media_type="application/json")


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
        result = get_meter_data(url, saveimages)
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


@log_execution_time
def get_meter_data(url: str = "", saveimages: bool = False) -> MeterResult:
    url = url or config.image_source.url
    timeout = config.image_source.timeout

    imageProcessor = ImageProcessor()
    (
        imageProcessor.enable_image_saving(saveimages)
        .download_image(url, timeout, config.image_source.min_size)
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

    return (
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


def get_image_as_base64_str(image_name: str) -> str:
    img = app.state.image_cache.get(image_name)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return utils.image.convert_image_base64str(img)


def load_config_file() -> str:
    with open(config_file, "r") as f:
        return f.read()


def save_config_file(data: str) -> None:
    config = Config().load_from_string(data)
    config.save_to_file(config_file, make_backup=True)


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

    frontend.init(app, CallbacksImpl())


@log_execution_time
def init_config() -> None:
    global config
    config = Config().load_from_file(ini_file=config_file)
    logger.setLevel(config.log_level)

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
