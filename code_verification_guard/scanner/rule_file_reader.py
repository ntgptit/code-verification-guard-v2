"""Helpers for reading rule target files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from code_verification_guard.scanner.file_scanner import FileScanner


@dataclass(frozen=True)
class RuleFile:
    """A target file and its decoded lines."""
    path: Path
    lines: list[str]
    content: str


class RuleFileReader:
    """Reads target files for rule implementations."""
    def __init__(self, scanner: FileScanner | None = None):
        """Create a reader backed by a file scanner."""
        self.scanner = scanner or FileScanner()

    def collect_files(
        self,
        project_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> list[Path]:
        """Collect target file paths for a rule."""
        return self.scanner.collect_files(
            project_root,
            include_patterns,
            exclude_patterns,
        )

    def collect_rule_files(
        self,
        project_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> list[RuleFile]:
        """Collect target files with their decoded lines."""
        return [
            self.read_rule_file(file_path)
            for file_path in self.collect_files(
                project_root,
                include_patterns,
                exclude_patterns,
            )
        ]

    def read_rule_file(self, file_path: Path) -> RuleFile:
        """Read a text file as a rule target."""
        content = self.read_text(file_path)
        return RuleFile(path=file_path, lines=content.splitlines(), content=content)

    def read_text(self, file_path: Path) -> str:
        """Read a text file as UTF-8 text."""
        return file_path.read_text(encoding="utf-8", errors="ignore")

    def read_lines(self, file_path: Path) -> list[str]:
        """Read a text file as UTF-8 lines."""
        return self.read_text(file_path).splitlines()
