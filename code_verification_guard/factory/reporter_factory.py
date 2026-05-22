"""Reporter factory implementation."""

from __future__ import annotations

from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.reporters.console_reporter import ConsoleReporter
from code_verification_guard.reporters.json_reporter import JsonReporter


class ReporterFactory:
    """Creates reporter instances from report format names."""
    REPORTERS = {
        Defaults.DEFAULT_REPORT_FORMAT: ConsoleReporter,
        "json": JsonReporter,
    }

    def create(self, report_format: str, show_fix_hint: bool = False):
        """Create a reporter for a configured format."""
        reporter_class = self.REPORTERS.get(report_format)

        # Unknown formats should fail before reporting starts.
        if reporter_class is None:
            supported_formats = ", ".join(sorted(self.REPORTERS.keys()))
            raise ValueError(
                f"Unsupported report format: {report_format}. "
                f"Supported formats: {supported_formats}"
            )

        # Console output may include optional fix hints.
        if reporter_class is ConsoleReporter:
            return reporter_class(show_fix_hint=show_fix_hint)

        return reporter_class()
