import re
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict


class ImagePosition(BaseModel):
    name: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class RefImage(ImagePosition):
    file_name: str = ""


class MeterConfig(BaseModel):
    name: str
    format: str
    consistency_enabled: bool = False
    allow_negative_rates: bool = False
    max_rate_value: float = 0.0
    use_previous_value: bool = False
    pre_value_from_file_max_age: int = 0
    use_extended_resolution: bool = False
    unit: str = ""

    @property
    def value_names(self) -> list[str]:
        return re.findall(r"\{(.*?)\}", self.format)


class CutImage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    image: Image
