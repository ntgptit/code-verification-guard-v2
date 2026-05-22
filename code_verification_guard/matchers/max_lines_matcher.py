"""Maximum file length matcher implementation."""

from __future__ import annotations

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class MaxLinesMatcher(BaseMatcher):
    """Checks file length against a configured maximum."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return file length violations for target files."""
        violations: list[Violation] = []
        max_lines = int(rule.rule_config[ConfigKeys.MAX_LINES])

        for rule_file in rule.target_rule_files(context.project_root):
            line_count = len(rule_file.lines)

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
