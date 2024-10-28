from typing import Protocol, runtime_checkable

from processor.digitizer import MeterResult
from configuration import Config


@runtime_checkable
class Callbacks(Protocol):
    def get_meter_data(self, url: str = "", saveimages: bool = False) -> MeterResult:
        """Get meter data"""
        ...

    def get_image_as_base64_str(self, image_name: str) -> str:
        """Get image as base64 string"""
        ...

    def get_config(self) -> Config:
        """Get configuration"""
        ...

    def load_config_file(self) -> str:
        """Get configuration file in text format"""
        ...

    def save_config_file(self, data: str) -> None:
        """Set configuration file in text format"""
        ...

    def use_config(self) -> None:
        """Take configuration file in use"""
        ...
