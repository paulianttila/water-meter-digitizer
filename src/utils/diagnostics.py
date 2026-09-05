import contextlib
import os
import platform
import sys
import time
from typing import Any
import requests

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore


def format_uptime(seconds: float) -> str:
    """Format elapsed seconds into a human-readable duration string."""
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def get_process_memory_info() -> dict[str, Any]:
    """
    Retrieve process memory statistics in megabytes.

    Normalizes ru_maxrss across Darwin (bytes) and Linux (kilobytes).
    """
    rss_mb: float | None = None
    peak_rss_mb: float | None = None

    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On macOS (Darwin), ru_maxrss is in bytes. On Linux, it is in kilobytes.
        if sys.platform == "darwin":
            peak_rss_mb = round(usage.ru_maxrss / (1024 * 1024), 2)
        else:
            peak_rss_mb = round(usage.ru_maxrss / 1024, 2)

    # Attempt to read current Resident Set Size (RSS) from /proc/self/status on Linux
    if os.path.exists("/proc/self/status"):
        with contextlib.suppress(Exception):
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        # VmRSS:     12345 kB
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            rss_mb = round(int(parts[1]) / 1024, 2)
                        break

    if rss_mb is None:
        rss_mb = peak_rss_mb or 0.0

    return {
        "rss_mb": rss_mb,
        "peak_rss_mb": peak_rss_mb or rss_mb,
        "platform": sys.platform,
    }


def check_camera_reachability(url: str, timeout: float = 2.0) -> dict[str, Any]:
    """
    Perform a lightweight reachability probe for the camera URL.

    Supports http://, https://, and file:// schemas.
    """
    if not url:
        return {
            "url": "",
            "reachable": False,
            "latency_ms": None,
            "status_code": None,
            "error": "No camera URL configured",
        }

    start_time = time.perf_counter()

    if url.startswith("file://"):
        file_path = url[7:]
        if os.path.exists(file_path):
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "url": url,
                "reachable": True,
                "latency_ms": latency_ms,
                "status_code": 200,
                "error": None,
            }
        return {
            "url": url,
            "reachable": False,
            "latency_ms": None,
            "status_code": 404,
            "error": f"Local file not found: {file_path}",
        }

    try:
        # Try HEAD first; fallback to streaming GET if HEAD is not allowed (405)
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 405:
            response = requests.get(
                url, timeout=timeout, stream=True, allow_redirects=True
            )
            response.close()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_reachable = response.status_code < 400

        return {
            "url": url,
            "reachable": is_reachable,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "error": None if is_reachable else f"HTTP error {response.status_code}",
        }
    except requests.RequestException as e:
        return {
            "url": url,
            "reachable": False,
            "latency_ms": None,
            "status_code": None,
            "error": str(e),
        }


def get_models_info(
    digital_enabled: bool,
    digital_modelfile: str,
    analog_enabled: bool,
    analog_modelfile: str,
) -> dict[str, Any]:
    """Inspect configured CNN model files and return existence and size telemetry."""

    def _inspect_model(enabled: bool, path: str) -> dict[str, Any]:
        exists = os.path.isfile(path) if path else False
        size_bytes = os.path.getsize(path) if exists else None
        return {
            "enabled": enabled,
            "path": path,
            "exists": exists,
            "size_bytes": size_bytes,
        }

    return {
        "digital": _inspect_model(digital_enabled, digital_modelfile),
        "analog": _inspect_model(analog_enabled, analog_modelfile),
    }


def get_system_info(version: str) -> dict[str, Any]:
    """Return runtime and system platform details."""
    return {
        "version": version,
        "python_version": platform.python_version(),
        "platform": f"{platform.system()}-{platform.release()}",
    }
