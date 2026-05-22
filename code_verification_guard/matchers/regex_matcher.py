"""Regex matcher implementation."""

from __future__ import annotations

import re

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule
from code_verification_guard.scanner.rule_file_reader import RuleFile


class RegexMatcher(BaseMatcher):
    """Matches configured regex patterns in line or file mode."""

    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return regex violations for target files."""
        mode = rule.rule_config.get(ConfigKeys.MODE, Defaults.DEFAULT_REGEX_MODE)

        # Line mode keeps the default per-line regex behavior.
        if mode == Defaults.REGEX_LINE_MODE:
            return self._match_lines(rule, context)

        return self._match_file(rule, context)

    def _match_lines(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return regex violations by scanning each line."""
        violations: list[Violation] = []
        regex_patterns = rule.compiled_patterns()

        for rule_file in rule.target_rule_files(context.project_root):
            for line_index, line in enumerate(rule_file.lines, start=1):
                for regex in regex_patterns:
                    match = regex.search(line)

                    # Lines that do not match remain compliant.
                    if not match:
                        continue

                    violations.append(
                        rule.create_violation(
                            file_path=rule_file.path,
                            line_number=line_index,
                            column_number=match.start() + 1,
                            code_line=line.strip(),
                        )
                    )

        return violations

    def _match_file(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return regex violations by scanning whole files."""
        violations: list[Violation] = []
        regex_patterns = [
            re.compile(pattern, re.MULTILINE)
            for pattern in rule.rule_config.get(ConfigKeys.PATTERNS, [])
        ]

        for rule_file in rule.target_rule_files(context.project_root):
            for regex in regex_patterns:
                for match in regex.finditer(rule_file.content):
                    line_number, column_number = self._line_position(
                        rule_file.content,
                        match.start(),
                    )
                    violations.append(
                        rule.create_violation(
                            file_path=rule_file.path,
                            line_number=line_number,
                            column_number=column_number,
                            code_line=self._code_line(rule_file, line_number),
                        )
                    )

        return violations

    def _line_position(self, text: str, offset: int) -> tuple[int, int]:
        """Return one-based line and column for a text offset."""
        prefix = text[:offset]
        line_number = prefix.count("\n") + 1
        column_number = offset - prefix.rfind("\n")

        # Newline-starting matches are clearer when reported on the next line.
        if offset < len(text) and text[offset] == "\n":
            line_number += 1
            column_number = 1

        return line_number, column_number

    def _code_line(self, rule_file: RuleFile, line_number: int) -> str:
        """Return the matched source line for reporting."""
        line_index = line_number - 1

        # Match offsets should point at decoded source lines.
        if line_index < len(rule_file.lines):
            return rule_file.lines[line_index].strip()

        return ""
