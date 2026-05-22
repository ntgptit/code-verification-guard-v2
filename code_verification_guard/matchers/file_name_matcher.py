"""File name matcher implementation."""

from __future__ import annotations

import re

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class FileNameMatcher(BaseMatcher):
    """Matches file names against a configured regex pattern."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return file-name violations for target files."""
        violations: list[Violation] = []
        file_name_pattern = re.compile(rule.rule_config[ConfigKeys.PATTERN])

        for file_path in rule.target_files(context.project_root):
            # Matching file names satisfy this naming rule.
            if file_name_pattern.match(file_path.name):
                continue

            violations.append(
                rule.create_violation(
                    file_path=file_path,
                    code_line=file_path.name,
                )
            )

        return violations
