"""Maximum file length matcher implementation."""

from __future__ import annotations

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule

COUNT_MODE_LOGICAL = "logical"
DART_DECLARATION_PREFIXES = (
    "import ",
    "export ",
    "part ",
)


class MaxLinesMatcher(BaseMatcher):
    """Checks file length against a configured maximum."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return file length violations for target files."""
        violations: list[Violation] = []
        max_lines = int(rule.rule_config[ConfigKeys.MAX_LINES])
        count_mode = rule.rule_config.get(ConfigKeys.COUNT_MODE)

        for rule_file in rule.target_rule_files(context.project_root):
            line_count = self._count_lines(rule_file.lines, count_mode)

            # Files under the configured limit are compliant.
            if line_count <= max_lines:
                continue

            violations.append(
                rule.create_violation(
                    file_path=rule_file.path,
                    line_number=1,
                    code_line=None,
                    message=f"{rule.message} Current lines: {line_count}, max: {max_lines}.",
                )
            )

        return violations

    def _count_lines(self, lines: list[str], count_mode: str | None) -> int:
        """Count either raw lines or logical source lines."""
        if count_mode != COUNT_MODE_LOGICAL:
            return len(lines)

        return sum(
            1
            for line in lines
            if self._is_logical_source_line(line)
        )

    def _is_logical_source_line(self, line: str) -> bool:
        """Return whether a line contributes to source logic size."""
        stripped = line.strip()

        if not stripped:
            return False

        if stripped.startswith("//"):
            return False

        if stripped.startswith(("/*", "*", "*/")):
            return False

        return not stripped.startswith(DART_DECLARATION_PREFIXES)
