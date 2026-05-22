"""Violation severity constants."""

from enum import StrEnum


class Severity(StrEnum):
    """Supported violation severities."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
