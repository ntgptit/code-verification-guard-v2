"""Generic rule implementation backed by a matcher."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule
from code_verification_guard.scanner.file_scanner import FileScanner


class GenericRule(BaseRule):
    """Runs a matcher with shared rule metadata."""
    def __init__(self, rule_config: dict, matcher: BaseMatcher):
        """Initialize a generic rule with its matcher."""
        super().__init__(rule_config)
        self.matcher = matcher

    def check(self, project_root: Path) -> list[Violation]:
        """Check a project through the configured matcher."""
        context = ScanContext(project_root=project_root, scanner=FileScanner())
        return self.matcher.match(self, context)
