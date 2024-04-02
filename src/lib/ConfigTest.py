import configparser
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Sections:
    raw_sections: dict

    def __post_init__(self):
        for section_key, section_value in self.raw_sections.items():
            logger.debug(f"{section_key}:")
            setattr(self, section_key, SectionContent(section_value.items()))


@dataclass
class SectionContent:
    raw_section_content: dict

    def __post_init__(self):
        for section_content_k, section_content_v in self.raw_section_content:
            logger.debug(f"  {section_content_k} = {section_content_v}")
            setattr(self, section_content_k, section_content_v)


class Config(Sections):
    def __init__(self, raw_config_parser):
        Sections.__init__(self, raw_config_parser)


class ConfigParser:
    def getConfig(self, file) -> Config:
        conf = configparser.ConfigParser()
        conf.optionxform = str
        conf.read(file)
        return Config(conf)
