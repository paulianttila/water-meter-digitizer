"""Configuration exceptions."""

from exceptions import ConfigurationMissingError


class ConfigurationMissing(ConfigurationMissingError):
    """Raised when configuration file or required configuration sections are missing."""
