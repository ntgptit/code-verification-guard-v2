"""If comment matcher implementation."""

from __future__ import annotations

import re

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class IfCommentMatcher(BaseMatcher):
    """Checks that each if statement has a preceding comment."""
    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return if-comment violations."""
        violations: list[Violation] = []
        if_patterns = rule.compiled_patterns()
        comment_prefixes = tuple(
            rule.rule_config.get(
                ConfigKeys.COMMENT_PREFIXES,
                Defaults.DEFAULT_COMMENT_PREFIXES,
            )
        )

        for rule_file in rule.target_rule_files(context.project_root):
            for line_index, line in enumerate(rule_file.lines, start=1):
                # Only if statements need a nearby comment.
                if not self._is_if_statement(line, if_patterns):
                    continue

                # A valid comment must be directly above the if statement.
                if self._has_comment_above(rule_file.lines, line_index, comment_prefixes):
                    continue

                violations.append(
                    rule.create_violation(
                        file_path=rule_file.path,
                        line_number=line_index,
                        column_number=len(line) - len(line.lstrip()) + 1,
                        code_line=line.strip(),
                    )
                )

        return violations

    def _is_if_statement(self, line: str, if_patterns: list[re.Pattern]) -> bool:
        """Return whether a line is an active if statement."""
        stripped_line = line.strip()

        # Commented code should not be treated as active code.
        if self._is_comment(stripped_line, tuple(Defaults.DEFAULT_COMMENT_PREFIXES)):
            return False

        return any(pattern.search(line) for pattern in if_patterns)

    def _has_comment_above(
        self,
        lines: list[str],
        line_index: int,
        comment_prefixes: tuple[str, ...],
    ) -> bool:
        """Return whether a line has a comment directly above it."""
        previous_line_index = line_index - 2

        # The first line cannot have a preceding comment.
        if previous_line_index < 0:
            return False

        previous_line = lines[previous_line_index].strip()
        return self._is_comment(previous_line, comment_prefixes)

    def _is_comment(self, line: str, comment_prefixes: tuple[str, ...]) -> bool:
        """Return whether a line starts with a comment prefix."""
        return line.startswith(comment_prefixes)
