"""Forbidden import matcher implementation."""

from __future__ import annotations

from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class ForbiddenImportMatcher(BaseMatcher):
    """Checks import declarations against forbidden patterns."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return forbidden import violations for target files."""
        violations: list[Violation] = []
        forbidden_patterns = rule.compiled_patterns()

        for rule_file in rule.target_rule_files(context.project_root):
            for line_index, line in enumerate(rule_file.lines, start=1):
                stripped_line = line.strip()

                # Only import declarations can violate this rule.
                if not self._is_import_line(stripped_line):
                    continue

                for pattern in forbidden_patterns:
                    match = pattern.search(stripped_line)

                    # Keep scanning until a forbidden import pattern matches.
                    if not match:
                        continue

                    violations.append(
                        rule.create_violation(
                            file_path=rule_file.path,
                            line_number=line_index,
                            column_number=match.start() + 1,
                            code_line=stripped_line,
                        )
                    )

        return violations

    def _is_import_line(self, line: str) -> bool:
        """Return whether a line is an import declaration."""
        return (
            line.startswith("import ")
            or line.startswith("from ")
            or line.startswith("package ")
            or line.startswith("using ")
        )
