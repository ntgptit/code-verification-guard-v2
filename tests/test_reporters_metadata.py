from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from rich.console import Console

from code_verification_guard.models.violation import Violation
from code_verification_guard.reporters.console_reporter import ConsoleReporter
from code_verification_guard.reporters.json_reporter import JsonReporter


def test_console_reporter_prints_class_name_and_fix_hint() -> None:
    buffer = StringIO()
    reporter = ConsoleReporter(show_fix_hint=True)
    reporter.console = Console(file=buffer, force_terminal=False, color_system=None)

    reporter.print(
        [
            Violation(
                rule_id="flutter.shared_widget.dart_doc.required",
                severity="error",
                message="Shared widget docs are missing.",
                file_path=Path("lib/presentation/shared/widgets/mx_button.dart"),
                class_name="MxButton",
                line_number=12,
                code_line="class MxButton extends StatelessWidget {",
                fix_hint="Add a Dart doc block.",
            )
        ]
    )

    output = buffer.getvalue()
    assert "Class: MxButton" in output
    assert "Suggested fix: Add a Dart doc block." in output


def test_json_reporter_includes_class_name_and_suggested_fix(capsys) -> None:
    JsonReporter().print(
        [
            Violation(
                rule_id="flutter.shared_widget.dart_doc.required",
                severity="error",
                message="Shared widget docs are missing.",
                file_path=Path("lib/presentation/shared/widgets/mx_button.dart"),
                class_name="MxButton",
                line_number=12,
                code_line="class MxButton extends StatelessWidget {",
                fix_hint="Add a Dart doc block.",
            )
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["class_name"] == "MxButton"
    assert payload[0]["fix_hint"] == "Add a Dart doc block."
    assert payload[0]["suggested_fix"] == "Add a Dart doc block."
