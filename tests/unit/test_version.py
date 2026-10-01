"""Unit tests for version resolution and fallback in src/version.py."""

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
        patch("version.Path.is_file", return_value=False),
        patch("version.version", side_effect=Exception("not installed")),
    ):
        v = _get_version()
        assert v == FALLBACK_VERSION


def test_version_reads_container_path(tmp_path):
    """Verify pyproject.toml is resolved when located directly beside version.py (container layout)."""
    # Create fake /app directory with pyproject.toml and a fake version.py
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "pyproject.toml").write_bytes(b'[project]\nversion = "2.3.4"\n')
    fake_version_file = app_dir / "version.py"
    fake_version_file.write_text("# dummy")

    with patch("version.__file__", str(fake_version_file)):
        v = _get_version()
        assert v == "2.3.4"
