"""File scanning helpers."""

from __future__ import annotations

import fnmatch
import os
import re
from functools import lru_cache
from pathlib import Path

from code_verification_guard.constants.defaults import Defaults

# fnmatch normcases both sides, which makes matching case-insensitive on
# Windows and case-sensitive on POSIX; the compiled union must keep that.
_CASE_INSENSITIVE_FS = os.path.normcase("A") == "a"


def _pattern_candidates(pattern: str) -> list[str]:
    """Expand glob patterns into equivalent matching candidates.

    Every globstar may independently match zero directories, so candidates
    cover all combinations of collapsing a leading ``**/`` and each nested
    ``/**/`` — not just the all-or-nothing variants. Without this, a pattern
    like ``a/**/b/**/*.dart`` never matches files sitting directly under
    ``b/`` while still nested under ``a/``.
    """
    normalized_pattern = pattern.replace("\\", "/")
    candidates = {normalized_pattern}
    pending = [normalized_pattern]

    while pending:
        current = pending.pop()

        # A leading globstar should also match paths at project root.
        if current.startswith("**/"):
            stripped = current[3:]
            if stripped not in candidates:
                candidates.add(stripped)
                pending.append(stripped)

        # Each nested globstar should also match zero nested directories.
        search_start = 0
        while True:
            globstar_index = current.find("/**/", search_start)
            if globstar_index == -1:
                break

            collapsed = current[:globstar_index] + current[globstar_index + 3:]
            if collapsed not in candidates:
                candidates.add(collapsed)
                pending.append(collapsed)

            search_start = globstar_index + 1

    return sorted(candidates)


@lru_cache(maxsize=None)
def _compiled_union(patterns: tuple[str, ...]) -> re.Pattern | None:
    """Compile a glob pattern set into one union regex (None when empty)."""
    candidates = [
        candidate
        for pattern in patterns
        for candidate in _pattern_candidates(pattern)
    ]

    if not candidates:
        return None

    translated = "|".join(f"(?:{fnmatch.translate(candidate)})" for candidate in candidates)
    flags = re.IGNORECASE if _CASE_INSENSITIVE_FS else 0
    return re.compile(translated, flags)


class FileScanner:
    """Collects project files using include and exclude glob patterns."""

    def __init__(self):
        """Create a scanner with per-run project file and rule-scope caches."""
        self._project_file_cache: dict[Path, list[tuple[Path, str]]] = {}
        self._scope_file_cache: dict[tuple, list[Path]] = {}

    def collect_files(
        self,
        project_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> list[Path]:
        """Collect files that match include and exclude patterns."""
        exclude_patterns = exclude_patterns or []
        resolved_root = project_root.resolve()

        # Many rules share the same scope, so the filtered file list is
        # memoized per (root, include, exclude) signature.
        cache_key = (resolved_root, tuple(include_patterns), tuple(exclude_patterns))
        cached_files = self._scope_file_cache.get(cache_key)

        if cached_files is None:
            cached_files = self._filter_files(
                resolved_root,
                include_patterns,
                exclude_patterns,
            )
            self._scope_file_cache[cache_key] = cached_files

        return list(cached_files)

    def _filter_files(
        self,
        resolved_root: Path,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> list[Path]:
        """Filter the walked project files through one compiled pattern union."""
        include_regex = _compiled_union(tuple(include_patterns))
        exclude_regex = _compiled_union(tuple(exclude_patterns))
        files: list[Path] = []

        if include_regex is None:
            return files

        for file_path, relative_path in self._project_files(resolved_root):
            # Include patterns define the rule's target file set.
            if not include_regex.match(relative_path):
                continue

            # Exclude patterns remove files from the rule's target file set.
            if exclude_regex is not None and exclude_regex.match(relative_path):
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
        regex = _compiled_union(tuple(patterns))

        if regex is None:
            return False

        return regex.match(path.replace("\\", "/")) is not None

    def is_in_default_excluded_directory(self, path: str) -> bool:
        """Return whether a path belongs to a default ignored directory."""
        return any(
            part in Defaults.DEFAULT_EXCLUDED_PATH_PARTS
            for part in path.replace("\\", "/").split("/")
        )

    def _pattern_candidates(self, pattern: str) -> list[str]:
        """Expand glob patterns into equivalent matching candidates."""
        return _pattern_candidates(pattern)
