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
    # 1. Try reading pyproject.toml from project root
    with contextlib.suppress(Exception):
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if pyproject_path.is_file():
            with open(pyproject_path, "rb") as f:
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
