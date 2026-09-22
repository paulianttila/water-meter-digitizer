import configparser
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

from data_classes import INVALID_DIGIT

logger = logging.getLogger(__name__)

_previous_value_lock = threading.Lock()


def _parse_timestamp(time_str: str) -> datetime:
    """Parse timestamp string supporting ISO-8601 and legacy formats."""
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        pass

    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported timestamp format: {time_str}")


def load_previous_value_from_file(
    file: str, section: str, max_age_minutes: int | None = None
) -> str:
    with _previous_value_lock:
        if not os.path.exists(file):
            raise ValueError(f"File '{file}' does not exist.")

        config = configparser.ConfigParser()
        config.read(file)

        try:
            if max_age_minutes is not None and max_age_minutes > 0:
                time_str = config.get(section, "Time")
                value_time = _parse_timestamp(time_str)
                diff_minutes = (datetime.now() - value_time).total_seconds() / 60

                if diff_minutes > max_age_minutes:
                    raise ValueError(
                        f"Previous value not loaded from file as value is too old: "
                        f"{diff_minutes!s} minutes"
                    )

            previous_value = config.get(section, "Value")
            if INVALID_DIGIT in previous_value:
                raise ValueError(
                    f"Previous value for section '{section}' contains invalid digit '{INVALID_DIGIT}': {previous_value}"
                )
            logger.debug("Previous value loaded from file: %s", previous_value)
            return previous_value
        except Exception as e:
            raise ValueError(
                f"Error occured during previous value loading: {e!s}"
            ) from e


def save_previous_value_to_file(file: str, section: str, value: str) -> None:
    if INVALID_DIGIT in value:
        raise ValueError(
            f"Cannot save previous value containing invalid digit '{INVALID_DIGIT}': {value}"
        )
    with _previous_value_lock:
        config = configparser.ConfigParser()
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if os.path.exists(file):
            config.read(file)
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, "Time", now)
            config.set(section, "Value", value)
        else:
            config[section] = {
                "Time": now,
                "Value": value,
            }

        file_path = Path(file).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = file_path.with_suffix(f"{file_path.suffix}.tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as cfg:
                config.write(cfg)
                cfg.flush()
                os.fsync(cfg.fileno())
            os.replace(tmp_file, file_path)
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
            raise


def get_all_previous_values(file: str) -> dict[str, dict[str, str]]:
    with _previous_value_lock:
        if not os.path.exists(file):
            return {}
        config = configparser.ConfigParser()
        try:
            config.read(file)
            result: dict[str, dict[str, str]] = {}
            for section in config.sections():
                result[section] = {
                    "time": config.get(section, "Time", fallback=""),
                    "value": config.get(section, "Value", fallback=""),
                }
            return result
        except Exception as e:
            logger.error("Failed to read previous value file '%s': %s", file, e)
            return {}
