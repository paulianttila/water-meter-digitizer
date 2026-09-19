"""Unit tests for domain exception hierarchy and RFC 7807 problem details exception handlers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.error_handlers import register_exception_handlers
from exceptions import (
    ConfigurationError,
    ConsistencyValidationError,
    ImageCaptureError,
    PipelineError,
    StorageQuotaExceededError,
    WaterMeterError,
)


def test_exception_hierarchy() -> None:
    """Verify inheritance relationships across domain exceptions."""
    err = ImageCaptureError(
        "Camera stream timeout", details={"camera_url": "http://192.168.1.50"}
    )
    assert isinstance(err, PipelineError)
    assert isinstance(err, WaterMeterError)
    assert err.message == "Camera stream timeout"
    assert err.details == {"camera_url": "http://192.168.1.50"}

    cons_err = ConsistencyValidationError("Rate excursion")
    assert isinstance(cons_err, PipelineError)
    assert isinstance(cons_err, WaterMeterError)


def test_exception_handlers_rfc7807() -> None:
    """Verify that FastAPI exception handlers return standard RFC 7807 JSON responses."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test-image-error")
    def trigger_image_error():
        raise ImageCaptureError("Cannot fetch frame", details={"device": "esp32cam"})

    @app.get("/test-config-error")
    def trigger_config_error():
        raise ConfigurationError(
            "Missing digital readout section", details={"file": "config.ini"}
        )

    @app.get("/test-storage-quota")
    def trigger_storage_quota():
        raise StorageQuotaExceededError("Disk full", details={"limit_mb": 500})

    @app.get("/test-general-domain")
    def trigger_general_domain():
        raise WaterMeterError("Internal processing failed", details={"code": 99})

    client = TestClient(app)

    # 1. ImageCaptureError -> 502 Bad Gateway
    r1 = client.get("/test-image-error")
    assert r1.status_code == 502
    data1 = r1.json()
    assert data1["status"] == 502
    assert data1["title"] == "Camera Image Capture Failed"
    assert data1["detail"] == "Cannot fetch frame"
    assert data1["details"]["device"] == "esp32cam"

    # 2. ConfigurationError -> 422 Unprocessable Entity
    r2 = client.get("/test-config-error")
    assert r2.status_code == 422
    data2 = r2.json()
    assert data2["status"] == 422
    assert data2["title"] == "Invalid Configuration"
    assert data2["detail"] == "Missing digital readout section"

    # 3. StorageQuotaExceededError -> 507 Insufficient Storage
    r3 = client.get("/test-storage-quota")
    assert r3.status_code == 507
    data3 = r3.json()
    assert data3["status"] == 507
    assert data3["title"] == "Storage Quota Exceeded"

    # 4. WaterMeterError -> 500 Internal Server Error
    r4 = client.get("/test-general-domain")
    assert r4.status_code == 500
    data4 = r4.json()
    assert data4["status"] == 500
    assert data4["title"] == "Domain Processing Error"
