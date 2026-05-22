"""Matcher registry implementation."""

from __future__ import annotations

from threading import Lock

from code_verification_guard.constants.rule_types import RuleType
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.matchers.file_name_matcher import FileNameMatcher
from code_verification_guard.matchers.forbidden_import_matcher import ForbiddenImportMatcher
from code_verification_guard.matchers.if_comment_matcher import IfCommentMatcher
from code_verification_guard.matchers.max_build_lines_matcher import MaxBuildLinesMatcher
from code_verification_guard.matchers.max_lines_matcher import MaxLinesMatcher
from code_verification_guard.matchers.python_docstring_matcher import PythonDocstringMatcher
from code_verification_guard.matchers.regex_matcher import RegexMatcher


class MatcherRegistry:
    """Stores matcher classes by rule type."""
    _instance = None
    _instance_lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Return the shared matcher registry instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        """Create a registry with builtin matchers."""
        if self._initialized:
            return

        self._matcher_classes: dict[str, type[BaseMatcher]] = {
            RuleType.REGEX: RegexMatcher,
            RuleType.FILE_NAME: FileNameMatcher,
            RuleType.MAX_LINES: MaxLinesMatcher,
            RuleType.MAX_BUILD_LINES: MaxBuildLinesMatcher,
            RuleType.FORBIDDEN_IMPORT: ForbiddenImportMatcher,
            RuleType.IF_COMMENT: IfCommentMatcher,
            RuleType.PYTHON_DOCSTRING: PythonDocstringMatcher,
        }
        self._initialized = True

    def get(self, matcher_type: str) -> type[BaseMatcher] | None:
        """Return a matcher class for a rule type."""
        return self._matcher_classes.get(matcher_type)

    def keys(self) -> list[str]:
        """Return registered matcher type keys."""
        return sorted(self._matcher_classes.keys())

    def register(self, matcher_type: str, matcher_class: type[BaseMatcher]) -> None:
        """Register a matcher class for a rule type."""
        self._matcher_classes[matcher_type] = matcher_class
