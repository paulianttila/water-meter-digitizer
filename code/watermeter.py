from http.server import BaseHTTPRequestHandler
from urllib import parse
import lib.MeterValue
import os
import socketserver
import gc
from dataclasses import dataclass
import logging
import sys

version = "Version 8.0.0 (2024-03-22)"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

index_page = '''
<!DOCTYPE html>
<html>
<body>
    Watermeter {0}
    <h1>Links</h1>
    <a href="watermeter.html?single">Watermeter value (single)</a><br>
    <a href="watermeter.html?usePreValue">Watermeter value with previous value</a><br>
    <a href="watermeter.html?full">Watermeter value with full details</a><br>
    <a href="watermeter.html?usePreValue&full">Watermeter value with previous value and full details</a><br>
    <a href="roi.html">ROI image</a><br>
    <br><br>
    <a href="watermeter.json?single">Watermeter value (single) in JSON format</a><br>
        <a href="watermeter.json?usePreValue">Watermeter value with previous value in JSON format</a><br>
    <h1>Set previous value</h1>
    Set previous value by &lt;ip&gt;:&lt;port&gt;/setPreValue.html?value=&lt;value&gt;
    <br><br>
    Example: 192.168.10.23:3000/setPreValue.html?value=452.0124
    <h1>Reload configuration</h1>
    <a href="reload.html">Reload</a><br>
</body>
</html>'''

@dataclass
class Params:
    simple: bool = True
    single: bool = True
    usePrevalue: bool = False
    url: str = ''
    value: str = ''

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        logger.debug(format, *args)

    def showMessage(self, message, content_type = 'text/html') -> None:
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(bytes(message, 'UTF-8'))             

    def parseQueryParams(self, path, query) -> Params:
        simple = '&full' not in path and '?full' not in path
        single = '&single' in path or '?single' in path
        usePrevalue = '&useprevalue' in path.lower() or '?useprevalue' in path.lower()
        url = query['url'][0] if 'url' in query else ''
        value = query['value'][0] if 'value' in query else ''
        return Params(simple, single, usePrevalue, url, value)
        
    def do_GET(self):
        global watermeter

        url_parse = parse.urlparse(self.path)
        query = parse.parse_qs(url_parse.query)
        args = self.parseQueryParams(self.path, query)

        if self.path == "/" or '/index.html' in url_parse.path:
            self.showMessage(index_page.format(version))
            return

        if '/reload' in url_parse.path:
            self.showMessage('Reload configuration')
            del watermeter
            gc.collect()
            watermeter = lib.MeterValue.MeterValue()
            return

        if ('/version' in url_parse.path):
            self.showMessage(version)
            return            

        GlobalError = watermeter.CheckError()
        if GlobalError is not None:
            self.showMessage(GlobalError)
            return

        if "/image_tmp/" in url_parse.path:
            self.send_response(200)
            size = str(os.stat(f'.{self.path}').st_size)
            self.send_header('Content-type', 'image/jpg')
            self.send_header('Content-length', size)
            self.end_headers()
            with open(f'.{self.path}', 'rb') as file: 
                self.wfile.write(file.read()) # Read the file and send the contents
            return

        if ('/crash' in url_parse.path):
            self.showMessage('Crash in a second')
            logger.info('Crash with division by zero!')
            a = 1
            b = 0
            c = a/b  # noqa: F841
            return

        if ('/roi' in url_parse.path.lower()):
            result = watermeter.getROI(args.url)
            self.showMessage(result)
            return

        if '/setprevalue' in url_parse.path.lower():
            result = watermeter.setPreValue(args.value)
            self.showMessage(result)
            return

        if '/watermeter.json' in url_parse.path:
            result = watermeter.getMeterValueJSON(args.url, args.simple, args.usePrevalue, args.single)
            self.showMessage(result, 'application/json')
            return

        if '/watermeter' in url_parse.path:
            result = watermeter.getMeterValue(args.url, args.simple, args.usePrevalue, args.single)
            self.showMessage(result)
            return

if __name__ == '__main__':

    logLevel = os.environ.get('LOG_LEVEL')
    if logLevel is not None:
        logger.setLevel(logLevel)

    logging.getLogger("lib.CutImage").setLevel(logger.level)
    logging.getLogger("lib.LoadFileFromHTTP").setLevel(logger.level)
    logging.getLogger("lib.ReadConfig").setLevel(logger.level)
    logging.getLogger("lib.UseAnalogCounterCNN").setLevel(logger.level)
    logging.getLogger("lib.UseClassificationCNN").setLevel(logger.level)
    logging.getLogger("lib.MeterValue").setLevel(logger.level)

    watermeter = lib.MeterValue.MeterValue()

    PORT = 3000
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        logger.info("Watermeter is serving at port %s", PORT)
        httpd.serve_forever()
