import configparser
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


def load_previous_value_from_file(file: str, section: str, max_age=None):
    try:
        config = configparser.ConfigParser()
        config.read(file)

        if max_age is not None:
            time = config.get(section, "Time")
            valueTime = datetime.strptime(time, "%Y.%m.%d %H:%M:%S")
            diff = (datetime.now() - valueTime).days * 24 * 60

            if diff > max_age:
                raise ValueError(
                    f"Previous value not loaded from file as value is too old: "
                    f"({str(diff)} minutes)."
                )

        previous_value = config.get(section, "Value")
        logger.info(f"Previous value loaded from file: " f"{previous_value}")
        return previous_value
    except Exception as e:
        raise ValueError(
            f"Error occured during previous value loading: {str(e)}"
        ) from e


def save_previous_value_to_file(file: str, section: str, value: str):
    config = configparser.ConfigParser()
    config.read(file)
    now = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime())
    config[section]["Time"] = now
    config[section]["Value"] = value
    with open(file, "w") as cfg:
        config.write(cfg)
