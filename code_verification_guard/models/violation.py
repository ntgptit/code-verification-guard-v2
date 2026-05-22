"""Violation data model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """A rule violation found in a project file."""
    rule_id: str
    severity: str
    message: str
    file_path: Path
    line_number: int | None = None
    column_number: int | None = None
    code_line: str | None = None
    fix_hint: str | None = None
    fix_example_bad: str | None = None
    fix_example_good: str | None = None
