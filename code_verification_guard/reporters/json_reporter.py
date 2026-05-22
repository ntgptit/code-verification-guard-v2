"""JSON reporter implementation."""

from __future__ import annotations

import json
import sys

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.models.violation import Violation


class JsonReporter:
    """Prints violations as a JSON array."""
    def print(self, violations: list[Violation]) -> None:
        """Print violations as JSON."""
        payload = [
            {
                "rule_id": violation.rule_id,
                ConfigKeys.SEVERITY: violation.severity,
                ConfigKeys.MESSAGE: violation.message,
                "file_path": str(violation.file_path),
                "line_number": violation.line_number,
                "column_number": violation.column_number,
                "code_line": violation.code_line,
                "fix_hint": violation.fix_hint,
                "fix_example_bad": violation.fix_example_bad,
                "fix_example_good": violation.fix_example_good,
            }
            for violation in violations
        ]

        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
