"""Python docstring matcher implementation."""

from __future__ import annotations

import ast
from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule


class PythonDocstringMatcher(BaseMatcher):
    """Checks Python AST nodes for required docstrings."""
    NODE_TYPE_MAP = {
        "class": ast.ClassDef,
        "function": ast.FunctionDef,
        "async_function": ast.AsyncFunctionDef,
        "module": ast.Module,
    }

    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return Python docstring violations."""
        violations: list[Violation] = []
        node_types = self._node_types(rule)

        for rule_file in rule.target_rule_files(context.project_root):
            violations.extend(
                self._check_file(rule, rule_file.path, rule_file.lines, node_types)
            )

        return violations

    def _node_types(self, rule: BaseRule) -> tuple[type[ast.AST], ...]:
        """Return AST node types configured for docstring checks."""
        names = rule.rule_config.get(
            ConfigKeys.NODE_TYPES,
            ["function", "async_function"],
        )
        return tuple(self.NODE_TYPE_MAP[name] for name in names)

    def _check_file(
        self,
        rule: BaseRule,
        file_path: Path,
        lines: list[str],
        node_types: tuple[type[ast.AST], ...],
    ) -> list[Violation]:
        """Check one Python file for missing docstrings."""
        source = "\n".join(lines)

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as error:
            return [self._syntax_violation(rule, file_path, error)]

        violations: list[Violation] = []

        # Module docstrings need a file-level location because modules have no line.
        if ast.Module in node_types and not ast.get_docstring(tree):
            violations.append(self._module_violation(rule, file_path, lines))

        for node in ast.walk(tree):
            # The module was checked before walking child nodes.
            if isinstance(node, ast.Module):
                continue

            # Only configured AST node types are covered by this rule.
            if not isinstance(node, node_types):
                continue

            # Nodes with docstrings satisfy the rule.
            if ast.get_docstring(node):
                continue

            line = lines[node.lineno - 1].strip()
            violations.append(
                rule.create_violation(
                    file_path=file_path,
                    line_number=node.lineno,
                    column_number=node.col_offset + 1,
                    code_line=line,
                )
            )

        return violations

    def _syntax_violation(
        self,
        rule: BaseRule,
        file_path: Path,
        error: SyntaxError,
    ) -> Violation:
        """Create a violation for a Python syntax error."""
        code_line = None

        # Syntax errors may include the source line that failed to parse.
        if error.text:
            code_line = error.text.strip()

        return rule.create_violation(
            file_path=file_path,
            line_number=error.lineno,
            column_number=error.offset,
            code_line=code_line,
            message=f"Cannot parse Python file: {error.msg}.",
        )

    def _module_violation(
        self,
        rule: BaseRule,
        file_path: Path,
        lines: list[str],
    ) -> Violation:
        """Create a violation for a missing module docstring."""
        code_line = None

        # Non-empty files can show the first source line in the report.
        if lines:
            code_line = lines[0].strip()

        return rule.create_violation(
            file_path=file_path,
            line_number=1,
            column_number=1,
            code_line=code_line,
        )
