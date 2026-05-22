"""Scan context model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from code_verification_guard.scanner.file_scanner import FileScanner


@dataclass(frozen=True)
class ScanContext:
    """Runtime context shared by matchers while scanning."""
    project_root: Path
    scanner: FileScanner
