import io
import re
import base64
from PIL import Image
import requests


def verify_image(data: bytes, width: int, height: int, format: str = "JPEG") -> bool:
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        return False if image.size != (width, height) else image.format == format
    except Exception:
        return False


def find_between(s, start, end):
    return s.split(start)[1].split(end)[0]


def check_roi_image(response: requests.Response):
    assert len(response.text) > 220000
    assert response.text.startswith("<!DOCTYPE html>")

    base64image = re.search('<img src="data:image/jpeg;base64, (.*)">', response.text)[
        1
    ]
    decodedImage = base64.b64decode(base64image)
    assert verify_image(decodedImage, 800, 600), "JEPG"


def check_image(response: requests.Response):
    image = Image.open(io.BytesIO(response.content))
    image.verify()
    assert image.format == "JPEG"
