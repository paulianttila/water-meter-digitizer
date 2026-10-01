"""Application version module (Single Source of Truth).

Reads the version dynamically from pyproject.toml if present,
falling back to package metadata or hardcoded fallback.
"""

import contextlib
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

FALLBACK_VERSION = "1.0.0"


def _get_version() -> str:
    # 1. Try reading pyproject.toml from project root or app directory
    for candidate in (
        Path(__file__).resolve().parent.parent / "pyproject.toml",
        Path(__file__).resolve().parent / "pyproject.toml",
    ):
        with contextlib.suppress(Exception):
            if candidate.is_file():
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                    v = data.get("project", {}).get("version")
                    if v:
                        return str(v)

    # 2. Try reading from installed package metadata
    with contextlib.suppress(PackageNotFoundError, Exception):
        return version("water-meter-digitizer")

    # 3. Fallback
    return FALLBACK_VERSION


__version__: str = _get_version()
