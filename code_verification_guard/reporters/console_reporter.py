"""Console reporter implementation."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.constants.severity import Severity
from code_verification_guard.models.violation import Violation


class ConsoleReporter:
    """Prints violations to a Rich console."""
    def __init__(self, show_fix_hint: bool = False):
        """Create a console reporter."""
        self.console = Console()
        self.show_fix_hint = show_fix_hint

    def progress(self, completed_rules: int, total_rules: int, rule_id: str) -> None:
        """Print rule execution progress."""
        if total_rules <= 0:
            return

        percent = int((completed_rules / total_rules) * Defaults.PERCENT_COMPLETE)
        self.console.print(
            f"[dim]Running rules: {percent:3d}% "
            f"({completed_rules}/{total_rules}) {rule_id}[/dim]"
        )

    def print(self, violations: list[Violation]) -> None:
        """Print a human-readable violation report."""
        # A clean run should produce a concise success report.
        if not violations:
            self.console.print(
                Panel.fit(
                    "[bold green]Code verification passed.[/bold green]\nNo violations found.",
                    title="code-verification-guard",
                )
            )
            return

        counter = Counter(violation.severity for violation in violations)

        summary = (
            f"[bold red]Code verification failed.[/bold red]\n"
            f"Total: {len(violations)} | "
            f"Errors: {counter.get(Severity.ERROR, 0)} | "
            f"Warnings: {counter.get(Severity.WARNING, 0)} | "
            f"Info: {counter.get(Severity.INFO, 0)}"
        )

        for violation in violations:
            self._print_violation(violation)

        self.console.print()
        self.console.print(
            Panel.fit(
                summary,
                title="code-verification-guard",
            )
        )

    def _print_violation(self, violation: Violation) -> None:
        """Print one violation."""
        severity_style = self._severity_style(violation.severity)
        location = str(violation.file_path)

        # Line numbers are optional for file-level violations.
        if violation.line_number:
            location += f":{violation.line_number}"

        # Column numbers are optional for line-level violations.
        if violation.column_number:
            location += f":{violation.column_number}"

        self.console.print()
        self.console.print(
            Text(f"[{violation.severity.upper()}] {violation.rule_id}", style=severity_style)
        )
        self.console.print(f"  File: {location}")
        if violation.class_name:
            self.console.print(f"  Class: {violation.class_name}")
        self.console.print(f"  Message: {violation.message}")

        # Code snippets are omitted when the rule reports only a location.
        if violation.code_line:
            self.console.print(f"  Code: {violation.code_line}")

        # Fix hints are shown only when requested by report config.
        if self.show_fix_hint and violation.fix_hint:
            self.console.print(f"  Suggested fix: {violation.fix_hint}")

    def _severity_style(self, severity: str) -> str:
        """Return the Rich style for a severity."""
        # Errors should stand out as hard failures.
        if severity == Severity.ERROR:
            return "bold red"

        # Warnings should be visible without looking like failures.
        if severity == Severity.WARNING:
            return "bold yellow"

        return "bold blue"
