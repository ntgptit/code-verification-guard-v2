"""Base rule implementation."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.models.violation import Violation
from code_verification_guard.scanner.rule_file_reader import RuleFile, RuleFileReader


class BaseRule(ABC):
    """Base class for all rule implementations."""
    def __init__(self, rule_config: dict):
        """Initialize shared rule metadata and helpers."""
        self.rule_config = rule_config
        self.rule_id: str = rule_config[ConfigKeys.ID]
        self.severity: str = rule_config.get(ConfigKeys.SEVERITY, Defaults.DEFAULT_SEVERITY)
        self.message: str = rule_config.get(ConfigKeys.MESSAGE, "")
        self.file_reader = RuleFileReader()

    @abstractmethod
    def check(self, project_root: Path) -> list[Violation]:
        """Check the project and return violations."""
        pass

    def include_patterns(
        self,
        default_patterns: list[str] | None = None,
    ) -> list[str]:
        """Return include patterns for this rule."""
        return self.rule_config.get(
            ConfigKeys.INCLUDE,
            default_patterns or Defaults.DEFAULT_INCLUDE_PATTERNS,
        )

    def exclude_patterns(self) -> list[str]:
        """Return exclude patterns for this rule."""
        return self.rule_config.get(ConfigKeys.EXCLUDE, [])

    def compiled_patterns(self) -> list[re.Pattern]:
        """Return compiled regex patterns for this rule."""
        return [
            re.compile(pattern)
            for pattern in self.rule_config.get(ConfigKeys.PATTERNS, [])
        ]

    def target_files(
        self,
        project_root: Path,
        default_include_patterns: list[str] | None = None,
    ) -> list[Path]:
        """Return target file paths for this rule."""
        return self.file_reader.collect_files(
            project_root,
            self.include_patterns(default_include_patterns),
            self.exclude_patterns(),
        )

    def target_rule_files(
        self,
        project_root: Path,
        default_include_patterns: list[str] | None = None,
    ) -> list[RuleFile]:
        """Return target files with decoded lines for this rule."""
        return self.file_reader.collect_rule_files(
            project_root,
            self.include_patterns(default_include_patterns),
            self.exclude_patterns(),
        )

    def create_violation(
        self,
        file_path: Path,
        line_number: int | None = None,
        column_number: int | None = None,
        code_line: str | None = None,
        message: str | None = None,
    ) -> Violation:
        """Create a violation using this rule's metadata."""
        fix_config = self.rule_config.get(ConfigKeys.FIX, {})
        return Violation(
            rule_id=self.rule_id,
            severity=self.severity,
            message=message or self.message,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            code_line=code_line,
            fix_hint=fix_config.get(ConfigKeys.HINT),
            fix_example_bad=fix_config.get(ConfigKeys.EXAMPLE_BAD),
            fix_example_good=fix_config.get(ConfigKeys.EXAMPLE_GOOD),
        )
