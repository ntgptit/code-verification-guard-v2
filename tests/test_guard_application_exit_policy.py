from __future__ import annotations

from pathlib import Path

from code_verification_guard.application.guard_application import GuardApplication
from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.severity import Severity
from code_verification_guard.models.violation import Violation


def test_warning_only_violations_do_not_fail_verification() -> None:
    app = GuardApplication()
    runtime_config = {
        ConfigKeys.FAILURE: {
            ConfigKeys.FAIL_ON: [Severity.ERROR],
            ConfigKeys.WARNING_AS_ERROR: False,
        }
    }
    violations = [
        Violation(
            rule_id="sample.warning",
            severity=Severity.WARNING,
            message="Sample warning.",
            file_path=Path("lib/main.dart"),
        )
    ]

    assert app._should_fail(runtime_config, violations) is False
