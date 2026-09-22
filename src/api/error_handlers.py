"""Centralized exception handlers translating domain errors into RFC 7807 Problem Details."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from exceptions import (
    ConfigurationError,
    ImageCaptureError,
    ModelLoadError,
    StorageQuotaExceededError,
    WaterMeterError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain exception handlers with the FastAPI application instance."""

    @app.exception_handler(ImageCaptureError)
    async def image_capture_handler(
        request: Request, exc: ImageCaptureError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "type": "https://errors.watermeter.local/image-capture",
                "title": "Camera Image Capture Failed",
                "status": 502,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )

    @app.exception_handler(ModelLoadError)
    async def model_load_handler(request: Request, exc: ModelLoadError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "type": "https://errors.watermeter.local/model-load-error",
                "title": "CNN Model Load Failed",
                "status": 503,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )

    @app.exception_handler(ConfigurationError)
    async def config_error_handler(
        request: Request, exc: ConfigurationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "type": "https://errors.watermeter.local/configuration-error",
                "title": "Invalid Configuration",
                "status": 422,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )

    @app.exception_handler(StorageQuotaExceededError)
    async def storage_quota_handler(
        request: Request, exc: StorageQuotaExceededError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            content={
                "type": "https://errors.watermeter.local/storage-quota-exceeded",
                "title": "Storage Quota Exceeded",
                "status": 507,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )

    @app.exception_handler(WaterMeterError)
    async def general_domain_handler(
        request: Request, exc: WaterMeterError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://errors.watermeter.local/internal-domain-error",
                "title": "Domain Processing Error",
                "status": 500,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )
