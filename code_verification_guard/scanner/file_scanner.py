"""File scanning helpers."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from code_verification_guard.constants.defaults import Defaults


class FileScanner:
    """Collects project files using include and exclude glob patterns."""

    def __init__(self):
        """Create a scanner with a per-run project file cache."""
        self._project_file_cache: dict[Path, list[tuple[Path, str]]] = {}

    def collect_files(
        self,
        project_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> list[Path]:
        """Collect files that match include and exclude patterns."""
        exclude_patterns = exclude_patterns or []
        files: list[Path] = []

        for file_path, relative_path in self._project_files(project_root):
            # Include patterns define the rule's target file set.
            if not self.matches_any(relative_path, include_patterns):
                continue

            # Exclude patterns remove files from the rule's target file set.
            if exclude_patterns and self.matches_any(relative_path, exclude_patterns):
                continue

            files.append(file_path)

        return files

    def _project_files(self, project_root: Path) -> list[tuple[Path, str]]:
        """Return project files after pruning default ignored directories."""
        resolved_root = project_root.resolve()

        if resolved_root not in self._project_file_cache:
            self._project_file_cache[resolved_root] = self._collect_project_files(resolved_root)

        return self._project_file_cache[resolved_root]

    def _collect_project_files(self, project_root: Path) -> list[tuple[Path, str]]:
        """Collect all project files while pruning ignored directories early."""
        files: list[tuple[Path, str]] = []

        for current_root, directory_names, file_names in os.walk(project_root):
            directory_names[:] = [
                directory_name
                for directory_name in directory_names
                if directory_name not in Defaults.DEFAULT_EXCLUDED_PATH_PARTS
            ]

            current_path = Path(current_root)

            for file_name in file_names:
                file_path = current_path / file_name
                relative_path = file_path.relative_to(project_root).as_posix()

                # Some ignored paths, such as .coverage, are files rather than directories.
                if self.is_in_default_excluded_directory(relative_path):
                    continue

                files.append((file_path, relative_path))

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
