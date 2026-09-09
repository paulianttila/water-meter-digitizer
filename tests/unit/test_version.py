import tomllib
from pathlib import Path
from unittest.mock import patch

from version import FALLBACK_VERSION, __version__, _get_version


def test_version_matches_pyproject_toml():
    pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    assert pyproject_path.is_file(), "pyproject.toml should exist"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    expected_version = data["project"]["version"]
    assert __version__ == expected_version
    assert _get_version() == expected_version


def test_version_fallback_when_file_not_found():
    with (
        patch("pathlib.Path.is_file", return_value=False),
        patch("version.version", side_effect=Exception("not installed")),
    ):
        v = _get_version()
        assert v == FALLBACK_VERSION
