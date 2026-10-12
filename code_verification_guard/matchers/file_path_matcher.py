"""File path matcher implementation."""

from __future__ import annotations

import re

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class FilePathMatcher(BaseMatcher):
    """Matches project-relative file paths against a configured regex pattern.

    The sibling ``file_name`` matcher sees only the basename, so a rule about
    *where* a file sits — not what it is called — cannot be expressed with it
    without resorting to a never-matching pattern over a carefully carved
    include/exclude set. That shape trips the runner's own
    ``rule_without_targets`` diagnostic, because its healthy state is an empty
    target set. This matcher keeps the healthy state populated: the include
    globs select the files the rule governs, and the pattern states the path
    shape each of them must satisfy.

    Paths are compared project-relative with forward slashes on every
    platform, so patterns are portable and never see an absolute prefix.
    """

    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return file-path violations for target files."""
        violations: list[Violation] = []
        file_path_pattern = re.compile(rule.rule_config[ConfigKeys.PATTERN])

        for file_path in rule.target_files(context.project_root):
            relative_path = file_path.relative_to(context.project_root).as_posix()

            # Matching paths satisfy this placement rule.
            if file_path_pattern.match(relative_path):
                continue

            violations.append(
                rule.create_violation(
                    file_path=file_path,
                    code_line=relative_path,
                )
            )

        return violations
