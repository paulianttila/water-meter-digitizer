from dataclasses import dataclass

from PIL.Image import Image


@dataclass
class ImagePosition:
    name: str
    x: int
    y: int
    w: int
    h: int


@dataclass
class RefImage(ImagePosition):
    file_name: str


@dataclass
class MeterConfig:
    name: str
    format: str
    consistency_enabled: bool
    allow_negative_rates: bool
    max_rate_value: float
    use_previuos_value: bool
    pre_value_from_file_max_age: int
    use_extended_resolution: bool = False
    unit: str = ""


@dataclass
class CutImage:
    name: str
    image: Image
