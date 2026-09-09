import pytest

from utils.diagnostics import check_camera_reachability
from utils.download import DownloadFailure, load_file_from_url
from utils.security import extract_file_path_from_uri, is_safe_path


def test_extract_file_path_from_uri():
    assert extract_file_path_from_uri("file:///path/to/file.jpg") == "/path/to/file.jpg"
    assert (
        extract_file_path_from_uri("file:///path/with%20space/file.jpg")
        == "/path/with space/file.jpg"
    )
    assert extract_file_path_from_uri("/direct/path.jpg") == "/direct/path.jpg"
    assert extract_file_path_from_uri("") == ""


def test_is_safe_path(tmp_path):
    safe_dir = tmp_path / "allowed"
    safe_dir.mkdir()
    safe_file = safe_dir / "image.jpg"
    safe_file.write_bytes(b"image")

    unsafe_dir = tmp_path / "restricted"
    unsafe_dir.mkdir()
    unsafe_file = unsafe_dir / "secret.txt"
    unsafe_file.write_bytes(b"secret")

    allowed_dirs = [str(safe_dir)]

    # Safe file inside allowed directory
    assert is_safe_path(str(safe_file), allowed_dirs) is True
    assert is_safe_path(f"file://{safe_file}", allowed_dirs) is True

    # File outside allowed directory
    assert is_safe_path(str(unsafe_file), allowed_dirs) is False
    assert is_safe_path(f"file://{unsafe_file}", allowed_dirs) is False

    # Path traversal attempt
    traversal_path = str(safe_dir / ".." / "restricted" / "secret.txt")
    assert is_safe_path(traversal_path, allowed_dirs) is False
    assert is_safe_path(f"file://{traversal_path}", allowed_dirs) is False

    # Empty inputs
    assert is_safe_path("", allowed_dirs) is False
    assert is_safe_path(str(safe_file), []) is True  # No restrictions


def test_load_file_from_url_allowed_directories(tmp_path):
    safe_dir = tmp_path / "config"
    safe_dir.mkdir()
    safe_img = safe_dir / "meter.jpg"
    safe_img.write_bytes(b"valid_image_bytes_here")

    unsafe_file = tmp_path / "outside.jpg"
    unsafe_file.write_bytes(b"outside_bytes")

    allowed = [str(safe_dir)]

    # Allowed file loads successfully
    data = load_file_from_url(f"file://{safe_img}", allowed_directories=allowed)
    assert data == b"valid_image_bytes_here"

    # Restricted file raises DownloadFailure
    with pytest.raises(DownloadFailure) as exc_info:
        load_file_from_url(f"file://{unsafe_file}", allowed_directories=allowed)
    assert "denied" in str(exc_info.value).lower()


def test_check_camera_reachability_security(tmp_path):
    safe_dir = tmp_path / "config"
    safe_dir.mkdir()
    safe_img = safe_dir / "meter.jpg"
    safe_img.write_bytes(b"data")

    unsafe_file = tmp_path / "passwd.txt"
    unsafe_file.write_bytes(b"root:x:0:0")

    allowed = [str(safe_dir)]

    # Allowed local file
    res_ok = check_camera_reachability(
        f"file://{safe_img}", allowed_directories=allowed
    )
    assert res_ok["reachable"] is True
    assert res_ok["status_code"] == 200

    # Denied local file
    res_denied = check_camera_reachability(
        f"file://{unsafe_file}", allowed_directories=allowed
    )
    assert res_denied["reachable"] is False
    assert res_denied["status_code"] == 403
    assert "denied" in res_denied["error"].lower()
