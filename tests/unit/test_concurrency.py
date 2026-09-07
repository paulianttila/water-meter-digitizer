from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from previous_value import (
    load_previous_value_from_file,
    save_previous_value_to_file,
)


def test_concurrent_previous_value_writes(tmp_path):
    target_file = str(tmp_path / "concurrent_prevalue.ini")

    def write_worker(idx: int):
        val = f"{1000 + idx}.{idx:04d}"
        save_previous_value_to_file(target_file, f"meter_{idx % 4}", val)
        return val

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_worker, i) for i in range(40)]
        results = [f.result() for f in futures]

    assert len(results) == 40

    # Ensure all 4 meter sections were created and can be cleanly read
    for m in range(4):
        val = load_previous_value_from_file(target_file, f"meter_{m}")
        assert val is not None
        assert float(val) > 0


def test_concurrent_set_previous_value_endpoints():
    client = TestClient(app)

    with patch("previous_value.save_previous_value_to_file"):

        def api_worker(idx: int):
            response = client.get(
                f"/setPreviousValue?name=total_{idx % 3}&value={100 + idx}.5"
            )
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(api_worker, i) for i in range(24)]
            results = [f.result() for f in futures]

        for status_code, data in results:
            assert status_code == 200
            assert data["status"] == "success"
            assert data["error"] == ""


def test_concurrent_reload_endpoints():
    client = TestClient(app)

    with patch("main.init_config"):

        def reload_worker(idx: int):
            response = client.get("/reload?format=json")
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(reload_worker, i) for i in range(16)]
            results = [f.result() for f in futures]

        for status_code, data in results:
            assert status_code == 200
            assert data["status"] == "success"
            assert "reloaded successfully" in data["message"]
