import dataclasses
import json
import signal
from lib.ImageLoader import DownloadFailure
from lib.Meter import Meter
import os
import gc
import logging
import sys
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

version = "Version 8.0.0 (2024-03-22)"
meter = None

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
def getIndex(request: Request):
    return templates.TemplateResponse(
        "index.html", context={"request": request, "version": version}
    )


@app.get("/healthcheck")
def healthcheck():
    return "Health - OK"


@app.get("/image_tmp/{image}")
def getImage(image: str):
    return FileResponse(
        f"{imageTmpFolder}/{image}", media_type="image/jpg", filename=image
    )


@app.get("/version", response_class=HTMLResponse)
def getVersion():
    return version


@app.get("/exit", response_class=HTMLResponse)
def doExit():
    os.kill(os.getpid(), signal.SIGTERM)
    return "App will exit in immidiately"


@app.get("/reload", response_class=HTMLResponse)
def reloadConfig():
    global meter
    del meter
    gc.collect()
    meter = Meter(  # noqa: F841
        configFile=f"{configDir}/config.ini",
        prevValueFile=f"{configDir}/prevalue.ini",
        imageTmpFolder=imageTmpFolder,
    )
    return "Configuration reloaded"


@app.get("/roi", response_class=HTMLResponse)
def getRoi(request: Request, url: str = "", timeout: int = 0):
    try:
        meter.getROI(url, timeout)
        return templates.TemplateResponse(
            "roi.html",
            context={"request": request, "image": "/image_tmp/roi.jpg"},
        )
    except DownloadFailure as e:
        return f"Error: {e}"


@app.get("/setPreviousValue", response_class=HTMLResponse)
def setPreviousValue(value: float):
    result = meter.setPreviousValue(value)
    return f"Last value set to: {result}"


@app.get("/meter")
def getMeterValue(
    request: Request,
    format: str = "html",
    url: str = "",
    simpleOutput: bool = False,
    usePreviuosValue: bool = False,
    ignoreConsistencyCheck: bool = False,
    timeout: int = 0,
):
    if format not in ["html", "json"]:
        return Response("Invalid format. Use 'html' or 'json'", media_type="text/html")

    try:
        result = meter.getMeterValue(
            url=url,
            usePreviuosValue=usePreviuosValue,
            ignoreConsistencyCheck=ignoreConsistencyCheck,
            timeout=timeout,
            saveImages=format == "html",
        )
    except Exception as e:
        logger.warn(f"Error occured: {str(e)}")
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
    if simpleOutput:
        return Response(f"{result.newValue.value}", media_type="text/html")
    return templates.TemplateResponse(
        "result.html",
        context={
            "request": request,
            "result": result,
        },
    )


if __name__ == "__main__":
    logLevel = os.environ.get("LOG_LEVEL")
    if logLevel is not None:
        logger.setLevel(logLevel)

    logging.getLogger("lib.CNNBase").setLevel(logger.level)
    logging.getLogger("lib.CutImage").setLevel(logger.level)
    logging.getLogger("lib.ImageLoader").setLevel(logger.level)
    logging.getLogger("lib.Config").setLevel(logger.level)
    logging.getLogger("lib.AnalogCounterCNN").setLevel(logger.level)
    logging.getLogger("lib.DigitalCounterCNN").setLevel(logger.level)
    logging.getLogger("lib.Meter").setLevel(logger.level)

    configDir = os.environ.get("CONFIG_DIR", "/config")
    imageTmpFolder = os.environ.get("IMAGE_TMP", "/image_tmp")
    meter = Meter(
        configFile=f"{configDir}/config.ini",
        prevValueFile=f"{configDir}/prevalue.ini",
        imageTmpFolder=imageTmpFolder,
    )

    port = 3000
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
