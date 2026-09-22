"""Domain exception hierarchy for the Water Meter Digitizer application."""

from typing import Any


class WaterMeterError(Exception):
    """Base exception for all Water Meter Digitizer domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(WaterMeterError):
    """Raised when configuration parsing, loading, or validation fails."""


class ConfigSyntaxError(ConfigurationError):
    """Raised on invalid INI or JSON configuration syntax."""


class ConfigValidationError(ConfigurationError):
    """Raised when configuration values violate constraints or schema rules."""


class ConfigurationMissingError(ConfigurationError):
    """Raised when required configuration files or sections are absent."""


class PipelineError(WaterMeterError):
    """Base exception for image processing, camera capture, and inference pipeline errors."""


class ImageCaptureError(PipelineError):
    """Raised when camera stream capture fails or image download times out."""


class AlignmentError(PipelineError):
    """Raised when reference markers or alignment transforms cannot be computed."""


class InferenceError(PipelineError):
    """Raised when LiteRT CNN model inference fails or outputs invalid shapes."""


class ModelLoadError(PipelineError, RuntimeError):
    """Raised when a neural network model file cannot be loaded or initialized."""


class ConsistencyValidationError(PipelineError):
    """Raised when a meter reading violates monotonicity, max rate, or sanity bounds."""


class StorageError(WaterMeterError):
    """Base exception for historical database and snapshot storage failures."""


class StorageQuotaExceededError(StorageError):
    """Raised when disk snapshot usage exceeds configured maximum quota."""


class RetentionPruneError(StorageError):
    """Raised when database pruning or vacuuming operation fails."""


class DatabaseConnectionError(StorageError):
    """Raised when relational database connection cannot be established."""


__all__ = [
    "AlignmentError",
    "ConfigSyntaxError",
    "ConfigValidationError",
    "ConfigurationError",
    "ConfigurationMissingError",
    "ConsistencyValidationError",
    "DatabaseConnectionError",
    "ImageCaptureError",
    "InferenceError",
    "ModelLoadError",
    "PipelineError",
    "RetentionPruneError",
    "StorageError",
    "StorageQuotaExceededError",
    "WaterMeterError",
]
