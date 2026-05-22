"""File scanning helpers."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from code_verification_guard.constants.defaults import Defaults


class FileScanner:
    """Collects project files using include and exclude glob patterns."""

    def collect_files(
        self,
        project_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> list[Path]:
        """Collect files that match include and exclude patterns."""
        exclude_patterns = exclude_patterns or []
        files: list[Path] = []

        for file_path in project_root.rglob("*"):
            # Directories and special files are not rule targets.
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(project_root).as_posix()

            # Dependency and cache folders are always ignored.
            if self.is_in_default_excluded_directory(relative_path):
                continue

            # Include patterns define the rule's target file set.
            if not self.matches_any(relative_path, include_patterns):
                continue

            # Exclude patterns remove files from the rule's target file set.
            if exclude_patterns and self.matches_any(relative_path, exclude_patterns):
                continue

            files.append(file_path)

        return files

    def matches_any(self, path: str, patterns: list[str]) -> bool:
        """Return whether a path matches any glob pattern."""
        normalized_path = path.replace("\\", "/")
        return any(
            fnmatch.fnmatch(normalized_path, candidate)
            for pattern in patterns
            for candidate in self._pattern_candidates(pattern)
        )

    def is_in_default_excluded_directory(self, path: str) -> bool:
        """Return whether a path belongs to a default ignored directory."""
        return any(
            part in Defaults.DEFAULT_EXCLUDED_PATH_PARTS
            for part in path.replace("\\", "/").split("/")
        )

    def _pattern_candidates(self, pattern: str) -> list[str]:
        """Expand glob patterns into equivalent matching candidates."""
        normalized_pattern = pattern.replace("\\", "/")
        candidates = [normalized_pattern]

        # A leading globstar should also match paths at project root.
        if normalized_pattern.startswith("**/"):
            candidates.append(normalized_pattern[3:])

        # A nested globstar should also match zero nested directories.
        if "/**/" in normalized_pattern:
            candidates.append(normalized_pattern.replace("/**/", "/"))

        return candidates
