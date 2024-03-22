from lib.MeterValue import MeterValue
import os
import gc
import logging
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
import uvicorn

version = 'Version 8.0.0 (2024-03-22)'

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(title='Watermeter')

@app.get('/', response_class=HTMLResponse)
def getIndex():
    return '''
<!DOCTYPE html>
<html>
<body>
    Watermeter {0}
    <h1>Links</h1>
    <a href="watermeter?single=True">Watermeter value (single)</a><br>
    <a href="watermeter?usePreValue=True">Watermeter value with previous value</a><br>
    <a href="watermeter?simple=False">Watermeter value with full details</a><br>
    <a href="watermeter?usePreValue=True&simple=False">Watermeter value with previous value and full details</a><br>
    <a href="roi">ROI image</a><br>
    <br><br>
    <a href="watermeter?format=json&single=True">Watermeter value (single) in JSON format</a><br>
    <a href="watermeter?format=json&simple=False&usePreValue=True">Watermeter value with previous value in JSON format</a><br>
    <h1>Set previous value</h1>
    Set previous value by &lt;ip&gt;:&lt;port&gt;/setPreValue.html?value=&lt;value&gt;
    <br><br>
    Example: 192.168.10.23:3000/setPreValue?value=452.0124
    <h1>Reload configuration</h1>
    <a href="reload">Reload</a><br>
</body>
</html>'''.format(version)

@app.get('/healthcheck')
def healthcheck():
    return 'Health - OK'

@app.get('/image_tmp/{image}')
def getImage(image: str):
    return FileResponse(f'./image_tmp/{image}', media_type='image/jpg', filename=image)

@app.get('/version', response_class=HTMLResponse)
def getVersion():
    return version   

@app.get('/reload', response_class=HTMLResponse)
def reloadConfig():
    global watermeter
    del watermeter
    gc.collect()
    watermeter = MeterValue()
    return 'Configuration reloaded'

@app.get('/roi', response_class=HTMLResponse)
def getRoi(url: str = ''):
    return watermeter.getROI(url)

@app.get('/setPreValue', response_class=HTMLResponse)
def setPreValue(value: float):
    return watermeter.setPreValue(value)

@app.get('/watermeter', response_class=HTMLResponse)
def getMeterValue(format: str = 'html', url: str = '', simple: bool = True, usePreValue: bool = False, single: bool = False):
    if format == 'json':
        return watermeter.getMeterValueJSON(url, simple, usePreValue, single)
    else:
        return watermeter.getMeterValue(url, simple, usePreValue, single)    

if __name__ == '__main__':
    logLevel = os.environ.get('LOG_LEVEL')
    if logLevel is not None:
        logger.setLevel(logLevel)

    logging.getLogger('lib.CNNBase').setLevel(logger.level)
    logging.getLogger('lib.CutImage').setLevel(logger.level)
    logging.getLogger('lib.LoadFileFromHTTP').setLevel(logger.level)
    logging.getLogger('lib.ReadConfig').setLevel(logger.level)
    logging.getLogger('lib.UseAnalogCounterCNN').setLevel(logger.level)
    logging.getLogger('lib.UseClassificationCNN').setLevel(logger.level)
    logging.getLogger('lib.MeterValue').setLevel(logger.level)

    watermeter = MeterValue()
    
    port = 3000
    logger.info(f'Watermeter is serving at port {port}')
    uvicorn.run(app, host='0.0.0.0', port=port)
