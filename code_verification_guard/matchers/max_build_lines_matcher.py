"""Flutter build method length matcher implementation."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule

COUNT_MODE_LOGICAL = "logical"


class MaxBuildLinesMatcher(BaseMatcher):
    """Checks Flutter build method length."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return long build method violations."""
        violations: list[Violation] = []
        max_lines = int(rule.rule_config[ConfigKeys.MAX_LINES])
        count_mode = rule.rule_config.get(ConfigKeys.COUNT_MODE)

        files = rule.target_rule_files(
            context.project_root,
            Defaults.DEFAULT_DART_INCLUDE_PATTERNS,
        )

        for rule_file in files:
            violations.extend(
                self._check_file(rule, rule_file.path, rule_file.lines, max_lines, count_mode)
            )

        return violations

    def _check_file(
        self,
        rule: BaseRule,
        file_path: Path,
        lines: list[str],
        max_lines: int,
        count_mode: str | None,
    ) -> list[Violation]:
        """Check one file for long build methods."""
        violations: list[Violation] = []

        for index, line in enumerate(lines):
            # Only build methods are measured by this rule.
            if "Widget build(BuildContext context)" not in line:
                continue

            start_line = index + 1
            end_line = self._find_method_end(lines, index)

            # Unbalanced methods are ignored by this length rule.
            if end_line is None:
                continue

            method_lines = lines[index:end_line]
            length = self._count_lines(method_lines, count_mode)

            # Build methods under the configured limit are compliant.
            if length <= max_lines:
                continue

            violations.append(
                rule.create_violation(
                    file_path=file_path,
                    line_number=start_line,
                    code_line=line.strip(),
                    message=f"{rule.message} Current lines: {length}, max: {max_lines}.",
                )
            )

        return violations

    def _count_lines(self, lines: list[str], count_mode: str | None) -> int:
        """Count either raw method lines or logical source lines."""
        if count_mode != COUNT_MODE_LOGICAL:
            return len(lines)

        return sum(
            1
            for line in lines
            if self._is_logical_source_line(line)
        )

    def _is_logical_source_line(self, line: str) -> bool:
        """Return whether a build line contributes to source logic size."""
        stripped = line.strip()

        if not stripped:
            return False

        if stripped.startswith("//"):
            return False

        return not stripped.startswith(("/*", "*", "*/"))

    def _find_method_end(self, lines: list[str], start_index: int) -> int | None:
        """Find the ending line for a brace-delimited method."""
        brace_count = 0
        started = False

        for current_index in range(start_index, len(lines)):
            current_line = lines[current_index]
            brace_count += current_line.count("{")
            brace_count -= current_line.count("}")

            # The first opening brace marks the method body start.
            if "{" in current_line:
                started = True

            # Returning to zero braces marks the method body end.
            if started and brace_count == 0:
                return current_index + 1

        return None
