import argparse
import dataclasses
import json
import signal
import os
import gc
import logging
import sys

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from Config import Config

from utils.DownloadUtils import DownloadFailure
import utils.ImageUtils as ImageUtils
from processor.DigitizerProcessor import DigitizerProcessor, MeterResult
from processor.ImageProcessor import ImageProcessor
import PreviousValueFile


VERSION = "8.0.0"

COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)

config_file = os.environ.get("CONFIG_FILE", "/config/config.ini")
processor = None
config = None
images = {}

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(title="meter")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse(
        "index.html", context={"request": request, "version": VERSION}
    )


@app.get("/healthcheck", response_class=HTMLResponse)
def healthcheck():
    return "Health - OK"


@app.get("/image_tmp/{image}")
def get_image(image: str):
    image = image.replace(".jpg", "")
    logger.debug(f"Getting image: {image}")
    img = images.get(image)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    image_bytes = ImageUtils.convert_image_to_bytes(img)
    return Response(content=image_bytes, media_type="image/jpg")


@app.get("/version")
def get_version():
    return Response(json.dumps({"version": VERSION}), media_type="application/json")


@app.get("/exit", response_class=HTMLResponse)
def do_exit():
    os.kill(os.getpid(), signal.SIGTERM)
    return "App will exit in immidiately"


@app.get("/reload", response_class=HTMLResponse)
def reload_config():
    global processor
    del processor
    gc.collect()
    init_app()
    return "Configuration reloaded"


@app.get("/roi", response_class=HTMLResponse)
def get_roi(
    request: Request,
    url: str = None,
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
                    img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

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
            "roi.html",
            context={"request": request, "data": base64image},
        )
    except DownloadFailure as e:
        return f"Error: {e}"


@app.get("/setPreviousValue")
def set_previous_value(name: str, value: str):
    try:
        if value is None or not value.isnumeric():
            raise ValueError(f"Value {value} is not a number")
        PreviousValueFile.save_previous_value_to_file(
            config.prevoius_value_file, name, value
        )
        err = ""
    except Exception as e:
        err = f"{e}"
    return Response(json.dumps({"error": err}), media_type="application/json")


@app.get("/meter")
def get_meters(
    request: Request,
    format: str = "html",
    url: str = None,
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
        "meters.html",
        context={
            "request": request,
            "result": result,
        },
        media_type="text/html",
    )


def get_meter_data(url: str = None, saveimages: bool = False) -> MeterResult:
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
        .save_image("processed")
        .endif_()
        .save_image("final", True)
    )
    digital_images = (
        imageProcessor.start_image_cutting()
        .cut_images(config.digital_readout.cut_images)
        .stop_image_cutting()
        .save_cutted_images()
        .get_cutted_images()
    )
    analog_images = (
        imageProcessor.start_image_cutting()
        .cut_images(config.analog_readout.cut_images)
        .stop_image_cutting()
        .save_cutted_images()
        .get_cutted_images()
    )
    global images
    images = imageProcessor.get_pictures()
    return (
        processor.execute_analog_ccn(analog_images)
        .execute_digital_ccn(digital_images)
        .evaluate_ccn_results()
        .get_meter_values(config.meter_configs)
    )


def get_image_as_base64_str(image_name: str):
    img = images.get(image_name)
    return ImageUtils.convert_image_base64str(img)


def load_config_file() -> str:
    with open(config_file, "r") as f:
        return f.read()


def save_config_file(data: str) -> None:
    with open(config_file, "w") as f:
        f.write(data)


def init_app():
    global processor, config
    config = Config().load_from_file(ini_file=config_file)
    logger.setLevel(config.log_level)

    logging.getLogger("CNN.CNNBase").setLevel(logger.level)
    logging.getLogger("CNN.AnalogNeedleCNN").setLevel(logger.level)
    logging.getLogger("CNN.DigitalCounterCNN").setLevel(logger.level)
    logging.getLogger("Utils.DownloadUtils").setLevel(logger.level)
    logging.getLogger("Config").setLevel(logger.level)
    logging.getLogger("Processor").setLevel(logger.level)
    logging.getLogger("PreviousValueFile").setLevel(logger.level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    processor = DigitizerProcessor()
    (
        processor.init_analog_model(
            config.analog_readout.model_file, config.analog_readout.model
        )
        .init_digital_model(
            config.digital_readout.model_file, config.digital_readout.model
        )
        .use_previous_value_file(config.prevoius_value_file)
    )


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
    init_app()
    port = 3000
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104
        port=port,
        log_level="info" if logger.level == logging.DEBUG else "warning",
    )
