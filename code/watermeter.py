from lib.MeterValue import MeterValue
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

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(title="Watermeter")
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
    return FileResponse(f"./image_tmp/{image}", media_type="image/jpg", filename=image)


@app.get("/version", response_class=HTMLResponse)
def getVersion():
    return version


@app.get("/reload", response_class=HTMLResponse)
def reloadConfig():
    global watermeter
    del watermeter
    gc.collect()
    watermeter = MeterValue()
    return "Configuration reloaded"


@app.get("/roi", response_class=HTMLResponse)
def getRoi(url: str = ""):
    return watermeter.getROI(url)


@app.get("/setPreValue", response_class=HTMLResponse)
def setPreValue(value: float):
    return watermeter.setPreValue(value)


@app.get("/watermeter")
def getMeterValue(
    format: str = "html",
    url: str = "",
    simple: bool = True,
    usePreValue: bool = False,
    single: bool = False,
):
    if format == "json":
        return Response(
            watermeter.getMeterValueJSON(url, simple, usePreValue, single),
            media_type="application/json",
        )
    else:
        return Response(
            watermeter.getMeterValue(url, simple, usePreValue, single),
            media_type="text/html",
        )


if __name__ == "__main__":
    logLevel = os.environ.get("LOG_LEVEL")
    if logLevel is not None:
        logger.setLevel(logLevel)

    logging.getLogger("lib.CNNBase").setLevel(logger.level)
    logging.getLogger("lib.CutImage").setLevel(logger.level)
    logging.getLogger("lib.LoadFileFromHTTP").setLevel(logger.level)
    logging.getLogger("lib.ReadConfig").setLevel(logger.level)
    logging.getLogger("lib.UseAnalogCounterCNN").setLevel(logger.level)
    logging.getLogger("lib.UseClassificationCNN").setLevel(logger.level)
    logging.getLogger("lib.MeterValue").setLevel(logger.level)

    watermeter = MeterValue()

    port = 3000
    logger.info(f"Watermeter is serving at port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
