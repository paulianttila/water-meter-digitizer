"""Pytest fixtures for Web UI integration testing using Playwright."""

import os
import re
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Generator
import urllib.request

import pytest
import uvicorn

from main import app


def find_free_port() -> int:
    """Find and return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """Start the FastAPI + NiceGUI server in a background thread and yield URL."""
    import main

    # Determine configuration file from env, /config, or repository config/
    config_file_env = os.environ.get("CONFIG_FILE")
    project_root = Path(__file__).resolve().parents[3]

    candidates = [
        Path(config_file_env).resolve() if config_file_env else None,
        Path("/config/config.ini"),
        project_root / "config" / "config.ini",
        Path("config/config.ini").resolve(),
    ]

    selected_config = next(
        (p for p in candidates if p is not None and p.is_file()), None
    )
    if selected_config is None:
        raise RuntimeError("No valid configuration file found for UI tests.")

    # If /config does not exist on filesystem, adapt ConfigDir to repo config/
    temp_config_file = None
    if not Path("/config").exists() and (project_root / "config").exists():
        raw_text = selected_config.read_text()
        repo_config_dir = str((project_root / "config").resolve())
        adapted_text = re.sub(
            r"^\s*ConfigDir\s*=\s*/config.*$",
            f"ConfigDir = {repo_config_dir}",
            raw_text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        adapted_text = re.sub(
            r"file:///config/",
            f"file://{repo_config_dir}/",
            adapted_text,
            flags=re.IGNORECASE,
        )
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix="_test_config.ini", delete=False
        )
        temp_file.write(adapted_text)
        temp_file.flush()
        temp_file.close()
        temp_config_file = temp_file.name
        final_config_path = temp_config_file
    else:
        final_config_path = str(selected_config)

    os.environ["CONFIG_FILE"] = final_config_path
    main.config_file = final_config_path

    main.init_config()
    main.init_gui(main.app)

    port = find_free_port()
    host = "127.0.0.1"

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to become responsive
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 15.0
    server_ready = False

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    server_ready = True
                    break
        except Exception:
            time.sleep(0.1)

    if not server_ready:
        server.should_exit = True
        if temp_config_file and os.path.exists(temp_config_file):
            os.unlink(temp_config_file)
        raise RuntimeError(f"Server at {base_url} failed to start within timeout.")

    yield base_url

    server.should_exit = True
    thread.join(timeout=3.0)

    if temp_config_file and os.path.exists(temp_config_file):
        try:
            os.unlink(temp_config_file)
        except OSError:
            pass


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Set default browser context options for consistent UI testing."""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1440,
            "height": 900,
        },
        "ignore_https_errors": True,
    }
