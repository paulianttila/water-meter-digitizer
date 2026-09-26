"""Seed configuration initialization and default asset provisioning."""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

EXCLUDE_SEED_ITEMS = {"local", "backups", ".DS_Store", "__pycache__", ".pytest_cache"}


def find_seed_dir() -> str | None:
    """Locate the default seed configuration directory.

    Checks:
    1. DEFAULT_CONFIG_DIR environment variable if provided
    2. /app/default_config (inside Docker container)
    3. Project repository root config/ directory (via relative path or parents)
    4. Current working directory config/
    """
    if "DEFAULT_CONFIG_DIR" in os.environ:
        env_dir = os.environ["DEFAULT_CONFIG_DIR"]
        if os.path.isdir(env_dir):
            return env_dir

    candidates: list[Path] = [
        Path("/app/default_config"),
        Path(__file__).resolve().parents[2] / "config",
        Path(os.getcwd()) / "config",
        Path(__file__).resolve().parents[1] / "config",
    ]
    for c in candidates:
        if c.is_dir() and (c / "config.ini").is_file():
            return str(c)
    return None


def _adjust_config_ini(
    config_file: str,
    target_dir: str,
) -> None:
    """Adjusts ConfigDir in newly seeded config.ini."""
    p = Path(config_file)
    if not p.is_file():
        return

    content = p.read_text(encoding="utf-8")

    # If target_dir is not /config, update ConfigDir
    if os.path.abspath(target_dir) != "/config":
        # Format ConfigDir nicely: relative to cwd if inside cwd, else absolute
        try:
            rel_path = os.path.relpath(target_dir, os.getcwd())
            dir_str = (
                rel_path
                if not rel_path.startswith("..")
                else os.path.abspath(target_dir)
            )
        except ValueError:
            dir_str = os.path.abspath(target_dir)

        content = re.sub(
            r"^(ConfigDir\s*=\s*).*$",
            rf"\g<1>{dir_str}",
            content,
            flags=re.MULTILINE,
        )

    p.write_text(content, encoding="utf-8")


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
            if item in EXCLUDE_SEED_ITEMS:
                continue
            src_path = os.path.join(seed_dir, item)
            dst_path = os.path.join(target_dir, item)
            if not os.path.exists(dst_path):
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)

        _adjust_config_ini(config_file, target_dir)

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


def copy_default_config(config_file: str, seed_dir: str | None = None) -> bool:
    """Copies default demo configuration and reference markers to the target directory."""
    if seed_dir is None:
        seed_dir = find_seed_dir()
    if not seed_dir or not os.path.exists(seed_dir):
        return False

    target_dir = os.path.dirname(os.path.abspath(config_file))
    seed_dir = os.path.abspath(seed_dir)

    try:
        os.makedirs(target_dir, exist_ok=True)
        for item in os.listdir(seed_dir):
            if item in EXCLUDE_SEED_ITEMS:
                continue
            src_path = os.path.join(seed_dir, item)
            dst_path = os.path.join(target_dir, item)
            if not os.path.exists(dst_path):
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)

        _adjust_config_ini(config_file, target_dir)
        return os.path.exists(config_file)
    except Exception as e:
        logger.error("Failed to copy default config to %s: %s", target_dir, e)
        return False


def init_profile_for_wizard(config_file: str, seed_dir: str | None = None) -> bool:
    """Initializes a new meter profile directory with baseline config ready for the Setup Wizard."""
    if seed_dir is None:
        seed_dir = find_seed_dir()
    if not seed_dir or not os.path.exists(seed_dir):
        return False

    target_dir = os.path.dirname(os.path.abspath(config_file))
    seed_dir = os.path.abspath(seed_dir)

    try:
        os.makedirs(target_dir, exist_ok=True)

        # Copy neuralnets if not already present so models are available
        src_nn = os.path.join(seed_dir, "neuralnets")
        dst_nn = os.path.join(target_dir, "neuralnets")
        if os.path.isdir(src_nn) and not os.path.exists(dst_nn):
            shutil.copytree(src_nn, dst_nn)

        # Copy meter_types if not already present so presets are available
        src_mt = os.path.join(seed_dir, "meter_types")
        if not os.path.isdir(src_mt):
            repo_mt = Path(__file__).resolve().parents[2] / "config" / "meter_types"
            if repo_mt.is_dir():
                src_mt = str(repo_mt)
        dst_mt = os.path.join(target_dir, "meter_types")
        if os.path.isdir(src_mt) and not os.path.exists(dst_mt):
            shutil.copytree(src_mt, dst_mt)

        # Copy meter_types.json single file if present
        src_mt_json = os.path.join(seed_dir, "meter_types.json")
        dst_mt_json = os.path.join(target_dir, "meter_types.json")
        if os.path.isfile(src_mt_json) and not os.path.exists(dst_mt_json):
            shutil.copy2(src_mt_json, dst_mt_json)

        # Create clean default configuration for new meter profile without picture check
        if not os.path.exists(config_file):
            try:
                rel_path = os.path.relpath(target_dir, os.getcwd())
                dir_str = (
                    rel_path
                    if not rel_path.startswith("..")
                    else os.path.abspath(target_dir)
                )
            except ValueError:
                dir_str = os.path.abspath(target_dir)

            from configuration import Config

            clean_cfg = Config.create_clean_default(
                config_dir=dir_str,
                data_dir=f"{dir_str}/data",
            )
            clean_cfg.save_to_file(config_file)

        return os.path.exists(config_file)
    except Exception as e:
        logger.error("Failed to initialize profile for wizard in %s: %s", target_dir, e)
        return False
