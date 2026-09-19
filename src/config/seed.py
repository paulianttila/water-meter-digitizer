"""Seed configuration initialization and default asset provisioning."""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def find_seed_dir() -> str | None:
    """Locate the default seed configuration directory.

    Checks:
    1. DEFAULT_CONFIG_DIR environment variable if provided
    2. /app/default_config (inside Docker container)
    3. Project repository config/ directory (during local development)
    """
    if "DEFAULT_CONFIG_DIR" in os.environ:
        env_dir = os.environ["DEFAULT_CONFIG_DIR"]
        if os.path.isdir(env_dir):
            return env_dir

    candidates = [
        "/app/default_config",
        os.path.join(os.getcwd(), "config"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config"
        ),
    ]
    for c in candidates:
        if os.path.isdir(c) and os.path.isfile(os.path.join(c, "config.ini")):
            return c
    return None


def ensure_config_initialized(config_file: str, seed_dir: str | None = None) -> bool:
    """Ensure that a configuration file exists.

    If missing, attempts to populate it and accompanying seed assets
    (models, demo images) from the default seed directory.
    """
    if os.path.exists(config_file):
        return True

    if seed_dir is None:
        seed_dir = find_seed_dir()

    if not seed_dir or not os.path.exists(seed_dir):
        return False

    target_dir = os.path.dirname(os.path.abspath(config_file))
    seed_dir = os.path.abspath(seed_dir)
    if target_dir == seed_dir:
        return os.path.exists(config_file)

    try:
        os.makedirs(target_dir, exist_ok=True)
        for item in os.listdir(seed_dir):
            src_path = os.path.join(seed_dir, item)
            dst_path = os.path.join(target_dir, item)
            if not os.path.exists(dst_path):
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
        logger.info(
            "Initialized default configuration and seed assets into '%s' from '%s'",
            target_dir,
            seed_dir,
        )
        return os.path.exists(config_file)
    except Exception as e:
        logger.warning(
            f"Failed to auto-populate seed configuration into '{target_dir}': {e}"
        )
        return False
